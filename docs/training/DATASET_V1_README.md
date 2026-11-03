# Data Archaeologist dataset v1 — reviewed training partition

## Files
- `data_archaeologist_training_v1.jsonl`: 80 training examples.
- `data_archaeologist_holdout_v1.jsonl`: 20 held-out examples. Do not upload as training data.
- `holdout_example_ids.txt`: IDs reserved for the holdout.
- `risk_review_audit.csv`: status of every row from the user's risk lists.

## Review scope
All 42 flagged examples in the training partition were rewritten using only evidence stated in their prompts. Nine flagged examples were in the existing holdout and were deliberately left unchanged: 45, 46, 48, 52, 53, 55, 69, 94, 95.
No examples were removed. The training/holdout membership remains disjoint and totals 100 records (80/20). The split was rebuilt after the training-side edits using the existing reserved holdout IDs so no holdout example entered training.

A final manual risk-word review of all 80 training rows was completed. Two additional rewrites were applied:
- **Row 35 (file row 32)** — `recommended_next_action`: removed the unsupported instruction to prioritise Extract A's end date. Replaced with a neutral instruction to keep both values, mark the field as conflicted, and defer to an authoritative source before choosing one.
- **Row 58 (file row 47)** — `reasoning.deduplication_logic`: softened "represent" to "may represent" so the hypothesis is properly hedged.

The candidate file (`data_archaeologist_training_candidate.jsonl`) has been promoted to replace `data_archaeologist_training_v1.jsonl` and the candidate file deleted. The 20 holdout rows were not reviewed or altered (evaluation only).

## Confidence
Every completion uses a numeric `confidence` value in [0, 1]. This is a normalized editorial confidence label, not a statistically calibrated probability.

## JSONL schema
Each line is one JSON object with:
- `prompt`: string
- `completion`: JSON-encoded string containing `finding`, `classification`, `evidence`, `reasoning`, `confidence`, `limitations`, `recommended_next_action`, and `additional_fields`.

## Adaption upload requirements checked
Adaption's documented dataset ingestion supports JSONL. For raw ingestion of training-ready prompt/completion data, use raw processing and map `prompt` and `completion`. AutoScientist's current documentation states SFT requires at least 1,000 effective rows. This file has 80 rows, so it can be uploaded as a dataset but is below the documented minimum for an SFT AutoScientist run. Do not assume upload acceptance means it is eligible to train.

## Important
Only upload `data_archaeologist_training_v1.jsonl` as the training dataset. Keep the holdout file private and use it only for evaluation after training choices are frozen.
