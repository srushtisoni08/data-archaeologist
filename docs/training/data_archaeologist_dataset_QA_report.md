# Data Archaeologist — Dataset QA Report

## Files reviewed
- Source: `data_archaeology_tasks.json`
- Examples: 100
- Empty prompts: 0
- Empty completions: 0
- Duplicate prompts: 0

## Structural findings
- Markdown-fenced completions: 76
- Unfenced completions: 24
- Completion JSON syntax repairs: 1
- Output records written to JSONL: 100
- Examples queued for manual review by automated phrase screening: 18

One malformed completion (example 57) had a missing closing quotation mark in an evidence string. A narrowly scoped syntax repair was applied so the record could be parsed. The repair does not validate the factual correctness of that example.

## Original output-field type variation

| Field | Original type counts |
|---|---|
| `finding` | str: 98, dict: 2 |
| `classification` | str: 94, dict: 2, list: 4 |
| `evidence` | list: 76, dict: 24 |
| `reasoning` | str: 77, dict: 19, list: 4 |
| `confidence` | str: 73, dict: 15, float: 12 |
| `limitations` | list: 82, str: 18 |
| `recommended_next_action` | str: 60, dict: 6, list: 34 |

## Normalization applied
The candidate JSONL uses one record per line with:
- `prompt`: the original `enhanced_prompt`
- `completion`: a JSON-encoded string with a consistent output schema

The normalized completion schema contains:
- `finding` (string)
- `classification` (string)
- `evidence` (array of strings)
- `reasoning` (string)
- `confidence` (string)
- `limitations` (array of strings)
- `recommended_next_action` (array of strings)
- `additional_fields` (object; preserves any extra original fields)

Where an original field was an object or array but the normalized field is a string, its content was serialized rather than deleted. For list fields, object values were serialized as JSON strings. This is a format normalization, not a semantic correction.

## Important limitation: not training-ready yet

This pass validates and normalizes structure only. It does **not** establish that the generated answers are factually or logically correct. Phrase-based screening flags examples that deserve closer human review, including:
- statistical significance claims without visible test details;
- MNAR classifications;
- strong correlation/exclusivity language;
- causal/root-cause assertions;
- imputation recommendations.

These are review prompts, not automatic verdicts. The CSV lists the flagged examples and excerpts.

Before model training, manually verify the evidence and conclusions in every example. In particular, check that confidence is justified, keys are not declared without uniqueness evidence, correlations are not treated as causes, and proposed imputations are supported by the supplied data.

## Recommended next step
Use the JSONL as a **normalized candidate**, not as a validated gold-standard dataset. Review `data_archaeologist_review_queue.csv`, correct or remove unsupported examples, and reserve a separate unseen evaluation set before AutoScientist training.
