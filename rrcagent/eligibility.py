"""Deterministic eligibility rules engine.

Evaluates a profile against study-specific inclusion/exclusion rules.
No LLM involvement — purely rules-driven.
"""

from __future__ import annotations


_YES = {"yes", "y", "true", "1"}
_NO = {"no", "n", "false", "0"}


def _coerce_to_bool(value) -> bool | None:
    """Coerce a string yes/no value to a Python bool, or return None."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in _YES:
        return True
    if isinstance(value, str) and value.strip().lower() in _NO:
        return False
    return None


def evaluate(
    profile: dict, rules: dict
) -> tuple[str, list[str]]:
    """Evaluate a profile against eligibility rules.

    Args:
        profile: Dict of field -> value from the lead's collected data.
        rules: Dict with 'inclusion' and 'exclusion' lists of rule objects.

    Returns:
        Tuple of (outcome_code, reason_codes) where outcome_code is one of
        QUALIFIED, DISQUALIFIED, or NEEDS_HUMAN.
    """
    reasons: list[str] = []
    has_missing = False

    # Check inclusion criteria
    for rule in rules.get("inclusion", []):
        field = rule["field"]
        if field not in profile or profile[field] is None:
            has_missing = True
            reasons.append(f"{field}_missing")
            continue

        value = profile[field]
        operator = rule["operator"]

        if operator == "between":
            low, high = rule["values"]
            if not (low <= value <= high):
                reasons.append(f"{field}_out_of_range")
        elif operator == ">=":
            if value < rule["value"]:
                reasons.append(f"{field}_below_minimum")
        elif operator == "==":
            cmp_value = value
            if isinstance(rule["value"], bool):
                coerced = _coerce_to_bool(value)
                if coerced is not None:
                    cmp_value = coerced
            if cmp_value != rule["value"]:
                reasons.append(f"{field}_not_met")

    # Check exclusion criteria
    for rule in rules.get("exclusion", []):
        field = rule["field"]
        if field not in profile or profile[field] is None:
            continue  # Can't exclude on missing data

        value = profile[field]
        operator = rule["operator"]

        if operator == "==":
            cmp_value = value
            if isinstance(rule["value"], bool):
                coerced = _coerce_to_bool(value)
                if coerced is not None:
                    cmp_value = coerced
            if cmp_value == rule["value"]:
                reasons.append(f"{field}_excluded")
        elif operator == "contains_any":
            if isinstance(value, str):
                value_lower = value.lower()
                if any(v.lower() in value_lower for v in rule["values"]):
                    reasons.append(f"{field}_excluded")

    # Determine outcome
    if has_missing:
        return "NEEDS_HUMAN", reasons

    disqualify_reasons = [r for r in reasons if "missing" not in r]
    if disqualify_reasons:
        return "DISQUALIFIED", disqualify_reasons

    return "QUALIFIED", []
