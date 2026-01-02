"""Categorization rules engine for preferences."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.logger import create_logger
from app.tools.category_helpers import normalize_category

logger = create_logger("categorization_rules")


@dataclass(frozen=True)
class CategorizationRule:
    id: str
    name: str
    bank_name: Optional[str]
    priority: int
    rule: Dict[str, Any]


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _looks_like_regex(pattern: str) -> bool:
    return any(ch in pattern for ch in ("^", "$", "[", "]", "(", ")", "|", "\\"))


def _compile_pattern(pattern: str) -> Optional[re.Pattern]:
    if not pattern:
        return None
    if "*" in pattern or "?" in pattern:
        escaped = re.escape(pattern).replace("\\*", ".*").replace("\\?", ".")
        return re.compile(escaped, re.IGNORECASE)
    if _looks_like_regex(pattern):
        try:
            return re.compile(pattern, re.IGNORECASE)
        except re.error:
            return None
    return None


def _match_pattern(value: Optional[str], pattern: Any) -> bool:
    if not value:
        return False
    if isinstance(pattern, list):
        return any(_match_pattern(value, p) for p in pattern)
    if not isinstance(pattern, str):
        return False
    trimmed = pattern.strip()
    if not trimmed:
        return False
    regex = _compile_pattern(trimmed)
    if regex:
        return bool(regex.search(value))
    return trimmed.lower() in value.lower()


def _extract_conditions(rule: Dict[str, Any]) -> Dict[str, Any]:
    conditions = {}
    raw_conditions = rule.get("conditions")
    if isinstance(raw_conditions, dict):
        conditions.update(raw_conditions)
    return conditions


def _rule_matches_transaction(tx: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    conditions = _extract_conditions(rule)

    merchant_pattern = rule.get("merchant_pattern") or conditions.get("merchant")
    description_pattern = rule.get("description_pattern") or conditions.get("description")
    generic_pattern = rule.get("pattern") or rule.get("merchant") or rule.get("description")

    amount_min = rule.get("amount_min") or conditions.get("amount_min")
    amount_max = rule.get("amount_max") or conditions.get("amount_max")

    amount_value = _to_decimal(tx.get("amount"))
    if amount_value is not None:
        min_value = _to_decimal(amount_min)
        max_value = _to_decimal(amount_max)
        if min_value is not None and amount_value < min_value:
            return False
        if max_value is not None and amount_value > max_value:
            return False

    description = tx.get("description") or ""
    merchant = tx.get("merchant") or ""
    vendor_payee = tx.get("vendor_payee") or ""

    if merchant_pattern:
        if _match_pattern(merchant, merchant_pattern) or _match_pattern(vendor_payee, merchant_pattern):
            return True
        return False

    if description_pattern:
        return _match_pattern(description, description_pattern)

    if generic_pattern:
        return (
            _match_pattern(merchant, generic_pattern)
            or _match_pattern(vendor_payee, generic_pattern)
            or _match_pattern(description, generic_pattern)
        )

    return False


def apply_categorization_rules(
    transactions: List[Dict[str, Any]],
    rules: List[CategorizationRule]
) -> Tuple[Dict[int, str], List[Dict[str, Any]]]:
    """
    Apply categorization rules to transactions.

    Returns:
        (categorized_map, uncategorized_transactions)
    """
    categorized_map: Dict[int, str] = {}
    remaining: List[Dict[str, Any]] = []

    for tx in transactions:
        tx_id = tx.get("id")
        if tx_id is None:
            remaining.append(tx)
            continue

        existing_category = normalize_category(tx.get("category") or "")
        if existing_category:
            categorized_map[tx_id] = existing_category
            continue

        matched = None
        for rule in rules:
            if not isinstance(rule.rule, dict):
                continue
            if not _rule_matches_transaction(tx, rule.rule):
                continue
            category = normalize_category(rule.rule.get("category") or "")
            if not category:
                logger.warn("Rule category invalid; skipping", {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "category": rule.rule.get("category"),
                })
                continue
            matched = category
            break

        if matched:
            categorized_map[tx_id] = matched
        else:
            remaining.append(tx)

    return categorized_map, remaining


def format_rules_for_prompt(rules: Iterable[CategorizationRule]) -> str:
    lines: List[str] = []
    for rule in rules:
        if not isinstance(rule.rule, dict):
            continue
        category = normalize_category(rule.rule.get("category") or "")
        if not category:
            continue
        conditions = _extract_conditions(rule.rule)
        merchant_pattern = rule.rule.get("merchant_pattern") or conditions.get("merchant")
        description_pattern = rule.rule.get("description_pattern") or conditions.get("description")
        generic_pattern = rule.rule.get("pattern") or rule.rule.get("merchant") or rule.rule.get("description")

        if merchant_pattern:
            lines.append(f"- If merchant matches '{merchant_pattern}', assign category '{category}'")
        elif description_pattern:
            lines.append(f"- If description matches '{description_pattern}', assign category '{category}'")
        elif generic_pattern:
            lines.append(f"- If merchant or description matches '{generic_pattern}', assign category '{category}'")

    if not lines:
        return ""
    return "\nExisting categorization rules (apply these first):\n" + "\n".join(lines)


def normalize_rule_input(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize rule schema for persistence and evaluation."""
    if "pattern" in rule and "merchant_pattern" not in rule and "description_pattern" not in rule:
        rule = {**rule, "merchant_pattern": rule.get("pattern")}
    return rule
