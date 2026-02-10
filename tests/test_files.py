"""Tests for attachments schema and files dashboard routes."""

import sqlite3

import pytest

from deeptrace.db import CaseDatabase

try:
    import flask  # noqa: F401

    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


@pytest.fixture()
def db(tmp_path):
    """Create a fresh case database."""
    path = tmp_path / "test_case.db"
    d = CaseDatabase(path)
    d.open()
    d.initialize_schema()
    yield d
    d.close()


class TestAttachmentsSchema:
    """Verify the attachments and attachment_links tables are created."""

    def test_attachments_table_exists(self, db):
        row = db.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='attachments'"
        )
        assert row is not None

    def test_attachment_links_table_exists(self, db):
        row = db.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='attachment_links'"
        )
        assert row is not None

    def test_insert_attachment(self, db):
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO attachments (filename, mime_type, file_size, data) "
                "VALUES (?, ?, ?, ?)",
                ("photo.jpg", "image/jpeg", 1024, b"\xff\xd8\xff\xe0"),
            )
        row = db.fetchone("SELECT * FROM attachments WHERE id = 1")
        assert row is not None
        assert row["filename"] == "photo.jpg"
        assert row["mime_type"] == "image/jpeg"
        assert row["file_size"] == 1024
        assert row["data"] == b"\xff\xd8\xff\xe0"

    def test_insert_attachment_with_optional_fields(self, db):
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO attachments "
                "(filename, mime_type, file_size, data, description, thumbnail) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("doc.pdf", "application/pdf", 2048, b"%PDF", "A report", b"\x89PNG"),
            )
        row = db.fetchone("SELECT * FROM attachments WHERE id = 1")
        assert row["description"] == "A report"
        assert row["thumbnail"] == b"\x89PNG"
        assert row["ai_analysis"] is None
        assert row["ai_analyzed_at"] is None

    def test_attachment_link_insert(self, db):
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO attachments (filename, mime_type, file_size, data) "
                "VALUES (?, ?, ?, ?)",
                ("photo.jpg", "image/jpeg", 1024, b"\xff\xd8"),
            )
            cur.execute(
                "INSERT INTO evidence_items (name, evidence_type, status) "
                "VALUES (?, ?, ?)",
                ("knife", "physical", "known"),
            )
            cur.execute(
                "INSERT INTO attachment_links (attachment_id, entity_type, entity_id) "
                "VALUES (?, ?, ?)",
                (1, "evidence", 1),
            )
        row = db.fetchone("SELECT * FROM attachment_links WHERE id = 1")
        assert row["attachment_id"] == 1
        assert row["entity_type"] == "evidence"
        assert row["entity_id"] == 1

    def test_attachment_link_check_constraint(self, db):
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO attachments (filename, mime_type, file_size, data) "
                "VALUES (?, ?, ?, ?)",
                ("photo.jpg", "image/jpeg", 1024, b"\xff\xd8"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            with db.transaction() as cur:
                cur.execute(
                    "INSERT INTO attachment_links (attachment_id, entity_type, entity_id) "
                    "VALUES (?, ?, ?)",
                    (1, "invalid_type", 1),
                )

    def test_attachment_link_unique_constraint(self, db):
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO attachments (filename, mime_type, file_size, data) "
                "VALUES (?, ?, ?, ?)",
                ("photo.jpg", "image/jpeg", 1024, b"\xff\xd8"),
            )
            cur.execute(
                "INSERT INTO evidence_items (name, evidence_type, status) "
                "VALUES (?, ?, ?)",
                ("knife", "physical", "known"),
            )
            cur.execute(
                "INSERT INTO attachment_links (attachment_id, entity_type, entity_id) "
                "VALUES (?, ?, ?)",
                (1, "evidence", 1),
            )
        # INSERT OR IGNORE should not raise
        with db.transaction() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO attachment_links "
                "(attachment_id, entity_type, entity_id) VALUES (?, ?, ?)",
                (1, "evidence", 1),
            )
        count = db.fetchone("SELECT COUNT(*) as c FROM attachment_links")["c"]
        assert count == 1

    def test_cascade_delete_attachment(self, db):
        """Deleting an attachment should cascade-delete its links."""
        with db.transaction() as cur:
            cur.execute(
                "INSERT INTO attachments (filename, mime_type, file_size, data) "
                "VALUES (?, ?, ?, ?)",
                ("photo.jpg", "image/jpeg", 1024, b"\xff\xd8"),
            )
            cur.execute(
                "INSERT INTO evidence_items (name, evidence_type, status) "
                "VALUES (?, ?, ?)",
                ("knife", "physical", "known"),
            )
            cur.execute(
                "INSERT INTO attachment_links (attachment_id, entity_type, entity_id) "
                "VALUES (?, ?, ?)",
                (1, "evidence", 1),
            )
        # Verify link exists
        assert db.fetchone("SELECT COUNT(*) as c FROM attachment_links")["c"] == 1
        # Delete attachment
        with db.transaction() as cur:
            cur.execute("DELETE FROM attachments WHERE id = 1")
        # Link should be cascade-deleted
        assert db.fetchone("SELECT COUNT(*) as c FROM attachment_links")["c"] == 0

    def test_indexes_created(self, db):
        """Verify the attachment-related indexes exist."""
        indexes = db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='index' AND "
            "name LIKE '%attachment%'"
        )
        names = {row["name"] for row in indexes}
        assert "idx_attachments_mime" in names
        assert "idx_attachment_link_unique" in names
        assert "idx_attachment_links_entity" in names


