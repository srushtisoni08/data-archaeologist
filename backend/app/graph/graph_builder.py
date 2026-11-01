import networkx as nx
from app.database import store
from app.reporting.report_generator import lineage_for_run


def _ev(run, tool):
    e = next((x for x in run["evidence"] if x["tool"] == tool and "error" not in x["result"]), None)
    return e["result"] if e else {}


def build_graph(run: dict) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    profs = {p["dataset_id"]: p for p in store.list_profiles() if p.get("ingestion_status") == "completed"}
    anoms = run["anomalies"]

    for ds, p in profs.items():
        G.add_node(ds, kind="dataset", label=p["filename"], rows=p["row_count"],
                   quality=p["fingerprint"]["quality_score"],
                   issues=p["fingerprint"]["quality_issues"],
                   anomalies=[a for a in anoms if a["dataset_id"] == ds])
        for c in p["columns"]:
            cid = f"{ds}.{c['name']}"
            G.add_node(cid, kind="column", label=c["name"], dataset=ds, semantic_type=c["semantic_type"],
                       dtype=c["dtype"], unique_ratio=c["unique_ratio"], null_pct=c["null_pct"],
                       anomalies=[a for a in anoms if a["dataset_id"] == ds and a["column"] == c["name"]])
            G.add_edge(ds, cid, rel="contains", provenance="observed", confidence=1.0)

    for m in _ev(run, "find_column_matches").get("matches", []):
        G.add_edge(f"{m['source_dataset']}.{m['source_column']}", f"{m['target_dataset']}.{m['target_column']}",
                   rel="semantically_matches", provenance="inferred", confidence=m["confidence"],
                   evidence=m["evidence"], needs_review=m["needs_review"])

    for h in run["hypotheses"]:
        if h["type"] == "foreign_key" and "(one_to_one)" not in h["claim"]:
            d = h.get("details") or {}
            if d.get("source"):
                G.add_edge(d["source"], d["target"], rel="references", provenance="inferred",
                           confidence=h["confidence"], status=h["status"], evidence=d,
                           notes=h["notes"], hypothesis=h["id"], needs_review=h["needs_review"])
        elif h["type"] == "entity_match":
            eid = h["claim"].split(":")[0]
            G.add_node(eid, kind="entity", label=eid, claim=h["claim"], status=h["status"],
                       confidence=h["confidence"], notes=h["notes"])
    ents = _ev(run, "resolve_entities").get("entities", [])
    for ent in ents:
        if len(ent["records"]) < 2:
            continue
        for r in ent["records"]:
            ds = r["dataset_id"]
            G.add_edge(ent["entity_id"], ds, rel="appears_in", provenance="inferred",
                       confidence=min(l["score"] for l in ent["links"]), record=r["key"])

    lin = lineage_for_run(run)
    for e in lin["edges"]:
        G.add_edge(e["target"], e["source"], rel="derived_from", provenance="inferred",
                   confidence=e["direction_confidence"], relatedness=e["relatedness"],
                   transformations=e["transformations"], evidence=e["evidence"], caveat=e["caveat"])
    for t in lin["temporal_hints"]:
        G.graph.setdefault("hints", []).append(t)

    for h in run["hypotheses"]:
        if h["type"] == "contradiction":
            c = next((x for x in _ev(run, "detect_contradictions").get("contradictions", [])
                      if x["file_a"] in h["claim"] and x["file_b"] in h["claim"]), None)
            if c:
                G.add_edge(f"{c['dataset_a']}.{c['column_a']}", f"{c['dataset_b']}.{c['column_b']}",
                           rel="conflicts_with", provenance="inferred", confidence=None,
                           conflicts=c["conflicts"], notes=h["notes"], needs_review=True)
    return G    