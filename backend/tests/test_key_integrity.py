import pandas as pd

from app.profiling.profiler import profile_dataframe
from app.profiling.fingerprint import build_fingerprint


def test_near_unique_column_is_not_candidate_primary_key():
    df = pd.DataFrame({
        "customer_id": [1, 2, 3, 3, 4],
        "name": ["a", "b", "c", "d", "e"],
    })
    columns = profile_dataframe(df)
    fingerprint = build_fingerprint(df, columns)

    assert "customer_id" not in fingerprint["candidate_keys"]
    assert "name" in fingerprint["candidate_keys"]


def test_column_with_null_is_not_candidate_primary_key():
    df = pd.DataFrame({"id": [1, 2, None], "value": ["a", "b", "c"]})
    columns = profile_dataframe(df)
    fingerprint = build_fingerprint(df, columns)

    assert "id" not in fingerprint["candidate_keys"]
    assert "value" in fingerprint["candidate_keys"]
