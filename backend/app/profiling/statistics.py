import re
import pandas as pd


def _py(v):
    return v.item() if hasattr(v, "item") else v


def base_type(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s): return "boolean"
    if pd.api.types.is_integer_dtype(s): return "integer"
    if pd.api.types.is_float_dtype(s): return "float"
    if pd.api.types.is_datetime64_any_dtype(s): return "datetime"
    return "string"


def shape_pattern(v) -> str:
    v = str(v)[:30]
    return re.sub(r"[a-z]+", "a", re.sub(r"[A-Z]+", "A", re.sub(r"\d+", "9", v)))


def column_stats(s: pd.Series, semantic: str) -> dict:
    n = len(s)
    nn = s.dropna()
    unique = int(nn.nunique())
    ratio = unique / len(nn) if len(nn) else 0
    st = {
        "dtype": base_type(s),
        "row_count": n,
        "null_count": int(s.isna().sum()),
        "null_pct": round(float(s.isna().mean() * 100), 2) if n else 0.0,
        "unique_count": unique,
        "duplicate_count": int(len(nn) - unique),
        "unique_ratio": round(ratio, 4),
        "cardinality": "unique" if ratio > 0.98 else "high" if ratio > 0.5 else "medium" if unique > 20 else "low",
        "top_values": {str(k): int(v) for k, v in nn.astype(str).value_counts().head(5).items()},
    }
    if len(nn):
        st["top_patterns"] = {k: int(v) for k, v in nn.map(shape_pattern).value_counts().head(3).items()}
    if base_type(s) in ("integer", "float") and len(nn):
        q1, q3 = nn.quantile(0.25), nn.quantile(0.75)
        iqr = q3 - q1
        outliers = int(((nn < q1 - 3 * iqr) | (nn > q3 + 3 * iqr)).sum()) if iqr > 0 else 0
        skew = float(nn.skew()) if len(nn) > 2 else 0.0
        st.update(min=_py(nn.min()), max=_py(nn.max()), mean=round(float(nn.mean()), 4),
                  std=round(float(nn.std() or 0), 4), skew=round(skew, 3), extreme_outliers=outliers,
                  distribution="skewed" if abs(skew) > 1 else "roughly_symmetric")
    elif semantic == "date":
        parsed = pd.to_datetime(nn, errors="coerce", format="mixed")
        st["invalid_dates"] = int(parsed.isna().sum())
        if parsed.notna().any():
            st.update(min=str(parsed.min()), max=str(parsed.max()))
    elif len(nn):
        L = nn.astype(str).str.len()
        st.update(min_length=int(L.min()), max_length=int(L.max()))
    return st