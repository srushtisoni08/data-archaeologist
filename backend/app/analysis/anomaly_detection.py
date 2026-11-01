import pandas as pd
from app.discovery.common import get_df, completed

N = 5
ORDER = {"high": 0, "medium": 1, "low": 2}


def _dt(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce")
    return pd.to_datetime(s.astype(str), errors="coerce", format="mixed")


def _add(out, ds, col, kind, sev, count, examples, detail):
    out.append({"dataset_id": ds, "column": col, "type": kind, "severity": sev,
                "count": int(count), "examples": [str(e) for e in list(examples)[:N]],
                "detail": detail, "status": "inferred"})


def detect_anomalies(profiles: list[dict], relationships: list[dict]) -> list[dict]:
    out, now = [], pd.Timestamp.now()
    for p in completed(profiles):
        ds, df = p["dataset_id"], get_df(p["dataset_id"])
        d = int(df.duplicated().sum())
        if d:
            _add(out, ds, None, "duplicate_rows", "medium", d, [], f"{d} fully duplicated rows")
        for c in p["columns"]:
            name, sem = c["name"], c["semantic_type"]
            nn = df[name].dropna()
            if nn.empty:
                continue
            if c["null_pct"] > 20:
                _add(out, ds, name, "high_null_rate", "medium", c["null_count"], [],
                     f"{c['null_pct']}% of values are null")
            if sem == "date":
                dt = _dt(nn)
                bad = nn[dt.isna()]
                if len(bad):
                    _add(out, ds, name, "invalid_date", "high", len(bad), bad, "Values that cannot be parsed as dates")
                fut = nn[dt > now]
                if len(fut):
                    _add(out, ds, name, "future_date", "medium", len(fut), fut, "Dates later than today")
            if pd.api.types.is_numeric_dtype(nn) and sem != "identifier":
                if sem == "currency" and (nn < 0).any():
                    neg = nn[nn < 0]
                    _add(out, ds, name, "negative_amount", "high", len(neg), neg, "Negative monetary values")
                q1, q3 = nn.quantile(0.25), nn.quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    o = nn[(nn < q1 - 3 * iqr) | (nn > q3 + 3 * iqr)]
                    if len(o):
                        _add(out, ds, name, "extreme_outlier", "medium", len(o), o, "Beyond 3x IQR from quartiles")
            if sem == "identifier" and 0.9 <= c["unique_ratio"] < 1:
                dups = nn[nn.duplicated(keep=False)].unique()
                _add(out, ds, name, "duplicate_identifier", "high", len(dups), dups,
                     "Identifier column is almost unique but has repeats")
    for r in relationships:
        e = r["evidence"]
        if r["relationship_type"] == "possible_foreign_key" and r["cardinality"] == "one_to_many" \
           and e["orphan_values"] and e.get("parent_semantic_type") == "identifier":        
            _add(out, r["target_dataset"], r["target_column"], "broken_reference",
                 "high" if e["referential_coverage"] >= 0.9 else "medium", e["orphan_values"],
                 e["orphan_examples"],
                 f"Values not found in {r['source_dataset']}.{r['source_column']} (coverage {e['referential_coverage']})")
    return sorted(out, key=lambda a: ORDER[a["severity"]])