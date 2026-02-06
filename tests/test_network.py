"""Tests for network analysis commands."""

import pytest

from deeptrace.db import CaseDatabase
from deeptrace.main import app

networkx = pytest.importorskip("networkx")
pyvis = pytest.importorskip("pyvis")


@pytest.fixture
def case_with_data(tmp_cases_dir, monkeypatch):
    """Create a case with entities, evidence, sources, and relationships."""
    monkeypatch.setattr("deeptrace.state.CASES_DIR", tmp_cases_dir)
    case_dir = tmp_cases_dir / "test-case"
    case_dir.mkdir(parents=True)
    db = CaseDatabase(case_dir / "case.db")
    db.open()
    db.initialize_schema()

    # Add sources
    db.execute(
        "INSERT INTO sources (raw_text, source_type, notes) VALUES (?, ?, ?)",
        ("FBI report", "official", "Primary source"),
    )
    db.execute(
        "INSERT INTO sources (raw_text, source_type, notes) VALUES (?, ?, ?)",
        ("News article", "news", "Secondary source"),
    )

    # Add entities
    db.execute(
        "INSERT INTO entities (name, entity_type, source_id) VALUES (?, ?, ?)",
        ("Victim A", "person", 1),
    )
    db.execute(
        "INSERT INTO entities (name, entity_type, source_id) VALUES (?, ?, ?)",
        ("Suspect B", "person", 1),
    )
    db.execute(
        "INSERT INTO entities (name, entity_type, source_id) VALUES (?, ?, ?)",
        ("Location X", "location", 2),
    )

    # Add relationship between entities
    db.execute(
        "INSERT INTO relationships (entity_a_id, entity_b_id, relationship_type, strength) "
        "VALUES (?, ?, ?, ?)",
        (1, 2, "known_associate", 0.7),
    )

    # Add evidence linked to source
    db.execute(
        "INSERT INTO evidence_items (name, evidence_type, status, source_id) VALUES (?, ?, ?, ?)",
        ("Knife", "physical", "known", 1),
    )

    # Add hypothesis
    db.execute(
        "INSERT INTO hypotheses (description, tier) VALUES (?, ?)",
        ("Suspect B committed the crime", "plausible"),
    )

    # Add ACH score linking hypothesis to evidence
    db.execute(
        "INSERT INTO hypothesis_evidence_scores"
        " (hypothesis_id, evidence_id, consistency, diagnostic_weight)"
        " VALUES (?, ?, ?, ?)",
        (1, 1, "C", "H"),
    )

    # Add timeline event
    db.execute(
        "INSERT INTO events (description, timestamp_start, confidence, source_id)"
        " VALUES (?, ?, ?, ?)",
        ("Crime occurred", "2026-01-15T22:00", "high", 1),
    )

    # Add suspect pool
    db.execute(
        "INSERT INTO suspect_pools (category, description, priority) VALUES (?, ?, ?)",
        ("Known associates", "People who knew the victim", "high"),
    )

    db.conn.commit()
    db.close()
    return "test-case"


@pytest.fixture
def empty_case(tmp_cases_dir, monkeypatch):
    monkeypatch.setattr("deeptrace.state.CASES_DIR", tmp_cases_dir)
    case_dir = tmp_cases_dir / "empty-case"
    case_dir.mkdir(parents=True)
    db = CaseDatabase(case_dir / "case.db")
    db.open()
    db.initialize_schema()
    db.close()
    return "empty-case"


class TestNetworkSummary:
    def test_summary_with_data(self, runner, case_with_data):
        result = runner.invoke(app, ["network", "summary", "--case", case_with_data])
        assert result.exit_code == 0
        assert "Network Summary" in result.output
        assert "Total nodes" in result.output
        assert "Total edges" in result.output

    def test_summary_empty_case(self, runner, empty_case):
        result = runner.invoke(app, ["network", "summary", "--case", empty_case])
        assert result.exit_code == 0
        assert "No data" in result.output

    def test_summary_shows_node_types(self, runner, case_with_data):
        result = runner.invoke(app, ["network", "summary", "--case", case_with_data])
        assert "entity" in result.output
        assert "evidence" in result.output
        assert "source" in result.output


class TestNetworkConnections:
    def test_connections_specific_node(self, runner, case_with_data):
        result = runner.invoke(
            app, ["network", "connections", "--case", case_with_data, "--node", "entity:1"]
        )
        assert result.exit_code == 0
        assert "Victim A" in result.output

    def test_connections_most_connected(self, runner, case_with_data):
        result = runner.invoke(
            app, ["network", "connections", "--case", case_with_data]
        )
        assert result.exit_code == 0
        assert "Most Connected" in result.output

    def test_connections_filter_by_type(self, runner, case_with_data):
        result = runner.invoke(
            app, ["network", "connections", "--case", case_with_data, "--type", "entity"]
        )
        assert result.exit_code == 0

    def test_connections_invalid_node(self, runner, case_with_data):
        result = runner.invoke(
            app, ["network", "connections", "--case", case_with_data, "--node", "entity:999"]
        )
        assert result.exit_code != 0

    def test_connections_empty_case(self, runner, empty_case):
        result = runner.invoke(
            app, ["network", "connections", "--case", empty_case]
        )
        assert result.exit_code == 0
        assert "No data" in result.output


class TestNetworkClusters:
    def test_clusters_connected(self, runner, case_with_data):
        result = runner.invoke(app, ["network", "clusters", "--case", case_with_data])
        assert result.exit_code == 0

    def test_clusters_empty(self, runner, empty_case):
        result = runner.invoke(app, ["network", "clusters", "--case", empty_case])
        assert result.exit_code == 0
        assert "No data" in result.output


