from collections import Counter
from app.database import store
from app.discovery.common import completed, norm_values
from app.discovery.schema_matching import match_columns
from app.discovery.relationship_detection import detect_relationships as _rels
from app.discovery.entity_resolution import resolve_entities as _ents
from app.analysis.anomaly_detection import detect_anomalies as _anoms
from app.analysis.contradiction_detection import detect_contradictions as _contras


class Ctx:
    def __init__(self):
        self.profiles = completed(store.list_profiles())
        self._c = {}

    def _get(self, k, fn):
        if k not in self._c:
            self._c[k] = fn()
        return self._c[k]

    def matches(self): return self._get("m", lambda: match_columns(self.profiles))
    def rels(self): return self._get("r", lambda: _rels(self.profiles))
    def prof(self, ds): return next((p for p in self.profiles if p["dataset_id"] == ds), None)


def inspect_dataset(ctx, dataset_id):
    p = ctx.prof(dataset_id)
    if not p:
        return {"error": f"unknown dataset {dataset_id}"}, f"unknown dataset {dataset_id}"
    fp = p["fingerprint"]
    res = {"dataset_id": dataset_id, "filename": p["filename"], "rows": p["row_count"],
           "columns": [{k: c[k] for k in ("name", "semantic_type", "dtype", "unique_ratio", "null_pct")}
                       for c in p["columns"]],
           "candidate_keys": fp["candidate_keys"], "quality_score": fp["quality_score"],
           "quality_issues": fp["quality_issues"]}
    return res, (f"{p['filename']}: {p['row_count']} rows, {p['column_count']} cols, "
                 f"candidate keys {fp['candidate_keys']}, quality {fp['quality_score']}")


def find_column_matches(ctx):
    m = ctx.matches()
    top = ", ".join(f"{x['source_dataset']}.{x['source_column']}~{x['target_dataset']}.{x['target_column']}"
                    f"({x['confidence']})" for x in m[:3])
    return {"count": len(m), "matches": m[:50]}, f"{len(m)} column matches; top: {top or 'none'}"


def detect_relationships(ctx):
    r = ctx.rels()
    top = ", ".join(f"{x['source_dataset']}.{x['source_column']}->{x['target_dataset']}.{x['target_column']}"
                    f"({x['confidence']})" for x in r[:3])
    return {"count": len(r), "relationships": r}, f"{len(r)} candidate key relationships; top: {top or 'none'}"


def validate_hypothesis(ctx, source_dataset, source_column, target_dataset, target_column):
    sp, tp = ctx.prof(source_dataset), ctx.prof(target_dataset)
    if not sp or not tp or source_column not in {c["name"] for c in sp["columns"]} \
       or target_column not in {c["name"] for c in tp["columns"]}:
        return {"error": "unknown dataset or column"}, "invalid hypothesis arguments"
    parent, child = norm_values(source_dataset, source_column), norm_values(target_dataset, target_column)
    pv = set(parent)
    cov = float(child.isin(pv).mean()) if len(child) else 0.0
    uniq = parent.nunique() / len(parent) if len(parent) else 0.0
    orphans = list(child[~child.isin(pv)].unique())[:20]
    elsewhere = []
    for p in ctx.profiles:
        for c in p["columns"]:
            if (p["dataset_id"], c["name"]) in {(source_dataset, source_column), (target_dataset, target_column)}:
                continue
            if c["unique_ratio"] < 0.98 or not orphans:
                continue
            found = [o for o in orphans if o in set(norm_values(p["dataset_id"], c["name"]))]
            if found:
                elsewhere.append({"dataset": p["dataset_id"], "column": c["name"], "values": found})
    parent_column_profile = next(c for c in sp["columns"] if c["name"] == source_column)
    parent_complete = parent_column_profile["null_count"] == 0
    parent_is_unique = uniq == 1.0 and parent_complete
    verdict = ("supported" if cov >= 0.95 and parent_is_unique else
               "partially_supported" if cov >= 0.5 and parent_is_unique else "rejected")
    res = {"source": f"{source_dataset}.{source_column}", "target": f"{target_dataset}.{target_column}",
           "coverage": round(cov, 3), "parent_uniqueness": round(uniq, 3), "child_rows": int(len(child)),
           "orphan_count": len(orphans), "orphan_examples": orphans[:5],
           "orphans_found_elsewhere": elsewhere, "verdict": verdict,
           "confidence": round(0.7 * cov + 0.3 * uniq, 3)}
    s = f"{res['source']} -> {res['target']}: coverage {res['coverage']}, uniqueness {res['parent_uniqueness']}, {verdict}"
    if elsewhere:
        s += f"; orphans also found in {elsewhere[0]['dataset']}.{elsewhere[0]['column']}"
    return res, s


def resolve_entities(ctx):
    r = _ents(ctx.profiles)
    n = sum(e["status"] != "same_entity" for e in r["entities"])
    return r, f"{len(r['entities'])} entity clusters, {n} need review"


def detect_anomalies(ctx):
    a = _anoms(ctx.profiles, ctx.rels())
    c = Counter(x["type"] for x in a)
    return {"anomalies": a}, f"{len(a)} anomalies: {dict(c)}"


def detect_contradictions(ctx):
    c = _contras(ctx.profiles, {"column_matches": ctx.matches(), "relationships": ctx.rels()})
    return {"contradictions": c}, f"{len(c)} contradictions: " + "; ".join(
        f"{x['file_a']} vs {x['file_b']} on {x['column_a']} ({x['conflict_count']}/{x['compared']})" for x in c[:3])


REGISTRY = {
    "inspect_dataset": {"fn": inspect_dataset, "args": ["dataset_id"],
                        "desc": "Schema, semantic types, candidate keys and quality of one dataset"},
    "find_column_matches": {"fn": find_column_matches, "args": [],
                            "desc": "Find semantically similar columns across datasets"},
    "detect_relationships": {"fn": detect_relationships, "args": [],
                             "desc": "Find candidate primary/foreign key relationships"},
    "validate_hypothesis": {"fn": validate_hypothesis,
                            "args": ["source_dataset", "source_column", "target_dataset", "target_column"],
                            "desc": "Test a parent->child key relationship: coverage, uniqueness, orphans"},
    "resolve_entities": {"fn": resolve_entities, "args": [],
                         "desc": "Find records that may be the same real-world entity"},
    "detect_anomalies": {"fn": detect_anomalies, "args": [],
                         "desc": "Invalid dates, negatives, outliers, duplicate ids, broken references"},
    "detect_contradictions": {"fn": detect_contradictions, "args": [],
                              "desc": "Conflicting values for the same key across files"},
}