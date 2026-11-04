# Data Archaeologist

**Investigate unfamiliar datasets. Discover hidden relationships. Trace likely lineage. Explain data-quality issues with evidence.**

Data Archaeologist is an evidence-driven dataset investigation tool. Give it a collection of CSV, Excel, JSON, JSONL, or Parquet files and it profiles the data, looks for relationships between files, identifies possible duplicate entities, infers likely dataset lineage, detects anomalies and cross-file contradictions, and generates an investigation report.

It is designed for situations where the structure and history of a dataset collection are not fully documented.

> **Important:** Findings are inferences from the available files and their contents. The system does not claim verified data provenance unless execution logs or other direct evidence are provided.

## What it does

| Capability | What it investigates |
|---|---|
| Dataset ingestion | Detects supported file formats, encodings, and delimiters; keeps uploaded originals read-only. |
| Data profiling | Examines data types, missing values, cardinality, value patterns, outliers, semantic types, and dataset fingerprints. |
| Schema matching | Finds columns that may represent the same field using names, embeddings, data types, distributions, and identifier-value containment. |
| Relationship discovery | Suggests primary-key/foreign-key candidates using uniqueness, referential coverage, and orphan checks. |
| Entity resolution | Finds possible duplicate entities using blocking and fuzzy comparisons across names, email addresses, and phone numbers. Results are classified as same, uncertain, or different. |
| Lineage inference | Estimates relationships and possible direction between dataset versions using key overlap, schema overlap, value changes, and filename/version clues. |
| Anomaly detection | Flags issues such as invalid dates, negative values, outliers, and broken references. |
| Contradiction detection | Finds conflicting values across files and records the supporting-field evidence used by the check. |
| Investigation agent | Selects investigation tools, stores evidence, and builds hypotheses. Deterministic Python tools perform the underlying calculations. |
| Knowledge graph | Presents discovered datasets, fields, relationships, and findings as an interactive graph. |
| Reports | Exports investigation results as JSON, Markdown, or PDF. |

## Investigation workflow

The system follows an evidence-oriented workflow:

1. **Discover** — ingest and profile the supplied files.
2. **Hypothesize** — identify possible schemas, keys, relationships, entities, and lineage.
3. **Investigate** — run targeted checks and collect supporting evidence.
4. **Validate** — test candidate relationships and findings against the available data.
5. **Explain** — present findings, confidence levels, evidence, and unresolved questions.

The LLM integration is optional. When configured, an LLM can help select the next tool and write natural-language explanations. It does **not** calculate the reported statistics or replace the deterministic analysis tools. Without an LLM API key, the application uses its built-in rules planner.

## Technology

- **Backend:** Python, FastAPI, pandas, NetworkX, RapidFuzz, Sentence Transformers
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, `@xyflow/react`
- **Exports:** JSON, Markdown, PDF (ReportLab)
- **Testing:** pytest

## Requirements

- Python 3.10 or later recommended
- Node.js and npm
- Internet access on the first run if the sentence-embedding model needs to be downloaded

The backend dependencies include packages for CSV/Excel/Parquet processing, fuzzy matching, embeddings, API serving, and report generation.

## Run locally (Windows PowerShell)

Open two terminals from the project root.

### 1. Start the backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`.

- Health check: `http://localhost:8000/health`
- Interactive API documentation: `http://localhost:8000/docs`

### 2. Start the frontend

In a second terminal, from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. The Vite development server is configured to proxy `/api` requests to the backend on port `8000`.

### Optional: configure an LLM

Create `backend/.env` using `backend/.env.example` as a reference and provide an OpenAI-compatible endpoint:

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=your_openai_compatible_base_url
LLM_MODEL=your_model_name
```

The exact values depend on the provider you use. Keep `.env` private and never commit API keys. The application can run without these variables using the deterministic rules planner.

## Use the application

1. Start the backend and frontend.
2. Upload a collection of related CSV, Excel, JSON, JSONL, or Parquet files through the interface (or the upload API).
3. Start an investigation.
4. Inspect the discovered relationships and findings in the graph.
5. Select graph nodes or edges to inspect their evidence. Use the Console tab to ask why a finding was produced.
6. Download the investigation report in PDF, Markdown, or JSON format.
7. Use **Reset** to clear the currently uploaded datasets when you want to start another investigation.

Reports are exposed through:

```text
/api/reports/{run_id}?format=pdf
/api/reports/{run_id}?format=md
/api/reports/{run_id}?format=json
```

## Run tests

From the project root:

```powershell
cd backend
python -m pytest -q
```

## Benchmark

The repository includes a synthetic benchmark generator, evaluator, and separate ground-truth file. The benchmark creates related company datasets with deliberately injected data-quality issues. The ground truth is not supplied to the investigation system during evaluation.

Run the benchmark from the project root:

```powershell
python benchmark\generate.py 42 base
python benchmark\evaluate.py base

