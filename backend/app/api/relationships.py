from fastapi import APIRouter
from app.database import store
from app.discovery.schema_matching import match_columns
from app.discovery.relationship_detection import detect_relationships
from app.discovery.composite_relationship_detection import detect_composite_relationships

router = APIRouter(tags=["discovery"])


@router.post("/discover")
def discover():
    profiles = store.list_profiles()
    result = {"column_matches": match_columns(profiles),
              "relationships": detect_relationships(profiles),
              "composite_relationships": detect_composite_relationships(profiles)}
    store.save_json("discovery", result)
    return result


@router.get("/relationships")
def relationships():
    return store.load_json("discovery", {"column_matches": [], "relationships": [], "composite_relationships": []})