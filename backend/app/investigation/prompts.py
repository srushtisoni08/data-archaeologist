import json

PLANNER = (
    "You plan a data investigation. Choose exactly ONE next tool. Reply with JSON only: "
    '{"tool": "<name or finish>", "args": {...}, "reason": "<one sentence>"}. '
    "Rules: never repeat a call; validate every candidate relationship before finishing; "
    "use only dataset ids and columns that appear in the evidence; do not state facts that are not in the evidence."
)

EXPLAIN = (
    "You explain findings from a data investigation. Use ONLY the hypotheses and evidence provided. "
    "Separate what is supported by evidence from what is inferred. Mention confidence and what a human should verify. "
    "Be concise (under 150 words). Never claim provenance that is not in the evidence."
)


def planner_user(objective, profiles, evidence, registry) -> str:
    return json.dumps({
        "objective": objective,
        "datasets": [{"id": p["dataset_id"], "file": p["filename"], "rows": p["row_count"]} for p in profiles],
        "tools": {k: {"description": v["desc"], "args": v["args"]} for k, v in registry.items()},
        "evidence_so_far": [{"id": e["id"], "tool": e["tool"], "args": e["args"], "summary": e["summary"]}
                            for e in evidence],
    })