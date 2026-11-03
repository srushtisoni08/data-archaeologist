# Data Archaeologist dataset v1 preparation

## Split
- Total examples: 100
- Training: 80
- Held-out evaluation: 20
- Holdout selection: deterministic random split, seed 20261103; IDs are recorded in the holdout JSONL.
- Do not merge the holdout file into training or use it to tune prompts, thresholds, or rules.

## Confidence normalization
All completion `confidence` fields are now numeric scalars in [0.0, 1.0].
Legacy qualitative labels were mapped conservatively: High=0.85, Medium/Moderate=0.65, Low=0.35; mixed dimensions use a conservative lower score; explicit numeric values are retained; objects are collapsed to the lowest dimension score.
This is a normalization for schema consistency, not a statistically calibrated probability.

## Review status
- The previously revised 16 examples remain revised.
- Examples 23 and 76 remain unchanged from the prior audit, with caveats.
- The other 82 are listed in `data_archaeologist_remaining_82_audit.csv` with targeted risk areas.
- This tracker is a screening/audit-control artifact, not evidence that all 82 were semantically corrected or independently validated. Do not call the dataset fully audited or training-ready until those 82 receive a content-level review and necessary rewrites.

## Files
- `data_archaeologist_training_v1.jsonl`: 80 training examples.
- `data_archaeologist_holdout_v1.jsonl`: 20 held-out examples.
- `data_archaeologist_remaining_82_audit.csv`: review tracker.
