"""Dashboard home/overview routes."""

from flask import Blueprint, current_app, redirect, render_template, request

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    # Check if user has selected a case
    case_slug = current_app.get_current_case_slug()
    if not case_slug:
        # No case selected, redirect to selector
        return redirect("/cases")

    db = current_app.get_db()
    try:
        stats = {
            "sources": db.fetchone("SELECT COUNT(*) as c FROM sources")["c"],
            "evidence": db.fetchone("SELECT COUNT(*) as c FROM evidence_items")["c"],
            "events": db.fetchone("SELECT COUNT(*) as c FROM events")["c"],
            "hypotheses": db.fetchone("SELECT COUNT(*) as c FROM hypotheses")["c"],
            "suspects": db.fetchone("SELECT COUNT(*) as c FROM suspect_pools")["c"],
            "entities": db.fetchone("SELECT COUNT(*) as c FROM entities")["c"],
            "relationships": db.fetchone("SELECT COUNT(*) as c FROM relationships")["c"],
            "ach_scores": db.fetchone(
                "SELECT COUNT(*) as c FROM hypothesis_evidence_scores"
            )["c"],
            "files": db.fetchone("SELECT COUNT(*) as c FROM attachments")["c"],
        }

        recent = []
        for table, name_col, type_label, date_col in [
            ("sources", "raw_text", "Source", "ingested_at"),
            ("evidence_items", "name", "Evidence", "created_at"),
            ("events", "description", "Event", "created_at"),
            ("hypotheses", "description", "Hypothesis", "created_at"),
            ("suspect_pools", "category", "Suspect Pool", "created_at"),
            ("attachments", "filename", "File", "created_at"),
        ]:
            rows = db.fetchall(
                f"SELECT id, {name_col} as label, {date_col} as ts FROM {table} "
                f"ORDER BY {date_col} DESC LIMIT 3"
            )
            for row in rows:
                label = row["label"]
                if len(label) > 80:
                    label = label[:80] + "..."
                recent.append({
                    "type": type_label,
                    "label": label,
                    "id": row["id"],
                    "ts": row["ts"],
                })

        recent.sort(key=lambda x: x["ts"] or "", reverse=True)
        recent = recent[:10]

        if request.headers.get("HX-Request"):
            return render_template(
                "modern_dashboard.html", stats=stats, recent=recent, case=case_slug
            )
        return render_template(
            "modern_base.html",
            page="dashboard",
            stats=stats,
            recent=recent,
            case=case_slug,
        )
    finally:
        db.close()
