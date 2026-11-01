from fastapi import APIRouter
from app.database import store
from app.discovery.schema_matching import match_columns
from app.discovery.relationship_detection import detect_relationships
from app.discovery.entity_resolution import resolve_entities
from app.analysis.anomaly_detection import detect_anomalies
from app.analysis.contradiction_detection import detect_contradictions

router = APIRouter(tags=["investigation"])


@router.post("/analyze")
def analyze():
    profiles = store.list_profiles()
    disc = {"column_matches": match_columns(profiles), "relationships": detect_relationships(profiles)}
    store.save_json("discovery", disc)
    ents = resolve_entities(profiles)
    anomalies = detect_anomalies(profiles, disc["relationships"])
    contradictions = detect_contradictions(profiles, disc)
    result = {
        "summary": {
            "datasets": len(profiles),
            "column_matches": len(disc["column_matches"]),
            "relationships": len(disc["relationships"]),
            "entity_clusters": len(ents["entities"]),
            "entities_needing_review": sum(e["status"] != "same_entity" for e in ents["entities"]),
            "anomalies": len(anomalies),
            "contradictions": len(contradictions),
        },
        "entities": ents, "anomalies": anomalies, "contradictions": contradictions,
    }
    store.save_json("analysis", result)
    return result


@router.get("/analysis")
def analysis():
    return store.load_json("analysis", {})