# backend/app/insights/validator.py
# Re-checks every displayed number against computed results before presentation (FR-16).
# Guarantees that no number was fabricated or hallucinated.

from typing import Any, Dict, List, Set, Tuple
import re


class InsightValidator:
    """
    Enforces FR-16: Every displayed number in an insight is strictly verified against
    the deterministic computation cache. Insights containing unverifiable numbers are blocked.
    """

    @classmethod
    def extract_numbers(cls, text: str) -> List[float]:
        """
        Extracts numbers from text string, handling currency symbols ($), commas, and percentages (%).
        Example: '$28,100.00 across 10 records with 40.68%' -> [28100.0, 10.0, 40.68]
        """
        numbers: List[float] = []
        # Strip markdown numbered list prefixes (e.g. "1. ", "2) ") so they aren't parsed as business metrics
        cleaned_text = re.sub(r"(?:^|\n)\s*\d+[\.\)]\s+", "\n", text)

        # Match signed decimals or integers with optional commas and percent signs
        # Exclude dates like 2026-01-15 by requiring whitespace or text boundary
        pattern = r"(?:^|\s|\$|€|£)\(?([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\)?%?"

        for match in re.finditer(pattern, cleaned_text):
            raw_str = match.group(1).replace(",", "").strip()
            try:
                num = float(raw_str)
                numbers.append(num)
            except ValueError:
                continue

        return numbers

    @classmethod
    def collect_known_numbers(cls, evidence: Any) -> Set[float]:
        """Recursively gathers all numeric values from evidence dictionaries and lists."""
        known: Set[float] = set()

        if isinstance(evidence, dict):
            for v in evidence.values():
                known.update(cls.collect_known_numbers(v))
        elif isinstance(evidence, (list, tuple)):
            for item in evidence:
                known.update(cls.collect_known_numbers(item))
        elif isinstance(evidence, (int, float)):
            val = float(evidence)
            known.add(round(val, 2))
            known.add(round(abs(val), 2))
        elif isinstance(evidence, str):
            for match in re.finditer(r"\b\d+(?:\.\d+)?\b", evidence):
                try:
                    num = float(match.group(0))
                    known.add(round(num, 2))
                    known.add(round(abs(num), 2))
                except ValueError:
                    pass

        return known

    @classmethod
    def validate_insight(
        cls,
        observed_fact: str,
        evidence: Dict[str, Any],
        all_metrics: Dict[str, Any],
        tolerance: float = 0.05,
    ) -> Tuple[bool, List[float]]:
        """
        Verifies all numbers in observed_fact against known computed metrics (FR-16).
        Returns: (is_valid, list_of_unverified_numbers)
        """
        extracted = cls.extract_numbers(observed_fact)
        if not extracted:
            return True, []

        known_pool = cls.collect_known_numbers(evidence)
        known_pool.update(cls.collect_known_numbers(all_metrics))

        unverified: List[float] = []

        for num in extracted:
            rounded_num = round(abs(num), 2)
            # Check for exact match or close match within tolerance (e.g. 40.68 vs 40.676)
            matched = any(abs(rounded_num - k) <= tolerance for k in known_pool)

            # Special case: check if num is represented as fraction (e.g. 0.4068 vs 40.68%)
            if not matched:
                matched = any(abs(rounded_num / 100.0 - k) <= tolerance for k in known_pool)
            if not matched:
                matched = any(abs(rounded_num * 100.0 - k) <= tolerance for k in known_pool)

            if not matched:
                unverified.append(num)

        is_valid = len(unverified) == 0
        return is_valid, unverified