@pytest.mark.skipif(not HAS_FLASK, reason="Flask not installed (optional dashboard dependency)")
class TestFilesRoute:
    """Test the dashboard files blueprint (requires Flask test client)."""

    @pytest.fixture()
    def app(self, tmp_path):
        """Create a Flask test app with a case database."""
        import deeptrace.state as _state

        _state.CASES_DIR = tmp_path
        case_dir = tmp_path / "test-case"
        case_dir.mkdir()
        db = CaseDatabase(case_dir / "case.db")
        db.open()
        db.initialize_schema()
        db.close()

        from deeptrace.dashboard import create_app

        app = create_app("test-case")
        app.config["TESTING"] = True
        return app

    @pytest.fixture()
    def client(self, app):
        return app.test_client()

    def test_files_index_empty(self, client):
        resp = client.get("/files/", headers={"HX-Request": "true"})
        assert resp.status_code == 200
        assert b"No files uploaded yet" in resp.data

    def test_upload_and_list(self, client):
        from io import BytesIO

        data = {
            "file": (BytesIO(b"fake image data"), "test.png"),
            "description": "Test file",
        }
        resp = client.post(
            "/files/",
            data=data,
            content_type="multipart/form-data",
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200
        assert b"test.png" in resp.data

    def test_upload_no_file(self, client):
        resp = client.post("/files/", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_detail(self, client):
        from io import BytesIO

        client.post(
            "/files/",
            data={"file": (BytesIO(b"data"), "test.txt")},
            content_type="multipart/form-data",
        )
        resp = client.get("/files/1")
        assert resp.status_code == 200
        assert b"test.txt" in resp.data

    def test_download(self, client):
        from io import BytesIO

        client.post(
            "/files/",
            data={"file": (BytesIO(b"hello world"), "test.txt")},
            content_type="multipart/form-data",
        )
        resp = client.get("/files/1/download")
        assert resp.status_code == 200
        assert resp.data == b"hello world"

    def test_thumbnail_placeholder(self, client):
        from io import BytesIO

        client.post(
            "/files/",
            data={"file": (BytesIO(b"%PDF-1.4"), "doc.pdf")},
            content_type="multipart/form-data",
        )
        resp = client.get("/files/1/thumbnail")
        assert resp.status_code == 200
        assert b"<svg" in resp.data

    def test_delete(self, client):
        from io import BytesIO

        client.post(
            "/files/",
            data={"file": (BytesIO(b"data"), "test.txt")},
            content_type="multipart/form-data",
        )
        resp = client.delete("/files/1")
        assert resp.status_code == 200
        resp = client.get("/files/1")
        assert resp.status_code == 404

    def test_link_and_unlink(self, client, app):
        from io import BytesIO

        # Upload a file
        client.post(
            "/files/",
            data={"file": (BytesIO(b"data"), "test.txt")},
            content_type="multipart/form-data",
        )
        # Create an evidence item to link to
        db = app.get_db()
        try:
            with db.transaction() as cur:
                cur.execute(
                    "INSERT INTO evidence_items (name, evidence_type, status) "
                    "VALUES (?, ?, ?)",
                    ("knife", "physical", "known"),
                )
        finally:
            db.close()

        # Link
        resp = client.post(
            "/files/1/link",
            data={"entity_type": "evidence", "entity_id": "1"},
        )
        assert resp.status_code == 200
        assert b"evidence" in resp.data

        # Unlink
        resp = client.delete("/files/1/link/1")
        assert resp.status_code == 200

    def test_type_filter(self, client):
        from io import BytesIO

        client.post(
            "/files/",
            data={"file": (BytesIO(b"img"), "pic.jpg")},
            content_type="multipart/form-data",
        )
        resp = client.get(
            "/files/?type=image", headers={"HX-Request": "true"}
        )
        assert resp.status_code == 200
