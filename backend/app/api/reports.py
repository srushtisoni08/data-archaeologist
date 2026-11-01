from fastapi import APIRouter, HTTPException, Response
from app.investigation.orchestrator import load_run
from app.reporting.report_generator import build_report, render_markdown, render_pdf, lineage_for_run

router = APIRouter(tags=["reports"])


def _run(run_id):
    run = load_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/lineage/{run_id}")
def lineage(run_id: str):
    return lineage_for_run(_run(run_id))


@router.get("/reports/{run_id}")
def report(run_id: str, format: str = "json"):
    rep = build_report(_run(run_id))
    if format == "md":
        return Response(render_markdown(rep), media_type="text/markdown")
    if format == "pdf":
        return Response(render_pdf(rep), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{run_id}.pdf"'})
    return rep