# InsightForge AI — System Architecture

## 1. Architectural Philosophy: Deterministic Core, AI on Top
In InsightForge AI, mathematical calculations and statistical metrics are strictly separated from generative AI language models:
- **Python (Pandas, NumPy)** computes all metrics, aggregations, growth trends, profit margins, and outlier scores deterministically.
- **LLMs (Gemini / Anthropic / OpenAI)** only interpret, synthesize, and explain the pre-calculated numbers.
- **FR-16 Validation Guard:** Every metric cited in an explanation or insight card is cross-checked against the deterministic computation cache. Numbers that don't match are blocked before presentation.
- **Provider-Independent AI Layer:** Abstract base interface with hot-swappable providers configured purely via `.env`. A complete deterministic fallback runs if no API key is provided.

```
┌─────────────────────────────────────────────────────────────┐
│                 Frontend: React + Vite + TS                 │
│   Overview · Upload · Explorer · Insights · Chat · Reports   │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON / HTTP REST
┌──────────────────────────────▼──────────────────────────────┐
│                  FastAPI Backend Service                    │
│                                                             │
│  routes/       -->  Thin API controllers                    │
│  ingestion/    -->  CSV, Excel, JSON, PDF parsers           │
│  profiling/    -->  Type detection, semantic mapping        │
│  analytics/    -->  Deterministic pandas calculations        │
│  insights/     -->  Fact/Interpretation/Action builder     │
│  llm/          -->  Gemini / Anthropic / OpenAI / Fallback  │
│  reports/      -->  PDF (ReportLab) & CSV generation        │
│  storage/      -->  SQLite metadata + uploads directory     │
└─────────────────────────────────────────────────────────────┘
```

## 2. Directory Layout & Module Responsibilities
- `backend/app/main.py`: Entry point for FastAPI, CORS setup, router registrations.
- `backend/app/config.py`: Environment variable loader. The single source of truth for `.env` secrets.
- `backend/app/routes/`: Route controllers exposing clean REST endpoints (`upload`, `datasets`, `analysis`, `chat`, `reports`, `history`, `health`).
- `backend/app/models/`: Pydantic schemas declaring models for datasets, tables, columns, insights, chat messages, and reports.
- `backend/app/ingestion/`: Input parsers with strict MIME, size, and header checks:
  - `csv_parser.py`: CSV/TSV sniffer, delimiter detection, encoding fallback (`utf-8`, `latin-1`).
  - `excel_parser.py`: Multi-sheet Excel reader with `data_only=True` to block formulas/macros.
  - `json_parser.py`: Standard JSON and JSONL line parser with normalization.
  - `pdf_parser.py`: Safe PDF extractor for structured tables and narrative text with page references.
- `backend/app/profiling/`: Statistical column profiling, semantic role inference, and data quality warnings.
- `backend/app/analytics/`: High-performance pandas math routines (descriptive stats, gross margins, AOV, time-series growth, Z-score outliers).
- `backend/app/insights/`:
  - `builder.py`: Synthesizes insight cards with separate Fact, Interpretation, and Action.
  - `priority.py`: Auditable rule-based priority scoring (Impact, Urgency, Reliability, Relevance).
  - `validator.py`: FR-16 Guard verifying displayed numbers against computed metrics.
- `backend/app/llm/`:
  - `base.py`: Provider-independent abstract base class `BaseLLMProvider`.
  - `safe_plans.py`: Fixed safe operation planner (`summary`, `revenue_margins`, `top_products`, `trend_growth`, `outliers`, `data_quality`).
  - `fallback.py`: Deterministic templated engine for offline execution without an API key.
  - `providers/`: Hot-swappable providers (`gemini.py`, `openai.py`, `anthropic.py`).
- `backend/app/reports/`:
  - `report_builder.py`: Multi-section executive report generator conforming to PRD FR-22.
  - `pdf_export.py`: Production ReportLab PDF generator producing branded multi-page BI reports.
- `backend/app/storage/`: Abstract data store with SQLite metadata implementation.