python benchmark\generate.py 7 holdout
python benchmark\evaluate.py holdout
```

The holdout uses a different random seed and altered column names. The benchmark results currently recorded in the repository are:

| Task / operating point | Recorded result |
|---|---|
| Schema matching — exact-name baseline | Precision 1.00, recall 0.368, F1 0.538 |
| Schema matching — hybrid score threshold ≥ 0.8 | Precision 1.00, recall 1.00, F1 1.00 |
| Schema matching — hybrid score threshold ≥ 0.7 | Precision 0.76, recall 1.00; 6 false matches |
| Schema matching — hybrid score threshold ≥ 0.9 | Precision 1.00, recall 0.684 |
| Foreign-key discovery — fixed pipeline | Precision 0.667, recall 1.00 |
| Foreign-key discovery — with validation step | Precision 1.00, recall 1.00 |
| Entity resolution — pairwise | Precision 1.00, recall 1.00; uncertain links are left for review |
| Injected anomalies | 4 of 4 detected, 0 false positives |
| Injected contradictions | 25 city, 5 date, and 3 negative-amount cases detected |
| Lineage | Expected pair found, direction correct, no extra edges |

These are results on the repository's synthetic benchmark, **not a claim of equivalent performance on arbitrary real-world datasets**. Re-run the benchmark in your environment before quoting the figures in a presentation, and describe the benchmark setup and limitations alongside the results.

## Limitations and interpretation

- The benchmark is synthetic and was authored alongside the system. Thresholds were tuned on the base benchmark; the holdout changes the seed and column names but retains the same underlying data structure. Independent real-world validation is still needed.
- Schema matching is threshold-sensitive. The recorded results show that lowering the threshold increases false matches, while raising it reduces recall.
- Foreign-key precision improves after deterministic validation; this improvement should not be attributed to the LLM.
- Agent-versus-LLM planning quality has not been evaluated independently.
- Lineage direction can depend on filename/version clues (for example, `_v2`). When ordering evidence is absent, direction confidence is intentionally low.
- Entity matches in the uncertain band are flagged for human review rather than automatically merged.
- Only the first worksheet of an Excel workbook is read.
- The current dataframe cache and JSON-file storage are single-user and do not provide authentication or a production database.
- Findings depend on the files supplied. Missing source systems, execution logs, business rules, or historical snapshots can limit what the tool can establish.

## Repository structure

```text
Data-Archaeologist/
├── backend/
│   ├── app/
│   │   ├── analysis/        # Anomaly and contradiction detection
│   │   ├── api/             # FastAPI endpoints
│   │   ├── database/        # Local storage
│   │   ├── discovery/       # Schema, relationship, entity, lineage discovery
│   │   ├── graph/           # Knowledge-graph construction and analysis
│   │   ├── ingestion/       # File loading and schema extraction
│   │   ├── investigation/  # Agent, hypotheses, evidence, tools
│   │   ├── profiling/       # Dataset profiling and fingerprints
│   │   └── reporting/       # Report generation
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/                 # React interface and graph view
├── benchmark/
│   ├── generate.py
│   ├── evaluate.py
│   ├── ground_truth.json
│   └── results.json
├── data/
│   ├── evaluation/          # Holdout evaluation data
│   ├── review/              # Dataset review and audit files
│   └── training/            # Training datasets
├── docs/                    # Technical design notes
├── sample_data/             # Example datasets for exploration
└── README.md
```

## Responsible interpretation

Data Archaeologist is an investigation assistant, not an oracle. Treat inferred keys, entity matches, lineage direction, anomaly explanations, and root-cause hypotheses as candidates supported by evidence. Review uncertain or high-impact findings before using them to change production data or make business decisions.

---

**Project status:** Working prototype with a deterministic investigation pipeline and an optional LLM-assisted explanation/planning layer. Fine-tuned model training and broader real-world evaluation are separate workstreams and are not prerequisites for running the current application.
