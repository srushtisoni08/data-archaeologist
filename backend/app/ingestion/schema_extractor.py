import hashlib
from pathlib import Path
from app.ingestion.loader import load_dataframe
from app.profiling.profiler import profile_dataframe
from app.profiling.fingerprint import build_fingerprint


def ingest(path: Path, dataset_id: str, original_name: str) -> dict:
    record = {"dataset_id": dataset_id, "filename": original_name,
              "stored_path": str(path), "size_bytes": path.stat().st_size,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    try:
        df, meta = load_dataframe(path)
        cols = profile_dataframe(df)
        record.update(meta, row_count=len(df), column_count=len(df.columns),
                      columns=cols, sample=df.head(5).astype(str).to_dict("records"),
                      fingerprint=build_fingerprint(df, cols), ingestion_status="completed")
    except Exception as e:
        record.update(ingestion_status="failed", error=str(e))
    return record