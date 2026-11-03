# Composite-key discovery

`POST /discover` now returns a `composite_keys` array alongside column matches
and single-column relationship candidates.

A candidate is a minimal combination of 2–3 columns that:
- has no nulls in any component;
- uniquely identifies every row;
- cannot be reduced by removing one or more components.

The search is bounded to the 18 eligible columns with the highest individual
cardinality. Results are marked `candidate` and `needs_review: true`; they are
not claims about declared database constraints.

Apply the two changed/new backend files and the test file to the matching
project paths. Run the test suite from `backend/` with `PYTHONPATH=.`.
