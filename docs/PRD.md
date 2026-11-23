# InsightForge AI — Product Requirements Document (PRD)

Version 1.0 · October 28, 2026 · Status: Approved

## 1. Product Summary
InsightForge AI is a business intelligence web app. A user uploads business files (spreadsheets, JSON, PDFs, text). The app reads them, checks their quality, runs real calculations, and produces evidence-backed insights, an interactive dashboard, a chat-style AI analyst, and a downloadable report.

**The one rule that shapes everything:** The AI never invents numbers. Python (pandas) does all calculations. The AI only explains results that Python already computed.

---

## 2. Problem and Goals
**Problem:** Small businesses have data in many formats but no analyst. Generic chatbots guess; basic dashboards only draw charts.

### Goals
- **G1:** Turn raw files into trustworthy insights, each linked to its source data.
- **G2:** Separate facts (calculated), interpretations (plausible reasons), and recommendations (suggested actions).
- **G3:** Work without an AI key for all deterministic analysis. The key only unlocks chat and written explanations.
- **G4:** Be easy to learn from: small files, plain names, comments, one job per file.

### Non-goals (MVP)
- Multi-user login, enterprise security claims, real-time streaming data, automatic merging of unrelated files, scanned-PDF OCR as a required feature.

---

## 3. Users and Needs
| User | Need |
| :--- | :--- |
| **Business owner** | Understand what is happening and what to do next, in plain English |
| **Analyst / student** | See formulas, evidence, and data-quality problems clearly |
| **Evaluator (college review)** | Verify that results are correct and traceable |

---

## 4. Scope: MVP vs Future

### MVP (Must Have)
1. Upload CSV, TSV, XLSX, JSON, JSONL (multi-file, drag and drop).
2. File validation and friendly error messages.
3. Data profiling: column types, suggested field meanings, quality checks.
4. Deterministic analytics: totals, averages, growth, top/bottom categories, trends, outliers.
5. Insight objects with evidence and source references.
6. Dashboard with KPI cards and charts built from real results.
7. AI Analyst chat grounded in computed results, with a no-key fallback.
8. PDF report and CSV exports.
9. SQLite-based analysis history.
10. Tests with a synthetic dataset whose answers are known.

### Phase 2 (Should Have)
- Text and PDF narrative analysis, PDF table extraction, customer feedback summaries, conflict detection across documents.

### Future (Nice to Have)
- OCR for scanned files, SQLite upload, forecasting, customer segmentation, PostgreSQL and cloud storage, authentication, Docker polish.

---

## 5. Functional Requirements
### 5.1 Upload and Validation
- **FR-1:** Accept multiple files; check extension, MIME type, size limit, and parse success.
- **FR-2:** Never execute uploaded files, macros, or formulas. Read values only.
- **FR-3:** Show corrupted or unsupported files as clear messages, not crashes.
- **FR-4:** Keep source references (filename, sheet, row, page) for every extracted value.
- **FR-5:** Never silently drop data. Anything skipped is listed as a warning.
- **FR-6:** Never merge multiple files automatically. Suggest a join and ask the user to confirm.

### 5.2 Data Understanding
- **FR-7:** Detect column types (number, date, text, category, ID).
- **FR-8:** Suggest meanings (e.g., revenue, order date, customer ID). Mark each as suggested until the user confirms it.
- **FR-9:** Detect missing values, duplicates, mixed date formats, invalid numbers, outliers, and inconsistent labels (for example "NY" vs "New York").
- **FR-10:** Keep the original data untouched. Store the cleaned version separately with a log of every change.
- **FR-11:** Guess the business domain, or ask the user if unclear.

### 5.3 Analytics Engine
- **FR-12:** Choose only analyses the data supports. No revenue analysis without revenue data.
- **FR-13:** Provide descriptive stats, category breakdowns, period-over-period growth, margins (with written formulas), top products and customers, time trends, and outlier detection.
- **FR-14:** Correlations are never described as causes.
- **FR-15:** Forecasts only with enough data, always labelled as estimates with uncertainty.

### 5.4 Insight Engine
Every insight is a structured object with these fields:
- `title`, `category`, `plain_English_explanation`
- `priority` (rule-based: impact, urgency, data reliability, relevance)
- `observed_fact`, `interpretation`, `recommendation` (kept strictly separate)
- `evidence` (metrics and numbers), `method_or_formula`
- `source` (file, sheet, rows, pages)
- `reliability_note` (statistical confidence, extraction reliability, and judgment uncertainty kept separate; no made-up percentages)
- `assumptions_and_limitations`
- **FR-16:** A validation step re-checks every displayed number against the computed result before it is shown.

### 5.5 AI Analyst (Chat)
- **FR-17:** Flow: understand question, pick tables and fields, build a safe plan, run the analytics engine, explain with sources and limits.
- **FR-18:** Use a fixed list of safe operations (sum, group by, trend, top N, compare). No AI-generated Python or shell commands. If SQL is used, it is read-only and validated.
- **FR-19:** If data is missing, say what is missing instead of guessing.
- **FR-20:** Text inside uploaded documents is treated as untrusted data. Instructions in it are ignored.
- **FR-21:** Without an API key, show computed results and templated explanations.

### 5.6 Reports and Exports
- **FR-22:** Report sections: executive summary, dataset overview, data quality, key metrics, findings, charts, risks, opportunities, next steps, methodology, sources, assumptions.
- **FR-23:** Include generation date and analysis settings. Mark forecasts clearly.
- **FR-24:** PDF report plus CSV exports of tables and insights.

---

## 6. UI Pages
1. **Overview:** Recent analyses, datasets, key findings.
2. **Upload Workspace:** Drag and drop, previews, processing status.
3. **Data Explorer:** Tables, sheets, column types, samples, warnings, transformations.
4. **Insights Dashboard:** KPIs, trends, anomalies, prioritized recommendations.
5. **AI Analyst:** Chat grounded in the selected dataset.
6. **Reports:** View report, download PDF and CSV.
7. **History:** Reopen or delete past analyses.
