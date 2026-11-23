# backend/app/insights/priority.py
# Transparent, rule-based priority ranking for insight objects (PRD Section 5.4).

from typing import Any, Dict


class InsightPriorityScorer:
    """
    Ranks insights deterministically based on four transparent factors:
    1. Impact: Financial magnitude or percentage of business affected.
    2. Urgency: Downward trajectories or high-severity anomalies requiring immediate intervention.
    3. Data Reliability: Statistical sample size and extraction completeness.
    4. Relevance: Core profit/loss drivers vs auxiliary metadata.
    """

    @classmethod
    def calculate_priority(
        cls,
        category: str,
        evidence: Dict[str, Any],
        is_negative_trend: bool = False,
    ) -> str:
        """
        Calculates priority tier: 'critical', 'high', 'medium', or 'low'.
        Ranking rules are auditable and reproducible without opaque heuristics.
        """
        score = 0

        # Factor 1: Impact
        # High concentration (>50% revenue in one category) or severe margin deficit
        if "percentage_of_total" in evidence and evidence["percentage_of_total"] >= 50.0:
            score += 4
        elif "share_pct" in evidence and evidence["share_pct"] >= 30.0:
            score += 3

        if "gross_margin_percentage" in evidence:
            margin = evidence["gross_margin_percentage"]
            if margin < 15.0:  # Dangerously low margin
                score += 4
            elif margin >= 35.0:  # Key profit driver
                score += 3
            else:
                score += 2

        # Factor 2: Urgency
        if is_negative_trend:
            score += 3

        if "growth_percentage" in evidence and evidence["growth_percentage"] is not None:
            g = evidence["growth_percentage"]
            if g < -10.0:
                score += 3
            elif g > 15.0:
                score += 2

        if "z_score" in evidence and evidence["z_score"] >= 2.5:
            score += 3

        # Factor 3: Category Weight
        category_weights = {
            "risk": 4,
            "revenue": 3,
            "efficiency": 3,
            "customer": 2,
            "inventory": 2,
        }
        score += category_weights.get(category.lower(), 1)

        # Map total score to priority tier
        if score >= 8:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        return "low"
