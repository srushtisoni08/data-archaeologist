from itertools import combinations, permutations

from app.discovery.common import completed, get_df
from app.discovery.schema_matching import name_sim

MIN_COVERAGE = 0.5
MAX_KEY_COLUMNS = 3
MAX_CANDIDATE_COLUMNS = 12
SKIP_TYPES = {"boolean", "category", "status", "geo_location", "person_name", "date", "currency"}


def _group(dtype):
    return "num" if dtype in ("integer", "float") else dtype


def _normalized_frame(dataset_id, columns):
    """Normalize composite values consistently before cross-file comparison."""
    frame = get_df(dataset_id).loc[:, list(columns)].copy()
    for column in columns:
        series = frame[column]
        non_null = series.dropna()
        if len(non_null) and all(isinstance(value, (int, float)) for value in non_null):
            if all(float(value).is_integer() for value in non_null):
                frame[column] = series.map(
                    lambda value: str(int(value)) if value is not None and value == value else None
                )
            else:
                frame[column] = series.map(
                    lambda value: str(value).strip().lower() if value is not None and value == value else None
                )
        else:
            frame[column] = series.map(
                lambda value: str(value).strip().lower() if value is not None and value == value else None
            )
    return frame


def _find_parent_keys(profile):
    dataset_id = profile["dataset_id"]
    df = get_df(dataset_id)
    stats = {column["name"]: column for column in profile.get("columns", [])}
    eligible = []
    for name in df.columns:
        column = stats.get(name)
        if not column or column.get("null_count", 0) != 0:
            continue
        if column.get("semantic_type") in SKIP_TYPES:
            continue
        ratio = column.get("unique_ratio", 0)
        if 0 < ratio < 1:
            eligible.append(name)

    eligible.sort(key=lambda name: stats[name].get("unique_ratio", 0), reverse=True)
    eligible = eligible[:MAX_CANDIDATE_COLUMNS]
    keys = []
    row_count = len(df)
    if row_count < 2:
        return keys

    for size in range(2, min(MAX_KEY_COLUMNS, len(eligible)) + 1):
        for candidate in combinations(eligible, size):
            values = _normalized_frame(dataset_id, candidate)
            if values.isna().any(axis=None) or values.drop_duplicates().shape[0] != row_count:
                continue
            minimal = True
            for sub_size in range(1, size):
                if any(
                    _normalized_frame(dataset_id, subset).drop_duplicates().shape[0] == row_count
                    for subset in combinations(candidate, sub_size)
                ):
                    minimal = False
                    break
            if minimal:
                keys.append(candidate)
    return keys


def detect_composite_relationships(profiles):
    """Infer composite foreign-key candidates by matching tuples to parent keys."""
    profiles = completed(profiles)
    parent_keys = {p["dataset_id"]: _find_parent_keys(p) for p in profiles}
    results = {}

    for parent in profiles:
        parent_id = parent["dataset_id"]
        parent_stats = {c["name"]: c for c in parent.get("columns", [])}
        for child in profiles:
            child_id = child["dataset_id"]
            if child_id == parent_id:
                continue
            child_df = get_df(child_id)
            child_stats = {c["name"]: c for c in child.get("columns", [])}

            for parent_columns in parent_keys[parent_id]:
                width = len(parent_columns)
                parent_types = [_group(parent_stats[c].get("dtype")) for c in parent_columns]
                parent_values = _normalized_frame(parent_id, parent_columns)
                parent_tuples = set(map(tuple, parent_values.to_numpy().tolist()))

                eligible = []
                for name in child_df.columns:
                    stats = child_stats.get(name)
                    if not stats or stats.get("semantic_type") in SKIP_TYPES:
                        continue
                    if stats.get("null_count", 0) >= len(child_df):
                        continue
                    if _group(stats.get("dtype")) in parent_types:
                        eligible.append(name)
                eligible.sort(key=lambda n: child_stats[n].get("unique_ratio", 0), reverse=True)
                eligible = eligible[:MAX_CANDIDATE_COLUMNS]

                for unordered in combinations(eligible, width):
                    # A small width (max 3) makes checking all alignments practical.
                    for child_columns in permutations(unordered):
                        child_types = [_group(child_stats[c].get("dtype")) for c in child_columns]
                        if child_types != parent_types:
                            continue
                        child_values = _normalized_frame(child_id, child_columns)
                        non_null = ~child_values.isna().any(axis=1)
                        child_values = child_values.loc[non_null]
                        if child_values.empty:
                            continue
                        child_tuples = list(map(tuple, child_values.to_numpy().tolist()))
                        matched = [value in parent_tuples for value in child_tuples]
                        coverage = sum(matched) / len(matched)
                        if coverage < MIN_COVERAGE:
                            continue

                        name_scores = [
                            name_sim(parent_col, child_col)
                            for parent_col, child_col in zip(parent_columns, child_columns)
                        ]
                        name_similarity = sum(name_scores) / len(name_scores)
                        confidence = 0.65 * coverage + 0.20 + 0.15 * name_similarity
                        orphan_examples = [
                            list(value) for value, is_match in zip(child_tuples, matched) if not is_match
                        ][:5]
                        unique_child = len(set(child_tuples)) == len(child_tuples)
                        result = {
                            "source_dataset": parent_id,
                            "source_columns": list(parent_columns),
                            "target_dataset": child_id,
                            "target_columns": list(child_columns),
                            "relationship_type": "possible_composite_foreign_key",
                            "cardinality": "one_to_one" if unique_child else "one_to_many",
                            "confidence": round(confidence, 3),
                            "status": "inferred",
                            "needs_review": coverage < 1.0 or confidence < 0.8,
                            "evidence": {
                                "referential_coverage": round(coverage, 3),
                                "parent_combination_unique": True,
                                "parent_rows": len(parent_values),
                                "child_non_null_rows": len(child_values),
                                "orphan_combinations": len(child_tuples) - sum(matched),
                                "orphan_examples": orphan_examples,
                                "component_name_similarities": [round(score, 3) for score in name_scores],
                                "type_compatible": True,
                            },
                        }
                        key = (parent_id, tuple(parent_columns), child_id, tuple(child_columns))
                        if key not in results or confidence > results[key]["confidence"]:
                            results[key] = result
                        # Avoid emitting permutations of the same child combination.
                        break
                    else:
                        continue
                    break

    return sorted(results.values(), key=lambda item: -item["confidence"])
