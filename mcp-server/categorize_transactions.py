#!/usr/bin/env python3
"""
Categorize bank transactions using existing rules and keyword analysis.
"""
import json
import sys
from typing import Dict, Any, List
from app.database import SessionLocal, CategorizationPreference, CategorizationRule, resolve_user_id
from app.tools.category_helpers import PREDEFINED_CATEGORIES

# Transactions to categorize
TRANSACTIONS = [
    {
        "date": "2025-01-22",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 73.80 PLN MULTIKINO S.A. Warszawa",
        "merchant": "DOP. MC 557519******1802",
        "amount": -73.8,
        "currency": "PLN",
        "balance": None,
        "id": 21
    },
    {
        "date": "2025-01-22",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 27.47 PLN ZABKA Z6502 K.1 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -27.47,
        "currency": "PLN",
        "balance": None,
        "id": 22
    },
    {
        "date": "2025-01-21",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 11.66 PLN WARZYWA I OWOCE ANIA Warszawa",
        "merchant": "DOP. MC 557519******1802",
        "amount": -11.66,
        "currency": "PLN",
        "balance": None,
        "id": 23
    },
    {
        "date": "2025-01-20",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 8.79 PLN CARREFOUR EXPRESS V55 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -8.79,
        "currency": "PLN",
        "balance": None,
        "id": 24
    },
    {
        "date": "2025-01-20",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 5.29 PLN CARREFOUR EXPRESS V55 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -5.29,
        "currency": "PLN",
        "balance": None,
        "id": 25
    },
    {
        "date": "2025-01-20",
        "description": "Prowizja za przewalutowanie transakcji dot.karty 557519******1802",
        "merchant": "PROWIZJA ZA PRZEWALUTOWANIE",
        "amount": -1.86,
        "currency": "PLN",
        "balance": None,
        "id": 26
    },
    {
        "date": "2025-01-19",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 15.58 USD 15.58 USD 1 USD=4.2655 PLN X CORP. PAID FEATURES SAN FRANCISCO",
        "merchant": "DOP. MC 557519******1802",
        "amount": -66.46,
        "currency": "PLN",
        "balance": None,
        "id": 27
    },
    {
        "date": "2025-01-18",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 8.98 PLN PL KFC WARSZAWA PROMEN Warszawa",
        "merchant": "DOP. MC 557519******1802",
        "amount": -8.98,
        "currency": "PLN",
        "balance": None,
        "id": 28
    },
    {
        "date": "2025-01-18",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 193.21 PLN KAUFLAND 05 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -193.21,
        "currency": "PLN",
        "balance": None,
        "id": 29
    },
    {
        "date": "2025-01-18",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 44.98 PLN ROSSMANN 169 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -44.98,
        "currency": "PLN",
        "balance": None,
        "id": 30
    },
    {
        "date": "2025-01-17",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 1.89 PLN JMP S.A. BIEDRONKA 538 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -1.89,
        "currency": "PLN",
        "balance": None,
        "id": 31
    },
    {
        "date": "2025-01-17",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 18.49 PLN ZABKA ZB602 K.2 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -18.49,
        "currency": "PLN",
        "balance": None,
        "id": 32
    },
    {
        "date": "2025-01-17",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 2.98 PLN GORACO POLECAM WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -2.98,
        "currency": "PLN",
        "balance": None,
        "id": 33
    },
    {
        "date": "2025-01-17",
        "description": "Prowizja za przewalutowanie transakcji dot.karty 557519******1802",
        "merchant": "PROWIZJA ZA PRZEWALUTOWANIE",
        "amount": -1.18,
        "currency": "PLN",
        "balance": None,
        "id": 34
    },
    {
        "date": "2025-01-16",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 9.84 USD 9.84 USD 1 USD=4.2655 PLN X CORP. PAID FEATURES SAN FRANCISCO",
        "merchant": "DOP. MC 557519******1802",
        "amount": -41.97,
        "currency": "PLN",
        "balance": None,
        "id": 35
    },
    {
        "date": "2025-01-16",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 93.01 PLN CARREFOUR HIPERMARKET WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -93.01,
        "currency": "PLN",
        "balance": None,
        "id": 36
    },
    {
        "date": "2025-01-16",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 12.99 PLN UBER *ONE HELP.UBER.COM",
        "merchant": "Uber",
        "amount": -12.99,
        "currency": "PLN",
        "balance": None,
        "id": 37
    },
    {
        "date": "2025-01-16",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 29.47 PLN GORACO POLECAM WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -29.47,
        "currency": "PLN",
        "balance": None,
        "id": 38
    },
    {
        "date": "2025-01-14",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 388.31 PLN LIDL BORA KOMOROWSKIEG WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -388.31,
        "currency": "PLN",
        "balance": None,
        "id": 39
    },
    {
        "date": "2025-01-13",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 17.98 PLN ZABKA ZA757 K.1 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -17.98,
        "currency": "PLN",
        "balance": None,
        "id": 40
    }
]


