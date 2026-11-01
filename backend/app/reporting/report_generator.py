import io
from datetime import datetime
from xml.sax.saxutils import escape
from app.database import store
from app.discovery.lineage_inference import infer_lineage


def _ev(run, tool):
    e = next((x for x in run["evidence"] if x["tool"] == tool and "error" not in x["result"]), None)
    return e["result"] if e else {}


def lineage_for_run(run: dict) -> dict:
    disc = {"column_matches": _ev(run, "find_column_matches").get("matches", []),
            "relationships": _ev(run, "detect_relationships").get("relationships", [])}
    return infer_lineage(store.list_profiles(), disc)


def _actions(run, lin):
    a = []
    for h in run["hypotheses"]:
        d = h.get("details") or {}
        if h["type"] == "foreign_key" and d.get("orphan_count") and "(one_to_one)" not in h["claim"]:
            a.append(f"Confirm the authoritative parent for {d['target']}; unmatched values {d['orphan_examples']}.")
        elif h["type"] == "contradiction":
            a.append(f"Decide the source of truth for: {h['claim']}.")
        elif h["type"] == "entity_match" and h["needs_review"]:
            a.append(f"Review before merging: {h['claim']}.")
    for x in run["anomalies"]:
        if x["type"] != "broken_reference":
            a.append(f"Fix or explain {x['type']} in {x['dataset_id']}.{x['column']}: {x['examples']}.")
    for e in lin["edges"]:
        if e["type"] == "related_versions":
            a.append(f"Confirm which of {e['source']} / {e['target']} is newer (no ordering evidence).")
        else:
            a.append(f"Confirm {e['source']} -> {e['target']} with ETL logs or the data owner.")
    return list(dict.fromkeys(a))


def build_report(run: dict) -> dict:
    lin = lineage_for_run(run)
    profs = {p["dataset_id"]: p for p in store.list_profiles()}
    S = []
    S.append({"title": "Datasets", "items": [
        f"{p['dataset_id']} {p['filename']}: {p.get('row_count')} rows, {p.get('column_count')} cols, "
        f"quality {p.get('fingerprint', {}).get('quality_score')}" for p in profs.values()]})
    S.append({"title": "Relationships (inferred)", "items": [
        f"[{h['status']}, confidence {h['confidence']}] {h['claim']}" + (f" | {'; '.join(h['notes'])}" if h["notes"] else "")
        for h in run["hypotheses"] if h["type"] == "foreign_key"]})
    S.append({"title": "Lineage (inferred, not confirmed provenance)", "items": [
        f"{e['source']} -> {e['target']} ({e['type']}, relatedness {e['relatedness']}, direction confidence "
        f"{e['direction_confidence']}): " + "; ".join(e["transformations"]) for e in lin["edges"]]
        + [f"{t['child']} aligns with {t['aligns_with']} ({t['coverage']}) more than {t['versus']} "
           f"({t['coverage_versus']}): {t['interpretation']}" for t in lin["temporal_hints"]]
        + [lin["caveat"]]})
    S.append({"title": "Entities", "items": [
        f"[{h['status']}, confidence {h['confidence']}] {h['claim']}" for h in run["hypotheses"] if h["type"] == "entity_match"]})
    S.append({"title": "Contradictions", "items": [
        f"[{h['status']}] {h['claim']} | {'; '.join(h['notes'])}" for h in run["hypotheses"] if h["type"] == "contradiction"]})
    S.append({"title": "Anomalies", "items": [
        f"[{x['severity']}] {x['type']} in {x['dataset_id']}.{x['column']}: {x['count']} ({x['examples']})" for x in run["anomalies"]]})
    S.append({"title": "Unresolved questions", "items": run["open_questions"]})
    acts = _actions(run, lin)
    S.append({"title": "Recommended actions", "items": acts})
    S.append({"title": "Method", "items": [
        f"{len(run['steps'])} tool calls; every number comes from deterministic Python tools "
        f"(evidence ids {run['evidence'][0]['id']}..{run['evidence'][-1]['id']}).",
        f"Planner: {'LLM with rules fallback' if run['llm_enabled'] else 'rules (no LLM key configured)'}.",
        "All findings are inferred; none are human-verified."] if run["evidence"] else []})
    return {"title": "Data Archaeology Report", "run_id": run["run_id"], "objective": run["objective"],
            "generated": datetime.now().isoformat(timespec="seconds"), "narrative": run["narrative"],
            "sections": [s for s in S if s["items"]], "lineage": lin, "hypotheses": run["hypotheses"],
            "anomalies": run["anomalies"], "recommended_actions": acts}


def render_markdown(r: dict) -> str:
    out = [f"# {r['title']}", f"*Run {r['run_id']} · {r['generated']}*", f"**Objective:** {r['objective']}", ""]
    for s in r["sections"]:
        out += [f"## {s['title']}"] + [f"- {i}" for i in s["items"]] + [""]
    return "\n".join(out)


def render_pdf(r: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    st, buf = getSampleStyleSheet(), io.BytesIO()
    fl = [Paragraph(escape(r["title"]), st["Title"]),
          Paragraph(escape(f"Run {r['run_id']} | {r['generated']}"), st["Normal"]),
          Paragraph(escape(f"Objective: {r['objective']}"), st["Normal"]), Spacer(1, 12)]
    for s in r["sections"]:
        fl.append(Paragraph(escape(s["title"]), st["Heading2"]))
        fl += [Paragraph("• " + escape(str(i)), st["BodyText"]) for i in s["items"]]
    SimpleDocTemplate(buf, pagesize=A4, title=r["title"]).build(fl)
    return buf.getvalue()