from itertools import combinations

from app.discovery.common import completed, get_df

MAX_KEY_COLUMNS = 3
MIN_ROWS = 2
MAX_COLUMNS_TO_SEARCH = 18


def _is_minimal_unique_key(df, columns):
    """Return whether the selected columns form a complete, minimal unique key."""
    subset = df.loc[:, list(columns)]
    if subset.isna().any(axis=None) or len(subset) < MIN_ROWS:
        return False, 0.0

    row_count = len(subset)
    unique_ratio = float(subset.drop_duplicates().shape[0] / row_count)
    if unique_ratio != 1.0:
        return False, unique_ratio

    # If any proper subset is already unique, this combination is redundant.
    for size in range(1, len(columns)):
        for smaller in combinations(columns, size):
            if df.loc[:, list(smaller)].drop_duplicates().shape[0] == row_count:
                return False, unique_ratio

    return True, unique_ratio


def detect_composite_keys(profiles, max_columns=MAX_KEY_COLUMNS):
    """
    Find minimal combinations of 2–3 columns that uniquely identify all rows.
    These are inferred candidates, not declared database primary keys.
    """
    results = []

    for profile in completed(profiles):
        dataset_id = profile["dataset_id"]
        df = get_df(dataset_id)
        if len(df) < MIN_ROWS:
            continue

        stats_by_name = {c["name"]: c for c in profile.get("columns", [])}
        eligible = []
        for name in df.columns:
            stats = stats_by_name.get(name)
            if not stats or stats.get("null_count", 0) != 0:
                continue
            ratio = stats.get("unique_ratio", 0)
            # Unique single columns are already keys; constants add no value.
            if 0 < ratio < 1:
                eligible.append(name)

        # Bound the search to control combinatorial cost.
        eligible.sort(
            key=lambda name: stats_by_name[name].get("unique_ratio", 0),
            reverse=True,
        )
        eligible = eligible[:MAX_COLUMNS_TO_SEARCH]

        for size in range(2, min(max_columns, len(eligible)) + 1):
            for columns in combinations(eligible, size):
                valid, ratio = _is_minimal_unique_key(df, columns)
                if not valid:
                    continue

                results.append({
                    "dataset_id": dataset_id,
                    "columns": list(columns),
                    "column_count": len(columns),
                    "row_count": int(len(df)),
                    "unique_ratio": round(ratio, 4),
                    "classification": "inferred_composite_key",
                    "status": "candidate",
                    "confidence": 1.0,
                    "evidence": {
                        "all_components_non_null": True,
                        "combination_uniquely_identifies_rows": True,
                        "minimal_key": True,
                        "component_unique_ratios": {
                            name: stats_by_name[name].get("unique_ratio", 0)
                            for name in columns
                        },
                    },
                    "needs_review": True,
                })

    return results
