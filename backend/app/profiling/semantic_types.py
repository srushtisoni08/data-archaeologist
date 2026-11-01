import re
import pandas as pd

PATTERNS = {
    "email": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$"),
    "url": re.compile(r"^https?://", re.I),
    "uuid": re.compile(r"^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$", re.I),
    "ip_address": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
    "phone": re.compile(r"^(?!\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$)\+?[\d\s().-]{8,16}$"),
    "currency": re.compile(r"^[$₹€£]\s?-?[\d,]+(\.\d+)?$"),
    "boolean": re.compile(r"^(true|false|yes|no|y|n|0|1)$", re.I),
}
NAME_HINTS = {
    "identifier": ("id", "ref", "no", "num", "code", "key", "uuid", "sku"),
    "person_name": ("name", "fullname"),
    "geo_location": ("city", "state", "country", "address", "zip", "pincode", "location", "region"),
    "date": ("date", "created", "joined", "updated", "_at", "dob"),
    "currency": ("amount", "price", "total", "cost", "spent", "revenue", "salary"),
    "status": ("status", "state_flag", "type", "category"),
}
THRESHOLD = 0.8


def _hint(col: str) -> str | None:
    c = col.lower()
    for t, keys in NAME_HINTS.items():
        if any(k in c for k in keys):
            return t
    return None


def detect_semantic_type(col: str, s: pd.Series) -> tuple[str, float]:
    s = s.dropna()
    if s.empty:
        return "unknown", 0.0
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date", 1.0
    if pd.api.types.is_bool_dtype(s):
        return "boolean", 1.0
    sample = s.sample(min(len(s), 500), random_state=0)
    strs = sample.astype(str).str.strip()
    hint = _hint(col)

    if not pd.api.types.is_numeric_dtype(s):
        for t, pat in PATTERNS.items():
            ratio = strs.map(lambda v: bool(pat.match(v))).mean()
            if ratio >= THRESHOLD:
                return t, round(float(ratio), 3)
        if strs.str.contains(r"\d").mean() > THRESHOLD and strs.str.contains(r"[-/:]").mean() > THRESHOLD:
            parsed = pd.to_datetime(strs, errors="coerce", format="mixed")
            ratio = parsed.notna().mean()
            if ratio >= THRESHOLD:
                return "date", round(float(ratio), 3)

    unique_ratio = s.nunique() / len(s)
    if hint == "identifier" and (unique_ratio > 0.5 or pd.api.types.is_integer_dtype(s) or s.nunique() > 20):
        return "identifier", 0.8
    if hint in ("person_name", "geo_location") and not pd.api.types.is_numeric_dtype(s):
        return hint, 0.7
    if hint == "currency" and pd.api.types.is_numeric_dtype(s):
        return "currency", 0.7
    if s.nunique() <= 20 and len(s) > 20 and unique_ratio < 0.1:
        return "status" if hint == "status" else "category", 0.6
    if pd.api.types.is_integer_dtype(s) and unique_ratio > 0.95:
        return "identifier", 0.6
    return ("numeric" if pd.api.types.is_numeric_dtype(s) else "text"), 0.5