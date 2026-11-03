import pandas as pd

from app.discovery.composite_key_detection import _is_minimal_unique_key


def test_two_columns_can_form_composite_key():
    df = pd.DataFrame({"order_id": [10, 10, 11, 11], "line_no": [1, 2, 1, 2]})
    valid, ratio = _is_minimal_unique_key(df, ("order_id", "line_no"))
    assert valid is True
    assert ratio == 1.0


def test_non_unique_combination_is_rejected():
    df = pd.DataFrame({"region": ["west", "west", "west", "east"],
                       "category": ["a", "a", "b", "a"]})
    valid, _ = _is_minimal_unique_key(df, ("region", "category"))
    assert valid is False


def test_null_component_is_rejected():
    df = pd.DataFrame({"order_id": [10, 10, 11], "line_no": [1, None, 1]})
    valid, _ = _is_minimal_unique_key(df, ("order_id", "line_no"))
    assert valid is False


def test_redundant_component_is_rejected():
    df = pd.DataFrame({"order_id": [10, 10, 11, 11],
                       "line_no": [1, 2, 1, 2],
                       "warehouse": ["x", "x", "y", "y"]})
    valid, _ = _is_minimal_unique_key(df, ("order_id", "line_no", "warehouse"))
    assert valid is False
