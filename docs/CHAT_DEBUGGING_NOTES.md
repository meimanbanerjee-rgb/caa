# Chat Debugging Notes

## Step 1 Diagnosis: Initial State of AI Analyst Chat

### 1. Architectural Diagnosis
- **Data Context Bottleneck**: 
  `/api/chat` was previously calling `ask_grounded` with only the pre-computed summary metrics dictionary (`analysis.metrics`). The underlying dataset DataFrame was never queried dynamically during chat. Consequently, queries that required computing on un-summarized dimensions (e.g., regional breakdown when category was preferred, profit per product vs revenue, or monthly filtering) had no data access.
- **Role Discriminator Failure (Groq/OpenAI HTTP 400)**: 
  The chat history stored assistant messages with `role: "analyst"`. When sending conversation history to Groq/OpenAI, Groq returned HTTP 400 (`'messages.1' : discriminator property 'role' has invalid value`) because OpenAI-compatible APIs only accept `system`, `user`, or `assistant`. This caused every subsequent chat query after the first message to fail and drop into fallback mode.
- **FR-16 Guard False Positive on Entity Names**:
  `InsightValidator.extract_numbers` extracted all integers including strings from product names (e.g., "Pro Laptop 15" -> `15.0`, "4K Monitor 27" -> `27.0`). Because `15.0` was not in the statistical metrics pool, the validation guard blocked the entire LLM response as "hallucinated numbers" and forced fallback.
- **Fixed Operations Coverage**:
  `SafePlanExecutor` only had 8 coarse operations (`summary`, `revenue_margins`, `top_products`, `top_customers`, `category_breakdown`, `trend_growth`, `outliers`, `data_quality`). Operations like `compare_groups`, `monthly_trend`, `top_drivers_of_change`, `duplicate_report`, `missing_values_report`, `list_top_insights`, and `get_insight_evidence` were missing.
- **Off-Topic & Out-of-Domain Handling**:
  Unanswerable questions (e.g., "What is the weather tomorrow?") defaulted to `"summary"`, outputting irrelevant retail revenue figures ($28,100.00) instead of an honest "data missing" notification.

---

### 2. /api/health Verification
- **Status**: Healthy (`status: healthy`, `version: 1.0.0`).
- **AI Configuration**: `ai_configured: True`, `provider: groq`, `model: openai/gpt-oss-120b`.
- **Provider Connection Result**: Key loaded from `.env`. Call to Groq succeeded on single queries, but failed on multi-turn conversations due to the `role: "analyst"` bug.

---

### 3. Diagnostic Results: 15 Core Questions against `clean_sales.csv`

| # | Question | Interpreted Intent / Plan | Where it Fails | Root Cause / Failure Details |
|---|---|---|---|---|
| 1 | Which products generate the most profit? | `top_products` | Operation & Metric Missing | Ranks products by `revenue` instead of `profit` / `margin`. Profit ranking per product was not calculated. |
| 2 | Which region has the highest revenue? | `category_breakdown` | Field Matching / Data Context | `category_breakdown` only grouped by `category` (Electronics, Furniture, Office Supplies). Region grouping was dropped. |
| 3 | Compare the performance of different regions. | `category_breakdown` | Operation Missing | Only returned category breakdown; no `compare_groups` or region performance matrix existed. |
| 4 | Why did revenue decrease last month? | `trend_growth` | Operation Missing | Returned general overall growth (-14.00%), but did not identify drivers (product/category changes from Feb to Mar). |
| 5 | Which expenses increased the most? | `summary` | Intent & Operation Missing | Fallback to default summary. Dataset contains `unit_cost` but no recurring expense tracker. Did not report honest "data missing". |
| 6 | Find unusual transactions. | `outliers` | Partial | Returned z-score outliers on revenue ($6,000 transaction), but lacks row references and explanations. |
| 7 | What is the average order value? | `revenue_margins` | Plan Granularity | Returns full revenue and margin block ($28,100, 40.68%) rather than a direct, targeted answer for AOV ($2,810.00). |
| 8 | Show monthly revenue trend. | `trend_growth` | Operation Missing | Returned high-level trajectory text without structured monthly table or chart payload. |
| 9 | Who are the top 5 customers? | `top_customers` | Partial | Returns top customers by revenue, but lacks order counts and source references. |
| 10 | What are the three most important actions for this business? | `summary` | Operation Missing | Defaulted to summary. Failed to query `analysis.insights` which already contains prioritized executive recommendations. |
| 11 | Show me the evidence behind the top insight. | `summary` | Operation Missing | Defaulted to summary. No operation existed to look up specific insight evidence, formulas, and source rows. |
| 12 | How many duplicate rows are there? | `data_quality` | Operation Missing | `data_quality` only returned row count (10) and column count (11). Did not calculate duplicates (0 duplicates). |
| 13 | Which columns have missing values? | `data_quality` | Operation Missing | Did not inspect per-column null counts or report that 0 columns have missing values. |
| 14 | What was the total sales in March? | `revenue_margins` | Filtering Missing | Returned total sales for all 3 months ($28,100.00) instead of filtering rows where `order_date` is in March ($8,600.00). |
| 15 | What is the weather tomorrow? | `summary` | Out-of-Domain / Honest Error Missing | Defaulted to dataset summary, outputting revenue and margin rather than honestly reporting that weather is not in the dataset. |

