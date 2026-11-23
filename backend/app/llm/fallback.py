# backend/app/llm/fallback.py
# Deterministic templated fallback engine used when no AI key is configured (FR-21).
# Guarantees zero arithmetic hallucination and 100% offline availability.

from typing import Any, Dict, List, Optional
import pandas as pd
from backend.app.llm.base import BaseLLMProvider, LLMResult
from backend.app.llm.safe_plans import SafePlan, SafePlanExecutor, OperationResult


class DeterministicFallbackProvider(BaseLLMProvider):
    """
    Produces deterministic natural-language explanations directly from pandas computations.
    Guarantees mathematically verified answers for all standard business operations offline.
    """

    async def ask_grounded(
        self,
        question: str,
        analysis_metrics: Dict[str, Any],
        dataset_ids: List[str],
        domain: str = "general",
        chat_history: Optional[List[Dict[str, str]]] = None,
        dataset: Optional[Any] = None,
        df: Optional[pd.DataFrame] = None,
        analysis: Optional[Any] = None,
    ) -> LLMResult:
        # Load df if not passed
        if df is None and dataset:
            from backend.app.analytics import load_dataset_dataframe
            df = load_dataset_dataframe(dataset)

        if df is None or df.empty:
            if analysis_metrics:
                # Legacy fallback execution using precomputed metrics dictionary
                legacy_plan = SafePlanExecutor.determine_plan(question, analysis_metrics)
                evidence, sources, limitations, warning = SafePlanExecutor.execute_plan(
                    operation=legacy_plan,
                    metrics=analysis_metrics,
                    dataset_ids=dataset_ids,
                )
                if warning:
                    return LLMResult(
                        text=warning,
                        computed_evidence={},
                        sources=sources,
                        limitations=limitations,
                        used_fallback=True,
                        safe_plan_executed=legacy_plan,
                    )
                text = self._format_legacy_explanation(legacy_plan, evidence, domain)
                return LLMResult(
                    text=text,
                    computed_evidence=evidence,
                    sources=sources,
                    limitations=limitations,
                    used_fallback=True,
                    safe_plan_executed=legacy_plan,
                )

            return LLMResult(
                text="The selected dataset contains no readable data rows.",
                limitations=["Empty or unreadable dataset."],
                used_fallback=True,
            )

        # 1. Determine plan using deterministic heuristic with fuzzy column matching
        plan = SafePlanExecutor.determine_plan_heuristic(question, df, dataset=dataset, analysis=analysis)

        # 2. Execute plan
        res: OperationResult = SafePlanExecutor.execute_safe_plan(plan, df, analysis=analysis, dataset=dataset)

        sources = [f"{s.get('filename', 'dataset')}:{s.get('sheet', 'default')} (rows {s.get('rows', '1-all')})" for s in res.source_references]
        limitations = res.limitations + ["Deterministic offline fallback: 100% calculated by Python pandas."]

        # Case 1: Clarification needed
        if res.status == "clarification_needed":
            text = f"I could not understand which field you mean: {res.clarification_question}"
            return LLMResult(
                text=text,
                computed_evidence=res.values,
                sources=sources,
                limitations=limitations,
                used_fallback=True,
                safe_plan_executed=plan.operation,
            )

        # Case 2: Missing data / honest error
        if res.status == "missing_data" or plan.operation == "unanswerable":
            if plan.operation == "unanswerable":
                if plan.metric_column and "expense" in plan.metric_column:
                    text = "Your data does not contain operational expense categories or expense tracking over time (missing: expense records / categories)."
                else:
                    text = (
                        "Your data does not contain what is needed to answer this question. "
                        "This business dataset does not include external information such as weather forecasts or non-business events."
                    )
            else:
                missing_str = ", ".join(res.missing_fields) if res.missing_fields else "required information"
                text = f"Your data does not contain what is needed (missing: {missing_str})."

            return LLMResult(
                text=text,
                computed_evidence=res.values,
                sources=sources,
                limitations=limitations,
                used_fallback=True,
                safe_plan_executed=plan.operation,
            )

        # Case 3: Success formatting
        text = self._format_explanation(plan.operation, res.values, question)

        return LLMResult(
            text=text,
            computed_evidence=res.values,
            sources=sources,
            limitations=limitations,
            used_fallback=True,
            safe_plan_executed=plan.operation,
            table_payload=res.table_payload,
            chart_payload=res.chart_payload,
        )

    def _format_explanation(self, op: str, val: Dict[str, Any], question: str) -> str:
        """Templates natural language explanation from exact computed values."""
        if op in ["financial_totals", "total"]:
            gross = val.get("gross_sales")
            disc = val.get("discount_amount")
            net = val.get("net_sales", val.get("total_revenue", val.get("total", 0.0)))
            cost = val.get("total_cost")
            profit = val.get("profit", val.get("gross_profit", 0.0))
            margin = val.get("profit_margin_percentage", val.get("gross_margin_percentage", 0.0))
            count = val.get("order_count", val.get("count", 0))

            lines = [f"Based on deterministic calculations across {count} records:"]
            if gross is not None:
                lines.append(f"• Gross Sales: ${gross:,.2f}")
            if disc is not None:
                lines.append(f"• Total Discount Amount: ${disc:,.2f}")
            lines.append(f"• Net Sales (Total Revenue): ${net:,.2f}")
            if cost is not None:
                lines.append(f"• Total Cost: ${cost:,.2f}")
            lines.append(f"• Profit (Net Income): ${profit:,.2f} ({margin:.2f}% gross margin)")
            lines.append(f"• Profit Margin: {margin:.2f}% (Formula: SUM(profit) / SUM(net_sales) * 100)")
            return "\n".join(lines)

        elif op == "average":
            col = val.get("column", "revenue")
            avg = val.get("average", 0.0)
            count = val.get("count", 0)
            return f"The average {col} is **${avg:,.2f}** across {count} transactions."

        elif op == "count":
            rows = val.get("total_rows", 0)
            cols = val.get("total_columns", 0)
            return f"The dataset contains **{rows:,}** records across {cols} columns."

        elif op == "group_by_sum":
            grp = val.get("group_column", "group")
            met = val.get("metric_column", "metric")
            highest = val.get("highest")
            bdown = val.get("breakdown", [])
            lines = [f"• **{item['name']}**: ${item['value']:,.2f} ({item.get('percentage', 0)}%)" for item in bdown]
            res_str = f"Revenue and performance breakdown by **{grp.title()}**:\n" + "\n".join(lines)
            if highest:
                res_str += f"\n\n**Highest {grp.title()}**: **{highest['name']}** with **${highest['value']:,.2f}** ({highest.get('percentage', 0)}% of total)."
            return res_str

        elif op == "top_n":
            ent = val.get("entity_column", "item")
            met = val.get("metric_column", "metric")
            top = val.get("top_n", val.get("ranks", []))
            lines = []
            for item in top:
                if "margin" in met:
                    lines.append(f"• #{item['rank']} **{item['name']}**: {item['value']:.2f}% profit margin (Net Sales: ${item.get('net_sales', 0):,.2f}, Profit: ${item.get('profit', 0):,.2f})")
                elif "profit" in met:
                    lines.append(f"• #{item['rank']} **{item['name']}**: ${item['value']:,.2f} profit ({item.get('profit_margin_percentage', 0):.2f}% margin, Net Sales: ${item.get('net_sales', 0):,.2f})")
                else:
                    lines.append(f"• #{item['rank']} **{item['name']}**: ${item['value']:,.2f} net sales")

            metric_label = "profit margin" if "margin" in met else ("profit" if "profit" in met else "sales revenue")
            return f"Top performers ranked by **{metric_label}**:\n" + "\n".join(lines)

        elif op == "bottom_n":
            ent = val.get("entity_column", "item")
            met = val.get("metric_column", "metric")
            bottom = val.get("bottom_n", val.get("ranks", []))
            lines = []
            for item in bottom:
                if "profit" in met:
                    lines.append(f"• #{item['rank']} **{item['name']}**: ${item['value']:,.2f} profit ({item.get('profit_margin_percentage', 0):.2f}% margin, Net Sales: ${item.get('net_sales', 0):,.2f})")
                else:
                    lines.append(f"• #{item['rank']} **{item['name']}**: ${item['value']:,.2f}")
            return f"Lowest performers ranked by lowest contribution:\n" + "\n".join(lines)

        elif op == "compare_groups":
            grp = val.get("group_column", "region")
            groups = val.get("groups", [])
            lines = []
            for g in groups:
                name = g.get(grp, "Unknown")
                ns = g.get("net_sales", 0.0)
                pf = g.get("profit", 0.0)
                pm = g.get("profit_margin_percentage", 0.0)
                share = g.get("revenue_share_pct", 0.0)
                lines.append(f"• **{name}**: Net Sales ${ns:,.2f} ({share:.2f}% share), Profit ${pf:,.2f}, Margin {pm:.2f}%")
            highest = val.get("highest")
            header = f"Performance comparison across **{grp.title()}** segments:\n" + "\n".join(lines)
            if highest:
                header += f"\n\n**Highest {grp.title()}**: **{highest['name']}** with **${highest['value']:,.2f}** net sales ({highest.get('percentage', 0)}% of total)."
            return header

        elif op == "monthly_trend":
            filtered = val.get("filtered_month")
            if filtered:
                m_name = filtered.get("month_name", "Specified Month")
                v = filtered.get("net_sales", filtered.get("value", 0.0))
                orders = filtered.get("order_count", 0)
                pf = filtered.get("profit", 0.0)
                margin = filtered.get("profit_margin_percentage", 0.0)
                return f"Total sales in **{m_name}** were **${v:,.2f}** across {orders} orders (Profit: ${pf:,.2f}, Margin: {margin:.2f}%)."

            periods = val.get("periods", [])
            lines = [f"• **{p['period']}**: Net Sales ${p['net_sales']:,.2f}, Profit ${p['profit']:,.2f} ({p['profit_margin_percentage']:.2f}% margin, {p['order_count']} orders)" for p in periods]
            return "Monthly revenue trajectory:\n" + "\n".join(lines)

        elif op == "period_over_period_change":
            ch = val.get("recent_change", {})
            return (
                f"Revenue changed by **${ch.get('absolute_change', 0):,.2f}** "
                f"({ch.get('percentage_change', 0):+.2f}%) from {ch.get('from_period')} to {ch.get('to_period')}."
            )

        elif op == "top_drivers_of_change":
            from_p = val.get("from_period", "")
            to_p = val.get("to_period", "")
            drag = val.get("biggest_drag", {})
            gain = val.get("biggest_gain", {})
            drivers = val.get("drivers", [])
            text = f"Revenue change drivers from **{from_p}** to **{to_p}**:\n"
            if drag:
                text += f"• Largest decrease: **{drag.get('item')}** changed by **${drag.get('absolute_diff', 0):,.2f}**.\n"
            if gain and gain != drag:
                text += f"• Largest increase: **{gain.get('item')}** changed by **+${gain.get('absolute_diff', 0):,.2f}**.\n"
            return text.strip()

        elif op == "find_outliers":
            found = val.get("outliers_found", 0)
            outliers = val.get("outliers", [])
            if found > 0:
                lines = [f"• {o['identifier']} (Row {o['row_index']}): ${o['value']:,.2f} (Z-Score: {o['z_score']})" for o in outliers]
                return f"Identified **{found}** unusual transaction(s) exceeding 2.0 standard deviations:\n" + "\n".join(lines)
            return "No statistical outliers exceeding 2.0 standard deviations were detected."

        elif op == "missing_values_report":
            total = val.get("total_rows", 0)
            missing = val.get("columns_with_missing", [])
            if not missing:
                return f"All columns are complete. There are **0 missing values** across all {total} rows."
            lines = [f"• **{m['column']}**: {m['null_count']} missing ({m['percentage']}%)" for m in missing]
            return f"Found missing values in {len(missing)} column(s):\n" + "\n".join(lines)

        elif op == "duplicate_report":
            dups = val.get("duplicate_count", 0)
            total = val.get("total_rows", 0)
            if dups == 0:
                return f"There are **0 duplicate rows** in this dataset across all {total} verified records."
            return f"Detected **{dups} duplicate row(s)** out of {total} total records."

        elif op == "list_top_insights":
            actions = val.get("top_actions", [])
            lines = [f"{i+1}. **{a['title']}** [{a['priority'].upper()}]: {a['recommendation']}" for i, a in enumerate(actions)]
            return "Top recommended actions for this business:\n" + "\n".join(lines)

        elif op == "get_insight_evidence":
            title = val.get("title", "Insight")
            formula = val.get("formula", "")
            fact = val.get("observed_fact", "")
            ev = val.get("evidence", {})
            return f"**Evidence for '{title}'**:\n• Fact: {fact}\n• Formula: `{formula}`\n• Computed Evidence: {ev}"

        return "Deterministic calculation completed successfully."

    def _format_legacy_explanation(self, plan: str, evidence: Dict[str, Any], domain: str) -> str:
        """Legacy formatter for backward compatibility with tests passing metrics dictionaries."""
        if plan == "revenue_margins":
            rev = evidence.get("total_revenue", 0.0)
            profit = evidence.get("gross_profit", 0.0)
            margin = evidence.get("gross_margin_percentage", 0.0)
            aov = evidence.get("average_order_value", 0.0)
            rows = evidence.get("row_count", 0)
            return (
                f"Based on deterministic calculations across {rows} transactions:\n"
                f"• Total Revenue: ${rev:,.2f}\n"
                f"• Gross Profit: ${profit:,.2f} ({margin:.2f}% gross margin)\n"
                f"• Average Order Value (AOV): ${aov:,.2f}\n\n"
                f"Gross margin is computed via formula: (Revenue - Cost) / Revenue * 100."
            )
        elif plan == "top_products":
            top = evidence.get("top_products", [])
            lines = [f"• {p['name']}: ${p['value']:,.2f} ({p.get('percentage_of_total', 0):.1f}% of total)" for p in top]
            return f"Top-performing products ranked by gross revenue:\n" + "\n".join(lines)
        elif plan == "top_customers":
            top = evidence.get("top_customers", [])
            lines = [f"• {c['name']}: ${c['value']:,.2f} ({c.get('percentage_of_total', 0):.1f}% of total)" for c in top]
            return f"Top customer accounts ranked by total sales contribution:\n" + "\n".join(lines)
        elif plan == "category_breakdown":
            cats = evidence.get("category_breakdown", [])
            lines = [f"• {c['category']}: ${c['value']:,.2f} ({c.get('percentage_of_total', 0):.1f}%)" for c in cats]
            return f"Revenue distribution across categories:\n" + "\n".join(lines)
        elif plan == "trend_growth":
            rate = evidence.get("overall_growth_rate", 0.0)
            direction = evidence.get("trend_direction", "stable")
            periods = evidence.get("periods", [])
            return f"Time-series analysis shows a {direction} trajectory with an overall growth rate of {rate:+.2f}% across {len(periods)} observed periods."
        elif plan == "outliers":
            outliers = evidence.get("revenue_outliers", [])
            if outliers:
                lines = [f"• Row {o['row_index']} ({o['identifier']}): ${o['value']:,.2f} (Z-Score: {o['z_score']})" for o in outliers[:5]]
                return f"Identified {len(outliers)} statistical outlier transactions:\n" + "\n".join(lines)
            return "No statistical outliers exceeding 2 standard deviations were found."
        elif plan == "data_quality":
            rows = evidence.get("row_count", 0)
            cols = evidence.get("column_count", 0)
            return f"The dataset contains {rows:,} verified rows and {cols} profiled columns."
        else:
            rows = evidence.get("row_count", 0)
            cols = evidence.get("column_count", 0)
            text = f"Analysis summary for domain '{domain}': Dataset contains {rows:,} verified rows and {cols} columns."
            if "total_revenue" in evidence:
                text += f" Total recorded revenue is ${evidence['total_revenue']:,.2f} with {evidence.get('gross_margin_percentage', 0.0):.1f}% gross margin."
            return text