def match_merchant_pattern(pattern: str, merchant: str, description: str) -> bool:
    """
    Match merchant pattern against merchant name or description.
    
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
    merchant = tx.get("merchant", "")
    description = tx.get("description", "")
    
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
    combined_text = f"{description} {merchant}".lower()
    
    # Income - check for salary/wages
    if "wynagrodzenie" in desc_lower or "salary" in desc_lower or "wage" in desc_lower:
        return "Income"
    
    # Debt Payments
    if "spłata kredytu" in desc_lower or "loan payment" in desc_lower or "debt" in desc_lower:
        return "Debt Payments"
    
    # Insurance
    if "ubezp" in desc_lower or "insurance" in desc_lower:
        return "Insurance"
    
    # Healthcare - pharmacy (ROSSMANN is a pharmacy/drugstore chain)
    if "apteka" in desc_lower or "pharmacy" in desc_lower or "drug" in desc_lower or "rossmann" in combined_text:
        return "Healthcare"
    
    # Transportation
    if "bolt" in desc_lower or "uber" in combined_text or "taxi" in desc_lower or "careem" in desc_lower:
        return "Transportation"
    
    # Entertainment - MULTIKINO is a cinema chain
    if "netflix" in desc_lower or "multikino" in combined_text or "cinema" in desc_lower or "movie" in desc_lower:
        return "Entertainment"
    
    # Food & Groceries
    grocery_keywords = [
        "carrefour", "lidl", "zabka", "warzywa", "owoce", "groceries",
        "supermarket", "hipermarket", "wesola pani", "bistro", "restaurant",
        "food", "herbate", "cafe", "café", "goraco", "polecam", "horeca",
        "vincent", "kaufland", "kfc", "biedronka"
    ]
    if any(kw in combined_text for kw in grocery_keywords):
        return "Food & Groceries"
    
    # Shopping
    shopping_keywords = ["tk maxx", "hebe", "decathlon", "shopping", "store", "retail"]
    if any(kw in desc_lower for kw in shopping_keywords):
        return "Shopping"
    
    # Travel
    if "odyssey" in desc_lower or "travel" in desc_lower or "hotel" in desc_lower:
        return "Travel"
    
    # Fees and charges (Other)
    if "prowizja" in desc_lower or "fee" in desc_lower or "przewalutowanie" in desc_lower:
        return "Other"
    
    # Payment services (Other)
    if "paypro" in desc_lower or "blik" in desc_lower or "payu" in desc_lower:
        return "Other"
    
    # Software/Subscriptions (Other) - X CORP. PAID FEATURES is likely a software subscription
    if "venice.ai" in desc_lower or "cursor" in desc_lower or "ai powered ide" in desc_lower or "x corp" in combined_text:
        return "Other"
    
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
        for tx in TRANSACTIONS:
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
