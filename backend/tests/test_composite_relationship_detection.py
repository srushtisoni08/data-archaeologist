import pandas as pd

from app.discovery import composite_relationship_detection as detector


def _column(name, dtype="integer", unique_ratio=0.66, null_count=0):
    return {
        "name": name,
        "dtype": dtype,
        "semantic_type": "identifier",
        "unique_ratio": unique_ratio,
        "null_count": null_count,
    }


def test_integer_and_float_columns_are_compatible():
    assert detector._group("integer") == detector._group("float") == "num"


def test_detects_composite_foreign_key_and_reports_orphans(monkeypatch):
    frames = {
        "parent": pd.DataFrame({"region_id": [1, 1, 2], "product_id": [10, 11, 10]}),
        "child": pd.DataFrame({"region_ref": [1, 1, 2, 9], "product_ref": [10, 11, 10, 99]}),
    }
    monkeypatch.setattr(detector, "get_df", lambda dataset_id: frames[dataset_id])

    profiles = [
        {
            "dataset_id": "parent", "ingestion_status": "completed",
            "columns": [_column("region_id"), _column("product_id")],
        },
        {
            "dataset_id": "child", "ingestion_status": "completed",
            "columns": [_column("region_ref", unique_ratio=0.75),
                        _column("product_ref", unique_ratio=0.75)],
        },
    ]

    results = detector.detect_composite_relationships(profiles)
    result = next(item for item in results if item["source_dataset"] == "parent")
    assert result["source_columns"] == ["region_id", "product_id"]
    assert result["target_columns"] == ["region_ref", "product_ref"]
    assert result["evidence"]["referential_coverage"] == 0.75
    assert result["evidence"]["orphan_combinations"] == 1
    assert result["needs_review"] is True


def test_does_not_infer_parent_key_when_pair_is_not_unique(monkeypatch):
    frames = {
        "parent": pd.DataFrame({"region_id": [1, 1, 1], "product_id": [10, 10, 10]}),
        "child": pd.DataFrame({"region_ref": [1, 1], "product_ref": [10, 10]}),
    }
    monkeypatch.setattr(detector, "get_df", lambda dataset_id: frames[dataset_id])

    profiles = [
        {
            "dataset_id": "parent", "ingestion_status": "completed",
            "columns": [_column("region_id", unique_ratio=0.33),
                        _column("product_id", unique_ratio=0.33)],
        },
        {
            "dataset_id": "child", "ingestion_status": "completed",
            "columns": [_column("region_ref", unique_ratio=0.5),
                        _column("product_ref", unique_ratio=0.5)],
        },
    ]

    assert detector.detect_composite_relationships(profiles) == []
