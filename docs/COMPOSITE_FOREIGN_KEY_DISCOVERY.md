# Composite foreign-key discovery

`POST /discover` now includes `composite_relationships` alongside the existing
single-column relationship candidates.

The detector searches for minimal, non-null combinations of 2–3 columns that
uniquely identify parent rows. It then checks compatible combinations in other
datasets and reports tuple-level referential coverage and orphan examples.

The search is bounded to the 12 highest-cardinality eligible columns in each
candidate dataset. Results are inferred candidates, not declared database
constraints, and require review. Null-containing child tuples are excluded
from the coverage denominator; inspect `child_non_null_rows` before interpreting
coverage.
