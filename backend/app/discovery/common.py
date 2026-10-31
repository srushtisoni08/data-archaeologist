from functools import lru_cache
from pathlib import Path
import pandas as pd
from app.database import store
from app.ingestion.loader import load_dataframe


@lru_cache(maxsize=32)
def get_df(dataset_id: str) -> pd.DataFrame:
    rec = store.load_profile(dataset_id)
    df, _ = load_dataframe(Path(rec["stored_path"]))
    return df


def norm_values(dataset_id: str, col: str) -> pd.Series:
    """Non-null values normalised to comparable strings (1.0 -> '1', ' A ' -> 'a')."""
    s = get_df(dataset_id)[col].dropna()
    if pd.api.types.is_float_dtype(s) and len(s) and (s == s.round()).all():
        s = s.astype("int64")
    return s.astype(str).str.strip().str.lower()


def completed(profiles: list[dict]) -> list[dict]:
    return [p for p in profiles if p.get("ingestion_status") == "completed"]