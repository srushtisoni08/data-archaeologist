import pandas as pd
from .semantic_types import detect_semantic_type
from .statistics import column_stats


def profile_dataframe(df: pd.DataFrame) -> list[dict]:
    out = []
    for col in df.columns:
        s = df[col]
        sem, conf = detect_semantic_type(col, s)
        out.append({"name": col, "semantic_type": sem, "semantic_confidence": conf,
                    **column_stats(s, sem)})
    return out