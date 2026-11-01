# Data Archaeologist

An evidence-driven investigation system for unknown dataset collections. Upload a folder of CSV / Excel / JSON / JSONL / Parquet files; it profiles them, discovers how they connect, infers likely lineage, resolves duplicate entities, finds contradictions and anomalies, and produces an explainable report with confidence levels and open questions.

Everything it reports is **inferred** from file contents and file names. It never claims confirmed provenance without execution logs.

## How it works

Discover → Hypothesize → Investigate → Validate → Explain.

| Stage | Module | Method |
|---|---|---|
| Ingestion | `ingestion/` | Format, encoding and delimiter detection; originals stored read-only |
| Profiling | `profiling/` | Types, nulls, cardinality, patterns, outliers, semantic types, dataset fingerprint |
| Schema matching | `discovery/schema_matching.py` | Hybrid score: name + embedding + type + distribution, plus value-containment boost for identifier columns |
| Relationships | `discovery/relationship_detection.py` | PK/FK candidates by referential coverage, parent uniqueness, orphans; dominated-candidate flagging |
| Entity resolution | `discovery/entity_resolution.py` | Blocking + fuzzy name/email/phone; outcomes: same / uncertain / different |
| Lineage | `discovery/lineage_inference.py` | Key overlap, schema overlap, value changes, filename ordering; direction confidence kept low |
| Anomalies / contradictions | `analysis/` | Invalid dates, negatives, outliers, broken references; cross-file value conflicts with supporting-field evidence |
| Agent | `investigation/` | Orchestrator picks the next tool; deterministic Python tools compute all numbers; evidence store; hypotheses |
| Graph | `graph/` | NetworkX knowledge graph served as React Flow payload |
| Report | `reporting/` | JSON, Markdown, PDF |

The LLM (optional) only chooses the next tool and writes explanations. Without `LLM_API_KEY` a deterministic rules planner runs the same tools.

## Setup

Backend (Windows PowerShell):
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Frontend:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (Vite proxies `/api` to port 8000). API docs: http://localhost:8000/docs.

Optional LLM: create `backend/.env` with `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` (any OpenAI-compatible endpoint). Never commit `.env`.

## Usage

1. Upload files (UI or `POST /api/uploads`).
2. Click **Investigate** (`POST /api/investigations`).
3. Click graph nodes/edges for evidence; use the Console tab to ask why a finding was made.
4. Download the report: `/api/reports/{run_id}?format=pdf|md|json`.
5. **Reset** clears all uploaded datasets.

## Benchmark

Synthetic company dataset: 10 related files with injected faults (renamed keys, orphan references, 15 duplicate people with name variants, 25 city conflicts, 5 invalid dates, 3 negative amounts, a newer file version). Ground truth is kept in a separate file the system never sees.

```powershell
python benchmark\generate.py 42 base
python benchmark\evaluate.py base
python benchmark\generate.py 7 holdout      # different seed, 7 different column names
python benchmark\evaluate.py holdout        # no threshold changes
```

Results (same on base and hold-out):

| Task | Result |
|---|---|
| Schema matching, exact name | P 1.0 / R 0.368 / F1 0.538 |
| Schema matching, hybrid ≥0.8 | P 1.0 / R 1.0 / F1 1.0 |
| Schema matching, hybrid ≥0.7 | P 0.76 / R 1.0 (6 false matches) |
| Schema matching, hybrid ≥0.9 | P 1.0 / R 0.684 |
| FK discovery, fixed pipeline | P 0.667 / R 1.0 |
| FK discovery, with validation step | P 1.0 / R 1.0 |
| Entity resolution (pairwise) | P 1.0 / R 1.0, 43 (base) / 68 (hold-out) links flagged for review |
| Anomalies | 4/4 found, 0 false positives |
| Contradictions | 25 / 5 / 3 found, exactly as injected |
| Lineage | pair found, direction correct, no extra edges |

## Limitations

- The benchmark is synthetic and was built by the author; thresholds were tuned on the base set. The hold-out run changed the seed and column names but not the data structure. Real, messy data is untested.
- The 0.8 matching threshold is a narrow operating point. At 0.7, same-type pairs such as `order_date ~ paid_on` and `full_name ~ employees.name` appear; at 0.9 recall drops.
- The improvement in FK precision comes from the deterministic validation step, not from an LLM. Agent-vs-LLM planning has not been evaluated.
- Lineage direction relies on filenames (`_v2`). Without ordering signals, direction confidence is low by design.
- Entity links in the uncertain band are flagged for human review, not merged.
- Only the first sheet of an Excel file is read.
- The dataframe cache and JSON file storage are single-user; there is no auth or database.

## Project layout

```
backend/app/{api,ingestion,profiling,discovery,analysis,investigation,graph,reporting,database}
frontend/src/{App,GraphView,SidePanel,api}
benchmark/{generate.py,evaluate.py,ground_truth.json,data/}
sample_data/
```