import re
from itertools import combinations
import numpy as np
from rapidfuzz import fuzz
from app.discovery.common import norm_values, completed

WEIGHTS_FULL = {"name": 0.20, "semantic": 0.35, "type": 0.20, "distribution": 0.25}
WEIGHTS_NO_EMB = {"name": 0.30, "type": 0.30, "distribution": 0.40}
MIN_SCORE = 0.60
REVIEW_BELOW = 0.80

_model = None


def _embedder():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _model = False
    return _model or None


def tokens(name: str) -> list[str]:
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return re.sub(r"[^a-zA-Z0-9]+", " ", name).lower().split()


def name_sim(a: str, b: str) -> float:
    return fuzz.token_sort_ratio(" ".join(tokens(a)), " ".join(tokens(b))) / 100


def describe(col: dict) -> str:
    ex = ", ".join(list(col.get("top_values", {}))[:5])
    return f"{' '.join(tokens(col['name']))} ({col['semantic_type']}) examples: {ex}"


def type_compat(a: dict, b: dict) -> float:
    sa, sb = a["semantic_type"], b["semantic_type"]
    if sa == sb and sa not in ("text", "unknown", "numeric"):
        return 1.0
    if a["dtype"] == b["dtype"]:
        return 0.8
    if {a["dtype"], b["dtype"]} <= {"integer", "float"}:
        return 0.8
    if sa == sb == "identifier":
        return 0.6
    return 0.0


def dist_sim(a: dict, b: dict, da: str, db: str) -> float:
    base = 0.5 * (1 - abs(a["unique_ratio"] - b["unique_ratio"])) \
         + 0.5 * (1 - abs(a["null_pct"] - b["null_pct"]) / 100)
    if a["dtype"] == "float" or b["dtype"] == "float":
        if "min" in a and "min" in b:
            lo, hi = max(a["min"], b["min"]), min(a["max"], b["max"])
            span = max(a["max"], b["max"]) - min(a["min"], b["min"])
            rng = max(0.0, hi - lo) / span if span else 1.0
            return 0.5 * rng + 0.5 * base
        return base
    va, vb = set(norm_values(da, a["name"]).head(5000)), set(norm_values(db, b["name"]).head(5000))
    if not va or not vb:
        return base
    overlap = len(va & vb) / min(len(va), len(vb))
    return 0.5 * overlap + 0.5 * base


def match_columns(profiles: list[dict]) -> list[dict]:
    profiles = completed(profiles)
    model = _embedder()
    emb = {}
    if model:
        keys = [(p["dataset_id"], c["name"]) for p in profiles for c in p["columns"]]
        descs = [describe(c) for p in profiles for c in p["columns"]]
        vecs = model.encode(descs, normalize_embeddings=True)
        emb = dict(zip(keys, vecs))
    W = WEIGHTS_FULL if model else WEIGHTS_NO_EMB

    out = []
    for pa, pb in combinations(profiles, 2):
        for ca in pa["columns"]:
            for cb in pb["columns"]:
                comp = {"name": name_sim(ca["name"], cb["name"]),
                        "type": type_compat(ca, cb)}
                if comp["type"] == 0:
                    continue
                comp["distribution"] = dist_sim(ca, cb, pa["dataset_id"], pb["dataset_id"])
                if model:
                    comp["semantic"] = float(np.dot(emb[(pa["dataset_id"], ca["name"])],
                                                    emb[(pb["dataset_id"], cb["name"])]))
                score = sum(W[k] * max(0.0, comp[k]) for k in W)
                if score >= MIN_SCORE:
                    out.append({
                        "source_dataset": pa["dataset_id"], "source_column": ca["name"],
                        "target_dataset": pb["dataset_id"], "target_column": cb["name"],
                        "relationship_type": "semantic_match",
                        "confidence": round(score, 3),
                        "evidence": {k: round(v, 3) for k, v in comp.items()},
                        "weights": W, "used_embeddings": bool(model),
                        "status": "inferred",
                        "needs_review": score < REVIEW_BELOW,
                    })
    return sorted(out, key=lambda r: -r["confidence"])