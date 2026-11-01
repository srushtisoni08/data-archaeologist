import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import ORIGINALS, PROFILES
from app.database import store
from app.discovery.common import get_df
from app.ingestion.schema_extractor import ingest

router = APIRouter(tags=["datasets"])


@router.post("/uploads")
async def upload(files: list[UploadFile] = File(...)):
    results = []
    for f in files:
        ds_id = store.next_dataset_id()
        dest = ORIGINALS / f"{ds_id}_{Path(f.filename).name}"
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        dest.chmod(0o444)
        rec = ingest(dest, ds_id, f.filename)
        store.save_profile(ds_id, rec)
        get_df.cache_clear()
        results.append({k: rec.get(k) for k in
                        ("dataset_id", "filename", "format", "row_count", "column_count", "ingestion_status", "error")})
    return results


@router.get("/datasets")
def datasets():
    return [{k: d.get(k) for k in ("dataset_id", "filename", "format", "row_count", "column_count", "ingestion_status")}
            for d in store.list_profiles()]


@router.get("/datasets/{dataset_id}")
def dataset(dataset_id: str):
    d = store.load_profile(dataset_id)
    if not d:
        raise HTTPException(404, "Dataset not found")
    return d


@router.delete("/datasets")
def reset():
    for p in list(PROFILES.glob("ds_*.json")) + list(ORIGINALS.glob("*")):
        p.chmod(0o666)
        p.unlink()
    get_df.cache_clear()
    return {"status": "reset"}