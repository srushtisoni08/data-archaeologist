import json
from app.config import PROFILES, STORAGE


def next_dataset_id() -> str:
    return f"ds_{len(list(PROFILES.glob('ds_*.json'))) + 1:03d}"


def save_profile(dataset_id: str, data: dict) -> None:
    (PROFILES / f"{dataset_id}.json").write_text(json.dumps(data, indent=2, default=str))


def load_profile(dataset_id: str) -> dict | None:
    p = PROFILES / f"{dataset_id}.json"
    return json.loads(p.read_text()) if p.exists() else None


def list_profiles() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(PROFILES.glob("ds_*.json"))]


def save_json(name: str, data) -> None:
    (STORAGE / f"{name}.json").write_text(json.dumps(data, indent=2, default=str))


def load_json(name: str, default=None):
    p = STORAGE / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else default