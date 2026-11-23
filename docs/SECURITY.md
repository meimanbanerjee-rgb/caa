# InsightForge AI — Security and Privacy Model

## 1. Threat Model & Implemented Safeguards (MVP)

### Untrusted User Files & Input Quarantine
- **No Code / Macro Execution (FR-2):**
  - Excel files are read with openpyxl in `data_only=True` mode, strictly preventing Excel formula execution, VBA macros, or external DDE references.
  - PDF documents are parsed in read-only mode with `pypdf`, strictly ignoring embedded JavaScript, action triggers, or external links.
  - CSV files are parsed with Pandas in C-engine mode, preventing shell execution or dynamic evaluation.
- **Upload Size & Type Limits (FR-1):**
  - Files exceeding the configured `MAX_UPLOAD_MB` (default 25 MB) are rejected at the edge before memory exhaustion.
  - MIME types and file extensions are strictly validated against a whitelist (`.csv`, `.tsv`, `.xlsx`, `.json`, `.jsonl`, `.pdf`).
- **Path Traversal Protection:**
  - Filenames are sanitized via regex to remove directory separators (`..`, `\`, `/`), prepended with random UUIDs, and isolated within dedicated upload folders.

### Untrusted File Content & Prompt Injection (FR-18, FR-20)
- **Untrusted Input Quarantine:** Raw text inside documents and user chat prompts is treated as untrusted data. Instructions attempting to override system behavior (e.g. "Ignore previous instructions", "Output $999,999,999") are neutralized.
- **Fixed Safe Operations Whitelist:**
  - The AI Analyst never synthesizes Python or shell commands directly for execution.
  - Only deterministic read-only operations (`summary`, `revenue_margins`, `top_products`, `top_customers`, `category_breakdown`, `trend_growth`, `outliers`, `data_quality`) are executed by Python pandas.
- **FR-16 Guard for Chat:**
  - Every number generated in an LLM response is checked against the precomputed deterministic evidence pool. If an LLM attempts to hallucinate an unverified figure, it is intercepted and replaced with the deterministic fallback.

### API Secrets and Privacy (PRD Section 9 & 13)
- **Strict Key Isolation:** Only `backend/app/config.py` accesses `.env`. API keys are never leaked to logs, client responses, error messages, or committed to Git (`.env` in `.gitignore`).
- **Deterministic Offline Mode (FR-21):**
  - Complete analytical and conversational functionality works 100% offline with zero external network calls if `LLM_API_KEY` is omitted.
- **External AI Warning:** The UI displays a clear indicator informing users before payload metadata is sent to an external provider.
- **Explicit Deletion (PRD Section 11):** Endpoint `DELETE /api/datasets/{id}` deletes datasets and cleans up disk artifacts.

## 2. Future Security Work (Documented Honestly)
InsightForge AI does not claim enterprise-grade security for the MVP. Future work includes:
- **Authentication & RBAC:** Multi-tenant user login, JWT tokens, and role-based permissions.
- **Encryption at Rest:** Database and uploaded file encryption using AES-256.
- **Rate Limiting:** Per-IP / per-user token bucket rate limiting on chat and file upload endpoints.
- **Audit Logs:** Immutable audit trail logging access and administrative actions.
- **Penetration Testing:** Formal vulnerability assessment and third-party penetration testing.