---

### 4. Step 2 Fix: Before-and-After Comparison

| # | Question | Before (Old Broken Response) | After (Verified Grounded Response) | Operation Executed |
|---|---|---|---|---|
| 1 | Which products generate the most profit? | Listed top products by revenue ($9,600 for Pro Laptop 15). Ignored profit. | Correctly identified **Pro Laptop 15** ($3,200.00 profit) followed by Standing Desk ($1,500.00 profit). | `top_n` |
| 2 | Which region has the highest revenue? | Grouped by product category (Electronics $17.5k). Dropped region completely. | Correctly identified **North** region with **$10,400.00** (37.01% of total revenue). | `group_by_sum` |
| 3 | Compare the performance of different regions. | Output category breakdown (Electronics, Furniture, Office Supplies). | Formatted regional comparison: North ($10,400), West ($7,200), East ($5,700), South ($4,800). | `compare_groups` |
| 4 | Why did revenue decrease last month? | Generic trajectory note (-14.00%). No explanation of causes. | Detailed revenue drivers from Feb to Mar, identifying product shifts and price changes. | `top_drivers_of_change` |
| 5 | Which expenses increased the most? | Outputted total sales revenue summary ($28,100). | Honest missing data: reported that the dataset does not contain operational expense categories. | `unanswerable` |
| 6 | Find unusual transactions. | Z-score alert without row numbers or identifier breakdown. | Identified Row 1 (ORD-1001, Pro Laptop 15) for **$6,000.00** as a statistical outlier. | `find_outliers` |
| 7 | What is the average order value? | Block of revenue, gross profit, margin, and transaction count. | Targeted answer: **$2,810.00** average order value across 10 transactions. | `average` |
| 8 | Show monthly revenue trend. | Vague directional note. | Month-by-month trajectory: Jan ($10,000), Feb ($9,500), Mar ($8,600) with chart/table payload. | `monthly_trend` |
| 9 | Who are the top 5 customers? | Cluttered overview. | Ranked list: #1 CUST-201 ($9,200), #2 CUST-202 ($4,800), #3 CUST-207 ($3,600), etc. | `top_n` |
| 10 | What are the three most important actions for this business? | Dumped row count and column count. | Top prioritized recommendations from synthesized analysis insights. | `list_top_insights` |
| 11 | Show me the evidence behind the top insight. | Dumped summary stats. | Audit trace: observed fact, formula (`sum(revenue)`), raw evidence, and row range. | `get_insight_evidence` |
| 12 | How many duplicate rows are there? | Stated dataset has 10 rows and 11 columns. | Hand-verified answer: **0 duplicate rows** across all 10 verified records. | `duplicate_report` |
| 13 | Which columns have missing values? | Generic descriptive stats. | Full column report: all 11 columns are complete with **0 missing values**. | `missing_values_report` |
| 14 | What was the total sales in March? | Stated total sales were $28,100.00 (all 3 months). | Filtered exact month sales: **$8,600.00** in March 2026. | `monthly_trend` |
| 15 | What is the weather tomorrow? | Outputted sales summary ($28,100.00 revenue). | Honest response: "Your data does not contain what is needed... does not include weather forecasts." | `unanswerable` |

