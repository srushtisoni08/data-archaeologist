from collections import defaultdict
import pandas as pd
from app.discovery.common import norm_values, completed
from app.analysis.contradiction_detection import version_rank, _keyed, _eq

CAVEAT = ("Inferred from file contents and file names only. Direction is not proven: "
          "no ETL logs, SQL or reliable timestamps are available (observed lineage: none).")


def _edge(profs, ms, a, b, ka, kb):
    pa, pb = profs[a], profs[b]
    A, B = set(norm_values(a, ka)), set(norm_values(b, kb))
    common = A & B
    oa, ob = len(common) / max(len(A), 1), len(common) / max(len(B), 1)
    good = [m for m in ms if m["confidence"] >= 0.8]
    ma, mb = {m["source_column"] for m in good}, {m["target_column"] for m in good}
    jac = len(good) / max(len(pa["columns"]) + len(pb["columns"]) - len(good), 1)

    changed, fmt, cells = defaultdict(int), defaultdict(int), 0
    for m in good:
        ca, cb = m["source_column"], m["target_column"]
        if ca == ka or cb == kb:
            continue
        sa, sb = _keyed(a, ka, ca), _keyed(b, kb, cb)
        for k in sa.index.intersection(sb.index):
            x, y = sa[k], sb[k]
            if pd.isna(x) or pd.isna(y):
                continue
            cells += 1
            if not _eq(x, y):
                changed[ca] += 1
            elif str(x) != str(y):
                fmt[ca] += 1
    agreement = 1 - sum(changed.values()) / cells if cells else 1.0
    relatedness = 0.4 * max(oa, ob) + 0.4 * jac + 0.2 * agreement

    ra, rb = version_rank(pa["filename"]), version_rank(pb["filename"])
    directed = ra != rb
    src, dst = (b, a) if rb < ra else (a, b)
    sk, dk = (A, B) if src == a else (B, A)
    only_dst, only_src = dk - sk, sk - dk
    sq, dq = profs[src]["fingerprint"]["quality_score"], profs[dst]["fingerprint"]["quality_score"]
    dir_conf = 0.0
    if directed:
        dir_conf = 0.55 + (0.1 if only_dst and not only_src else 0) + (0.1 if dq > sq else 0)

    t = []
    if only_dst:
        t.append(f"{len(only_dst)} keys only in {dst}, e.g. {sorted(only_dst)[:3]} (additions if {dst} is later)")
    if only_src:
        t.append(f"{len(only_src)} keys of {src} missing in {dst}, e.g. {sorted(only_src)[:3]} (filtering/removal if {dst} is later)")
    if profs[src]["row_count"] != profs[dst]["row_count"]:
        t.append(f"row count {profs[src]['row_count']} -> {profs[dst]['row_count']}")
    if changed:
        t.append("values differ on shared records: " + ", ".join(f"{c}={n}" for c, n in changed.items()))
    if fmt:
        t.append("representation-only differences (same value, different text): " + ", ".join(f"{c}={n}" for c, n in fmt.items()))
    only_cols = {a: [c["name"] for c in pa["columns"] if c["name"] not in ma],
                 b: [c["name"] for c in pb["columns"] if c["name"] not in mb]}
    if any(only_cols.values()):
        t.append(f"unmatched columns: {only_cols}")
    if dq != sq:
        t.append(f"quality score {sq} -> {dq}")

    return {"source": src, "target": dst, "type": "inferred_derivation" if directed else "related_versions",
            "relatedness": round(relatedness, 3), "direction_confidence": round(dir_conf, 3),
            "evidence": {"key_columns": {a: ka, b: kb}, "key_overlap": {a: round(oa, 3), b: round(ob, 3)},
                         "schema_overlap": round(jac, 3), "shared_cells": cells,
                         "changed_cells": sum(changed.values()),
                         "filename_order": f"{pa['filename'] if src == a else pb['filename']} looks older than "
                                           f"{pb['filename'] if src == a else pa['filename']}" if directed
                                           else "no ordering signal in filenames"},
            "transformations": t, "provenance": "inferred", "caveat": CAVEAT}


def _temporal(rels):
    g = defaultdict(list)
    for r in rels:
        if (r["relationship_type"] == "possible_foreign_key" and r["cardinality"] == "one_to_many"
                and r["evidence"].get("parent_semantic_type") == "identifier"):
            g[(r["target_dataset"], r["target_column"])].append(r)
    out = []
    for (t, c), rs in g.items():
        rs.sort(key=lambda r: -r["evidence"]["referential_coverage"])
        best, worst = rs[0], rs[-1]
        cb, cw = best["evidence"]["referential_coverage"], worst["evidence"]["referential_coverage"]
        if len(rs) > 1 and cb - cw >= 0.2:
            out.append({"child": f"{t}.{c}", "aligns_with": f"{best['source_dataset']}.{best['source_column']}",
                        "coverage": cb, "versus": f"{worst['source_dataset']}.{worst['source_column']}",
                        "coverage_versus": cw,
                        "interpretation": "child records appear to have been created against the better-matching "
                                          "parent version (inferred)"})
    return out


def infer_lineage(profiles: list[dict], discovery: dict) -> dict:
    profs = {p["dataset_id"]: p for p in completed(profiles)}
    ms = defaultdict(list)
    for m in discovery["column_matches"]:
        ms[(m["source_dataset"], m["target_dataset"])].append(m)
    edges, seen = [], set()
    for r in discovery["relationships"]:
        if r["relationship_type"] != "possible_foreign_key" or r["cardinality"] != "one_to_one":
            continue
        a, b = sorted((r["source_dataset"], r["target_dataset"]))
        if (a, b) in seen:
            continue
        seen.add((a, b))
        ka, kb = ((r["source_column"], r["target_column"]) if r["source_dataset"] == a
                  else (r["target_column"], r["source_column"]))
        edges.append(_edge(profs, ms[(a, b)], a, b, ka, kb))
    return {"edges": sorted(edges, key=lambda e: -e["relatedness"]), "observed": [],
            "temporal_hints": _temporal(discovery["relationships"]), "caveat": CAVEAT}