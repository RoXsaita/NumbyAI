#!/usr/bin/env python3
"""Categorize the provided bank transactions into predefined categories"""

import json
import re
from typing import List, Dict, Any, Optional
from app.database import SessionLocal, CategorizationPreference, CategorizationRule, resolve_user_id
from app.tools.category_helpers import PREDEFINED_CATEGORIES

# Transactions to categorize
transactions = [
    {
        "date": "2025-01-02",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 15.50 PLN ZABKA ZE087 K.1 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -15.5,
        "currency": "PLN",
        "balance": None,
        "id": 81
    },
    {
        "date": "2025-01-02",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 34.90 PLN GREEN COFFEE WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -34.9,
        "currency": "PLN",
        "balance": None,
        "id": 82
    }
]


def match_merchant_pattern(pattern: str, merchant: str, description: str) -> bool:
    """Check if merchant pattern matches transaction merchant or description.
    
    Supports:
    - Exact match
    - Wildcard pattern (e.g., "NETFLIX*")
    - Substring match
    """
    pattern_upper = pattern.upper()
    merchant_upper = merchant.upper()
    description_upper = description.upper()
    
    # Handle wildcard patterns
    if pattern_upper.endswith("*"):
        prefix = pattern_upper[:-1]
        return prefix in merchant_upper or prefix in description_upper
    
    # Exact or substring match
    return pattern_upper in merchant_upper or pattern_upper in description_upper


def categorize_transaction(
    tx: Dict[str, Any],
    categorization_preferences: List[Dict],
    categorization_rules: List[Dict]
) -> str:
    """Categorize a single transaction based on rules and patterns."""
    merchant = tx.get("merchant", "") or ""
    description = tx.get("description", "") or ""
    
    # First, check CategorizationPreference rules (higher priority)
    # Sort by priority descending
    sorted_prefs = sorted(
        categorization_preferences,
        key=lambda x: x.get("priority", 0),
        reverse=True
    )
    
    for pref in sorted_prefs:
        rule = pref.get("rule", {})
        conditions = rule.get("conditions", {})
        merchant_pattern = conditions.get("merchant")
        
        if merchant_pattern and match_merchant_pattern(merchant_pattern, merchant, description):
            category = rule.get("category")
            if category in PREDEFINED_CATEGORIES:
                return category
    
    # Then check CategorizationRule (simpler merchant pattern matching)
    for rule in categorization_rules:
        merchant_pattern = rule.get("merchant_pattern", "")
        if merchant_pattern and match_merchant_pattern(merchant_pattern, merchant, description):
            category = rule.get("category")
            if category in PREDEFINED_CATEGORIES:
                return category
    
    # If no rule matches, analyze description and merchant
    desc_lower = description.lower()
    merchant_lower = merchant.lower()
    
    # Income - check for salary/wages
    if "wynagrodzenie" in desc_lower or "salary" in desc_lower or "wage" in desc_lower:
        return "Income"
    
    # Debt Payments
    if "spłata kredytu" in desc_lower or "loan payment" in desc_lower or "debt" in desc_lower:
        return "Debt Payments"
    
    # Insurance
    if "ubezp" in desc_lower or "insurance" in desc_lower:
        return "Insurance"
    
    # Healthcare - pharmacy
    if "apteka" in desc_lower or "pharmacy" in desc_lower or "drug" in desc_lower:
        return "Healthcare"
    
    # Transportation
    if "bolt" in desc_lower or "uber" in desc_lower or "taxi" in desc_lower or "careem" in desc_lower:
        return "Transportation"
    
    # Entertainment
    if "cinema" in desc_lower or "netflix" in desc_lower or "lounge" in desc_lower or "klub" in desc_lower or "club" in desc_lower:
        return "Entertainment"
    
    # Food & Groceries
    grocery_keywords = [
        "carrefour", "lidl", "zabka", "warzywa", "owoce", "groceries",
        "supermarket", "hipermarket", "wesola pani", "bistro", "restaurant",
        "food", "herbate", "cafe", "café", "goraco", "polecam", "horeca",
        "vincent", "thai wok", "green coffee", "pijalnia", "burger", "burge"
    ]
    if any(kw in desc_lower for kw in grocery_keywords):
        return "Food & Groceries"
    
    # Shopping
    shopping_keywords = ["tk maxx", "hebe", "decathlon", "shopping", "store", "retail"]
    if any(kw in desc_lower for kw in shopping_keywords):
        return "Shopping"
    
    # Travel
    if "odyssey" in desc_lower or "travel" in desc_lower or "hotel" in desc_lower:
        return "Travel"
    
    # Software/Subscriptions (Other)
    if "venice.ai" in desc_lower or "cursor" in desc_lower or "ai powered ide" in desc_lower or "godaddy" in desc_lower:
        return "Other"
    
    # Fees and charges (Other)
    if "prowizja" in desc_lower or "fee" in desc_lower or "przewalutowanie" in desc_lower:
        return "Other"
    
    # Payment services (Other)
    if "paypro" in desc_lower or "blik" in desc_lower or "payu" in desc_lower:
        return "Other"
    
    # Public transport (Transportation)
    if "aut." in desc_lower or "mera-mza" in desc_lower or "public transport" in desc_lower:
        return "Transportation"
    
    # Default
    return "Other"


def main():
    """Main function to categorize all transactions."""
    db = SessionLocal()
    try:
        user_id = resolve_user_id()
        
        # Fetch categorization preferences
        prefs = (
            db.query(CategorizationPreference)
            .filter(
                CategorizationPreference.user_id == user_id,
                CategorizationPreference.preference_type == "categorization",
                CategorizationPreference.enabled.is_(True)
            )
            .order_by(CategorizationPreference.priority.desc())
            .all()
        )
        
        categorization_preferences = []
        for pref in prefs:
            categorization_preferences.append({
                "id": str(pref.id),
                "name": pref.name,
                "bank_name": pref.bank_name,
                "rule": pref.rule,
                "priority": pref.priority,
            })
        
        # Fetch categorization rules
        rules = (
            db.query(CategorizationRule)
            .filter(
                CategorizationRule.user_id == user_id,
                CategorizationRule.enabled.is_(True)
            )
            .all()
        )
        
        categorization_rules = []
        for rule in rules:
            categorization_rules.append({
                "id": str(rule.id),
                "merchant_pattern": rule.merchant_pattern,
                "category": rule.category,
                "confidence_score": rule.confidence_score,
            })
        
        # Categorize all transactions
        results = []
        for tx in transactions:
            category = categorize_transaction(tx, categorization_preferences, categorization_rules)
            results.append({
                "id": tx["id"],
                "category": category
            })
        
        # Output JSON
        print(json.dumps(results, indent=2))
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
