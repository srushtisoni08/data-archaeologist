# Core engine implementation notes

## Changes in this pass

Candidate primary keys require 100% uniqueness and zero nulls.
Cross-dataset relationship discovery applies the same strict parent-key
condition. A relationship is labeled one-to-one only when the child
column is also complete and exactly unique. Hypothesis validation does
not call a parent key supported if it contains duplicates or nulls.

## Run the regression tests

Run from the `backend/` directory:

```powershell
pip install -r requirements.txt
pip install pytest
$env:PYTHONPATH = "."
pytest -q
```

These tests cover strict candidate-key detection. They do not certify
the complete investigation engine or calibrate confidence scores.
