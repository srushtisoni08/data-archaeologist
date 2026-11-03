from collections import defaultdict
from itertools import permutations
from app.discovery.common import norm_values, completed
from app.discovery.schema_matching import name_sim

MIN_COVERAGE = 0.5
SKIP_SEMANTIC = {"boolean", "category", "status"}
SKIP_PARENT = SKIP_SEMANTIC | {"geo_location", "person_name", "date", "currency"}


def _group(dtype: str) -> str:
    return "num" if dtype in ("integer", "float") else dtype


def _mark_dominated(out: list[dict], pv: dict) -> None:
    key = lambda r: (r["source_dataset"], r["source_column"], r["target_dataset"], r["target_column"])
    by_key = {key(r): r for r in out}
    # version pairs: 1:1 key link AND the key columns share (nearly) the same name
    versions = {frozenset((r["source_dataset"], r["target_dataset"])) for r in out
                if r["cardinality"] == "one_to_one" and r["evidence"]["name_similarity"] >= 0.9}
    by_child = defaultdict(list)
    for r in out:
        by_child[(r["target_dataset"], r["target_column"])].append(r)
    for r in out:
        cov = r["evidence"]["referential_coverage"]
        rev = by_key.get((r["target_dataset"], r["target_column"], r["source_dataset"], r["source_column"]))
        if rev and rev["evidence"]["referential_coverage"] > cov:
            r["dominated_by"] = f"reverse direction {rev['source_dataset']}.{rev['source_column']}"
            continue
        sp = pv[(r["source_dataset"], r["source_column"])]
        for q in by_child[(r["target_dataset"], r["target_column"])]:
            qp = pv[(q["source_dataset"], q["source_column"])]
            if (q is not r and sp < qp and q["evidence"]["referential_coverage"] > cov
                    and frozenset((r["source_dataset"], q["source_dataset"])) not in versions):
                r["dominated_by"] = f"{q['source_dataset']}.{q['source_column']}"
                break


def detect_relationships(profiles: list[dict]) -> list[dict]:
    profiles = completed(profiles)
    out, pv = [], {}
    for parent, child in permutations(profiles, 2):
        for pc in parent["columns"]:
            if pc["unique_ratio"] < 1.0 or pc["null_count"] > 0 or pc["unique_count"] < 2 \
               or pc["semantic_type"] in SKIP_PARENT:
                continue
            pvals = set(norm_values(parent["dataset_id"], pc["name"]))
            pv[(parent["dataset_id"], pc["name"])] = pvals
            for cc in child["columns"]:
                if _group(pc["dtype"]) != _group(cc["dtype"]) or cc["semantic_type"] in SKIP_SEMANTIC:
                    continue
                cvals = norm_values(child["dataset_id"], cc["name"])
                if cvals.empty:
                    continue
                matched = cvals.isin(pvals)
                coverage = float(matched.mean())
                if coverage < MIN_COVERAGE:
                    continue
                nsim = name_sim(pc["name"], cc["name"])
                conf = 0.65 * coverage + 0.20 * pc["unique_ratio"] + 0.15 * nsim
                orphans = cvals[~matched].unique()
                out.append({
                    "source_dataset": parent["dataset_id"], "source_column": pc["name"],
                    "target_dataset": child["dataset_id"], "target_column": cc["name"],
                    "relationship_type": "possible_foreign_key",
                    "cardinality": "one_to_one" if cc["unique_ratio"] == 1.0 and cc["null_count"] == 0 else "one_to_many",
                    "confidence": round(conf, 3),
                    "evidence": {
                        "referential_coverage": round(coverage, 3),
                        "parent_uniqueness": pc["unique_ratio"],
                        "parent_distinct_values": len(pvals),
                        "child_rows": int(len(cvals)),
                        "orphan_values": len(orphans),
                        "orphan_examples": [str(v) for v in orphans[:5]],
                        "name_similarity": round(nsim, 3),
                        "type_compatible": True,
                        "parent_semantic_type": pc["semantic_type"],
                    },
                    "status": "inferred",
                    "needs_review": coverage < 1.0 or conf < 0.8,
                })
    _mark_dominated(out, pv)
    return sorted(out, key=lambda r: -r["confidence"])