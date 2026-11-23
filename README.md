# InsightForge AI ⚡

> **Deterministic Business Intelligence with Grounded AI Explanations**
>
> *Rule 1: The AI never invents numbers. Python (pandas) does all calculations. The AI only explains what Python computed.*

InsightForge AI turns raw multi-format files (CSV, TSV, XLSX, JSON, JSONL, PDF) into auditable, evidence-backed business insights, interactive dashboards, chat-driven intelligence, and downloadable executive reports with mathematical precision.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- **Node.js 18+** & npm
- *(Optional)* **Docker & Docker Compose**

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Start backend server
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
Verify backend is healthy:
```bash
curl http://127.0.0.1:8000/api/health
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4. Running with Docker
```bash
docker compose up --build
```
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

---

## 🛠️ Configuration (.env)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key settings:
- `LLM_PROVIDER`: `gemini` (default), `openai`, `anthropic`, or `none`.
- `LLM_API_KEY`: **Optional!** If omitted or blank, InsightForge operates in 100% deterministic offline fallback mode with zero external network calls.
- `MAX_UPLOAD_MB`: Maximum file upload size in megabytes (default: 25).
- `ALLOWED_ORIGINS`: CORS origins (default: `http://localhost:5173,http://localhost:3000`).

---

## 🧪 Automated Testing
Run the complete automated test suite (42 unit and integration tests):
```bash
python -m pytest backend/tests -v
```
To build and check frontend TypeScript types:
```bash
cd frontend
npm run build
```

---

## 📡 API Endpoints (PRD Section 11)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Server status and AI provider configuration |
| `POST` | `/api/upload` | Upload multi-format files (CSV, TSV, XLSX, JSON, PDF) |
| `GET` | `/api/datasets` | List all uploaded datasets |
| `GET` | `/api/datasets/{id}` | Inspect tables, column types, samples, quality stats |
| `PATCH` | `/api/datasets/{id}/fields` | Confirm or change suggested semantic column meanings |
| `DELETE`| `/api/datasets/{id}` | Delete dataset and disk storage |
| `POST` | `/api/datasets/{id}/analyze` | Execute deterministic analytics pipeline & build insights |
| `GET` | `/api/analyses/{id}` | Retrieve computed metrics, charts, and prioritized insights |
| `GET` | `/api/analyses/{id}/insights/{i_id}/evidence` | Audit exact formula and numbers behind an insight card |
| `POST` | `/api/chat` | Ask questions to the Grounded AI Analyst |
| `GET` | `/api/chat/{analysis_id}` | Retrieve chat conversation history |
| `GET` | `/api/reports/{analysis_id}/sections` | Get structured multi-section report preview (FR-22) |
| `GET` | `/api/reports/{analysis_id}/pdf` | Download multi-page executive PDF report (ReportLab) |
| `GET` | `/api/reports/{analysis_id}/csv` | Download complete CSV metric and insight export |
| `GET` | `/api/history` | List persistent analysis history records |

---

## 🔍 Chat Debugging Notes
See [docs/CHAT_DEBUGGING_NOTES.md](docs/CHAT_DEBUGGING_NOTES.md) for the detailed diagnosis and findings table of the 15 core business questions against sample data.

---

## 📁 Repository Structure
```
insightforge-ai/
├── README.md                    # Project documentation & run guide
├── .env.example                 # Template configuration
├── docker-compose.yml           # Docker orchestration configuration
├── backend/
│   ├── Dockerfile               # Backend container recipe
│   ├── requirements.txt         # Python dependencies
│   ├── app/
│   │   ├── main.py              # FastAPI entry point & route registration
│   │   ├── config.py            # Environment variable loader
│   │   ├── routes/              # Thin API controllers
│   │   ├── models/              # Pydantic schemas (dataset, insight, chat)
│   │   ├── ingestion/           # CSV, Excel, JSON, and PDF parsers
│   │   ├── profiling/           # Type detection, semantic classification
│   │   ├── analytics/           # Pure deterministic pandas computation
│   │   ├── insights/            # Fact / Interpretation / Action builder & FR-16 Guard
│   │   ├── llm/                 # Gemini, OpenAI, Anthropic & Offline Fallback
│   │   ├── reports/             # Multi-section ReportBuilder & PDF export
│   │   └── storage/             # SQLite database and persistence
│   └── tests/                   # Pytest test suite & synthetic test data
├── frontend/
│   ├── Dockerfile               # Frontend container recipe
│   ├── package.json
│   ├── src/
│   │   ├── api/client.ts        # Unified HTTP client
│   │   ├── pages/               # Overview, Upload, Explorer, Insights, Analyst, Reports, History
│   │   └── components/          # KpiCard, ChartCard, InsightCard, EvidenceModal
└── docs/
    ├── PRD.md                   # Product Requirements Document
    ├── ARCHITECTURE.md          # Architectural Blueprint
    ├── SECURITY.md              # Security model & threat analysis
    └── MANUAL_TEST_PLAN.md      # Comprehensive step-by-step test plan
```

---

## 🔒 Security & Privacy (FR-1 to FR-21)
- **Safe Parsing:** Excel is parsed with `data_only=True` (no macro or formula execution). PDFs are extracted in read-only mode with `pypdf`.
- **FR-16 Guard:** Every number shown in an insight card or AI chat response is mathematically verified against the deterministic calculation cache before presentation.
- **Prompt Injection Defense:** User text and document contents are treated as untrusted data; instructions attempting to override role constraints are neutralized.
- **Deterministic Core:** Analytics, charts, profiling, and fallback explanations execute 100% locally with zero external API calls if no key is configured.
