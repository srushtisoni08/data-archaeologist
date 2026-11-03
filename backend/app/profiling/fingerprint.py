import hashlib
import pandas as pd


def build_fingerprint(df: pd.DataFrame, columns: list[dict]) -> dict:
    schema = sorted((c["name"].lower(), c["dtype"]) for c in columns)
    schema_hash = hashlib.sha1(str(schema).encode()).hexdigest()[:16]
    n = max(len(df), 1)
    dup_rows = int(df.duplicated().sum())
    avg_null = sum(c["null_pct"] for c in columns) / max(len(columns), 1)
    issues = []
    for c in columns:
        if c["null_pct"] > 20: issues.append(f"{c['name']}: {c['null_pct']}% nulls")
        if c.get("invalid_dates"): issues.append(f"{c['name']}: {c['invalid_dates']} invalid dates")
        if c.get("extreme_outliers"): issues.append(f"{c['name']}: {c['extreme_outliers']} extreme outliers")
    quality = max(0.0, 100 - avg_null - (dup_rows / n * 100) - 2 * len(issues))
    return {
        "schema_hash": schema_hash,
        "duplicate_rows": dup_rows,
        "candidate_keys": [c["name"] for c in columns if c["unique_ratio"] == 1.0 and c["null_count"] == 0],
        "semantic_summary": {t: sum(1 for c in columns if c["semantic_type"] == t)
                             for t in {c["semantic_type"] for c in columns}},
        "quality_score": round(quality, 1),
        "quality_issues": issues,
    }