class TestNetworkBridges:
    def test_bridges_with_data(self, runner, case_with_data):
        result = runner.invoke(app, ["network", "bridges", "--case", case_with_data])
        assert result.exit_code == 0

    def test_bridges_empty(self, runner, empty_case):
        result = runner.invoke(app, ["network", "bridges", "--case", empty_case])
        assert result.exit_code == 0
        assert "Need at least" in result.output


class TestNetworkPaths:
    def test_path_between_nodes(self, runner, case_with_data):
        result = runner.invoke(
            app,
            [
                "network", "paths", "--case", case_with_data,
                "--source", "entity:1", "--target", "entity:2",
            ],
        )
        assert result.exit_code == 0
        assert "Path found" in result.output

    def test_path_invalid_node(self, runner, case_with_data):
        result = runner.invoke(
            app,
            [
                "network", "paths", "--case", case_with_data,
                "--source", "entity:1", "--target", "entity:999",
            ],
        )
        assert result.exit_code != 0

    def test_path_through_source(self, runner, case_with_data):
        """Evidence:1 and event:1 share source:1, so a path should exist."""
        result = runner.invoke(
            app,
            [
                "network", "paths", "--case", case_with_data,
                "--source", "evidence:1", "--target", "event:1",
            ],
        )
        assert result.exit_code == 0
        assert "Path found" in result.output


class TestNetworkVisualize:
    def test_creates_html_file(self, runner, case_with_data, tmp_path):
        out = str(tmp_path / "test_graph.html")
        result = runner.invoke(
            app,
            [
                "network", "visualize", "--case", case_with_data,
                "--output", out, "--no-open",
            ],
        )
        assert result.exit_code == 0
        assert "Saved interactive graph" in result.output
        assert (tmp_path / "test_graph.html").exists()

    def test_html_contains_vis_js(self, runner, case_with_data, tmp_path):
        out = str(tmp_path / "graph.html")
        runner.invoke(
            app,
            [
                "network", "visualize", "--case", case_with_data,
                "--output", out, "--no-open",
            ],
        )
        content = (tmp_path / "graph.html").read_text()
        assert "vis-network" in content or "vis" in content

    def test_html_contains_legend(self, runner, case_with_data, tmp_path):
        out = str(tmp_path / "graph.html")
        runner.invoke(
            app,
            [
                "network", "visualize", "--case", case_with_data,
                "--output", out, "--no-open",
            ],
        )
        content = (tmp_path / "graph.html").read_text()
        assert "dt-legend" in content
        assert "DeepTrace Network" in content

    def test_html_contains_nodes(self, runner, case_with_data, tmp_path):
        out = str(tmp_path / "graph.html")
        runner.invoke(
            app,
            [
                "network", "visualize", "--case", case_with_data,
                "--output", out, "--no-open",
            ],
        )
        content = (tmp_path / "graph.html").read_text()
        assert "Victim A" in content
        assert "Knife" in content

    def test_empty_case(self, runner, empty_case, tmp_path):
        out = str(tmp_path / "empty.html")
        result = runner.invoke(
            app,
            [
                "network", "visualize", "--case", empty_case,
                "--output", out, "--no-open",
            ],
        )
        assert result.exit_code == 0
        assert "No data" in result.output

    def test_default_output_name(self, runner, case_with_data, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["network", "visualize", "--case", case_with_data, "--no-open"],
        )
        assert result.exit_code == 0
        assert (tmp_path / "test-case-network.html").exists()


class TestNetworkInspect:
    def test_overview_mode(self, runner, case_with_data):
        result = runner.invoke(
            app, ["network", "inspect", "--case", case_with_data]
        )
        assert result.exit_code == 0
        assert "Network Overview" in result.output
        assert "Nodes by Type" in result.output

    def test_focus_on_entity(self, runner, case_with_data):
        result = runner.invoke(
            app,
            [
                "network", "inspect", "--case", case_with_data,
                "--focus", "entity:1",
            ],
        )
        assert result.exit_code == 0
        assert "Victim A" in result.output
        assert "Connections" in result.output

    def test_focus_on_source(self, runner, case_with_data):
        result = runner.invoke(
            app,
            [
                "network", "inspect", "--case", case_with_data,
                "--focus", "source:1",
            ],
        )
        assert result.exit_code == 0
        assert "source" in result.output

    def test_focus_shows_navigation_hints(self, runner, case_with_data):
        result = runner.invoke(
            app,
            [
                "network", "inspect", "--case", case_with_data,
                "--focus", "source:1",
            ],
        )
        assert "Drill deeper" in result.output
        assert "deeptrace network inspect" in result.output

    def test_focus_invalid_node(self, runner, case_with_data):
        result = runner.invoke(
            app,
            [
                "network", "inspect", "--case", case_with_data,
                "--focus", "entity:999",
            ],
        )
        assert result.exit_code != 0

    def test_empty_case(self, runner, empty_case):
        result = runner.invoke(
            app, ["network", "inspect", "--case", empty_case]
        )
        assert result.exit_code == 0
        assert "No data" in result.output

    def test_overview_shows_isolated(self, runner, case_with_data):
        """Suspect pool and hypothesis should be isolated (no edges to them)."""
        result = runner.invoke(
            app, ["network", "inspect", "--case", case_with_data]
        )
        # Hypothesis has ACH edge so won't be isolated, but suspect pool should be
        assert "Isolated" in result.output
        assert "suspect_pool" in result.output
