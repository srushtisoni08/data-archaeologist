import re
from collections import defaultdict
import pandas as pd
from app.discovery.common import get_df, completed

TOL = 1e-6
MAX_CONFLICTS = 10


def _py(v):
    return v.item() if hasattr(v, "item") else v


def _eq(a, b) -> bool:
    try:
        x, y = float(a), float(b)
        return abs(x - y) <= TOL * max(1.0, abs(x))
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


def version_rank(filename: str) -> tuple:
    f = filename.lower()
    years = [int(y) for y in re.findall(r"(20\d\d)", f)]
    r = 0
    m = re.search(r"(?:^|[_\-\s.])v(\d+)", f)
    if m:
        r += int(m.group(1))
    r -= sum(w in f for w in ("old", "backup", "raw", "orig", "draft"))
    r += sum(w in f for w in ("final", "new", "latest", "updated", "clean"))
    return (max(years, default=0), r)


def _keyed(ds: str, key: str, col: str) -> pd.Series:
    df = get_df(ds)[[key, col]].dropna(subset=[key]).copy()
    k = df[key]
    if pd.api.types.is_float_dtype(k) and (k == k.round()).all():
        k = k.astype("int64")
    df["k"] = k.astype(str).str.strip().str.lower()
    return df.drop_duplicates("k", keep=False).set_index("k")[col]


def detect_contradictions(profiles: list[dict], discovery: dict) -> list[dict]:
    names = {p["dataset_id"]: p["filename"] for p in completed(profiles)}
    by_pair = defaultdict(list)
    for m in discovery["column_matches"]:
        by_pair[(m["source_dataset"], m["target_dataset"])].append(m)

    out, seen = [], set()
    for rel in discovery["relationships"]:
        # only 1:1 key links: otherwise rows are not comparable one-to-one
        if rel["relationship_type"] != "possible_foreign_key" or rel["cardinality"] != "one_to_one":
            continue
        pair = tuple(sorted((rel["source_dataset"], rel["target_dataset"])))
        if pair in seen:
            continue
        seen.add(pair)
        a, b = pair
        ka, kb = ((rel["source_column"], rel["target_column"]) if rel["source_dataset"] == a
                  else (rel["target_column"], rel["source_column"]))
        cols = []
        for m in by_pair.get(pair, []):
            if m["confidence"] < 0.8:
                continue
            ca, cb = ((m["source_column"], m["target_column"]) if m["source_dataset"] == a
                      else (m["target_column"], m["source_column"]))
            if ca == ka or cb == kb:
                continue
            sa, sb = _keyed(a, ka, ca), _keyed(b, kb, cb)
            cols.append((ca, cb, sa, sb, sa.index.intersection(sb.index)))

        ra, rb = version_rank(names[a]), version_rank(names[b])
        newer = a if ra > rb else b if rb > ra else None

        for ca, cb, sa, sb, common in cols:
            bad = []
            for k in common:
                x, y = sa[k], sb[k]
                if pd.isna(x) or pd.isna(y) or _eq(x, y):
                    continue
                agree = sum(1 for oa, ob, osa, osb, oc in cols
                            if (oa, ob) != (ca, cb) and k in oc
                            and not pd.isna(osa[k]) and not pd.isna(osb[k]) and _eq(osa[k], osb[k]))
                bad.append({"key": k, "value_a": _py(x), "value_b": _py(y),
                            "other_fields_agreeing": f"{agree}/{len(cols) - 1}"})
            if not bad:
                continue
            rate = len(bad) / max(len(common), 1)
            out.append({
                "dataset_a": a, "file_a": names[a], "column_a": ca,
                "dataset_b": b, "file_b": names[b], "column_b": cb,
                "key_columns": {a: ka, b: kb},
                "compared": len(common), "conflict_count": len(bad), "conflict_rate": round(rate, 3),
                "conflicts": bad[:MAX_CONFLICTS],
                "likely_newer_dataset": newer,
                "assessment": (f"Differences may be updates: {names[newer]} looks newer by filename "
                               f"(inferred, low confidence; file timestamps are not preserved on upload)."
                               if newer else "No ordering evidence between the files; cannot tell which value is current."),
                "requires_human": newer is None or rate > 0.2,
                "status": "inferred",
            })
    return sorted(out, key=lambda c: -c["conflict_rate"])