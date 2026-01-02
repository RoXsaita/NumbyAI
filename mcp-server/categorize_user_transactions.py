#!/usr/bin/env python3
"""Categorize bank transactions into predefined categories"""

import json
import re
from typing import List, Dict, Any, Optional
from app.database import SessionLocal, CategorizationPreference, CategorizationRule, resolve_user_id
from app.tools.category_helpers import PREDEFINED_CATEGORIES

# Transactions to categorize
transactions = [
    {
        "date": "2025-01-30",
        "description": "PWC wynagrodzenie za 01 2025 PRICEWATERHOUSECOOPERS POLSKA SP. Z O.O. SP.K. UL. POLNA 11 00-633 WARSZAWA ELIXIR 30-01-2025",
        "merchant": "PWC WYNAGRODZENIE ZA",
        "amount": 10804.79,
        "currency": "PLN",
        "balance": 26480.21,
        "id": 1
    },
    {
        "date": "2025-01-30",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 21.92 PLN GORACO POLECAM WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -21.92,
        "currency": "PLN",
        "balance": 26414.94,
        "id": 2
    },
    {
        "date": "2025-01-30",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 43.35 PLN ZIKO APTEKA 23 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -43.35,
        "currency": "PLN",
        "balance": 26436.86,
        "id": 3
    },
    {
        "date": "2025-01-30",
        "description": "Prowizja za przewalutowanie transakcji dot.karty 557519******1802",
        "merchant": "PROWIZJA ZA PRZEWALUTOWANIE",
        "amount": -2.15,
        "currency": "PLN",
        "balance": 15675.42,
        "id": 4
    },
    {
        "date": "2025-01-29",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 18.00 USD 18.00 USD 1 USD=4.2655 PLN VENICE.AI SHERIDAN",
        "merchant": "DOP. MC 557519******1802",
        "amount": -76.78,
        "currency": "PLN",
        "balance": 15677.57,
        "id": 5
    },
    {
        "date": "2025-01-28",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 16.99 PLN ZABKA Z3074 K.1 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -16.99,
        "currency": "PLN",
        "balance": 15754.35,
        "id": 6
    },
    {
        "date": "2025-01-27",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 334.35 PLN LIDL KAPELANOW Warszawa",
        "merchant": "DOP. MC 557519******1802",
        "amount": -334.35,
        "currency": "PLN",
        "balance": 15771.34,
        "id": 7
    },
    {
        "date": "2025-01-27",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 99.97 PLN DECATHLON Warszawa Ost WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -99.97,
        "currency": "PLN",
        "balance": 16105.69,
        "id": 8
    },
    {
        "date": "2025-01-26",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 162.00 PLN Krutoy Lounge Warszawa",
        "merchant": "DOP. MC 557519******1802",
        "amount": -162.0,
        "currency": "PLN",
        "balance": 16205.66,
        "id": 9
    },
    {
        "date": "2025-01-26",
        "description": "Zakup BLIK PayU S.A.None Grunwaldzka 18660-166 Poznan ref:86082081517 PayU S.A.None Grunwaldzka 18660-166 Poznan",
        "merchant": "ZAKUP BLIK PAYU",
        "amount": -245.79,
        "currency": "PLN",
        "balance": 16367.66,
        "id": 10
    },
    {
        "date": "2025-01-25",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 22.00 PLN WM SP zoo HORECA SP K Ilow",
        "merchant": "DOP. MC 557519******1802",
        "amount": -22.0,
        "currency": "PLN",
        "balance": 16672.12,
        "id": 11
    },
    {
        "date": "2025-01-25",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 10.00 PLN Klub Stodola Warszawa",
        "merchant": "DOP. MC 557519******1802",
        "amount": -10.0,
        "currency": "PLN",
        "balance": 16694.12,
        "id": 12
    },
    {
        "date": "2025-01-25",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 43.96 PLN ZABKA ZA757 K.1 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -43.96,
        "currency": "PLN",
        "balance": 16613.45,
        "id": 13
    },
    {
        "date": "2025-01-25",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 14.71 PLN WARZYWA I OWOCE ANIA Warszawa",
        "merchant": "DOP. MC 557519******1802",
        "amount": -14.71,
        "currency": "PLN",
        "balance": 16657.41,
        "id": 14
    },
    {
        "date": "2025-01-24",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 16.90 PLN VINCENT NOWY SWIAT WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -16.9,
        "currency": "PLN",
        "balance": 16704.12,
        "id": 15
    },
    {
        "date": "2025-01-24",
        "description": "Zakup BLIK PayU S.A.None Grunwaldzka 18660-166 Poznan ref:86040463936 PayU S.A.None Grunwaldzka 18660-166 Poznan",
        "merchant": "ZAKUP BLIK PAYU",
        "amount": -89.19,
        "currency": "PLN",
        "balance": 16762.91,
        "id": 16
    },
    {
        "date": "2025-01-23",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 23.00 PLN ZABKA Z3074 K.1 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -23.0,
        "currency": "PLN",
        "balance": 16739.91,
        "id": 17
    },
    {
        "date": "2025-01-23",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 7.99 PLN ZABKA Z3074 K.1 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -7.99,
        "currency": "PLN",
        "balance": 16852.1,
        "id": 18
    },
    {
        "date": "2025-01-23",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 18.22 PLN ZABKA Z3074 K.1 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -18.22,
        "currency": "PLN",
        "balance": 16860.09,
        "id": 19
    },
    {
        "date": "2025-01-23",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 18.89 PLN CARREFOUR EXPRESS V55 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -18.89,
        "currency": "PLN",
        "balance": 16721.02,
        "id": 20
    }
]


def match_merchant_pattern(pattern: str, merchant: str, description: str) -> bool:
    """
    Match a merchant pattern against transaction merchant and description.
    Patterns can be:
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
    if "netflix" in desc_lower or "lounge" in desc_lower or "klub" in desc_lower or "club" in desc_lower:
        return "Entertainment"
    
    # Food & Groceries
    grocery_keywords = [
        "carrefour", "lidl", "zabka", "warzywa", "owoce", "groceries",
        "supermarket", "hipermarket", "wesola pani", "bistro", "restaurant",
        "food", "herbate", "cafe", "café", "goraco", "polecam", "horeca",
        "vincent"
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
    if "venice.ai" in desc_lower or "cursor" in desc_lower or "ai powered ide" in desc_lower:
        return "Other"
    
    # Fees and charges (Other)
    if "prowizja" in desc_lower or "fee" in desc_lower or "przewalutowanie" in desc_lower:
        return "Other"
    
    # Payment services (Other)
    if "paypro" in desc_lower or "blik" in desc_lower or "payu" in desc_lower:
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
