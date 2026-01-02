#!/usr/bin/env python3
"""Categorize bank transactions into predefined categories"""

import json
import re
from typing import List, Dict, Any, Optional
from app.database import SessionLocal, CategorizationPreference, CategorizationRule, resolve_user_id
from app.tools.category_helpers import PREDEFINED_CATEGORIES

# Transaction data from user
transactions = [
    {
        "date": "2025-01-05",
        "description": "Zakup BLIK PayPro S.A. ul. Pastelowa 8 ref:85674178538 PayPro S.A. ul. Pastelowa 8",
        "merchant": "ZAKUP BLIK PAYPRO",
        "amount": -14900.0,
        "currency": "PLN",
        "balance": 2028614.0,
        "id": 61
    },
    {
        "date": "2025-01-05",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 50.92 PLN BOLT.EU/O/2501051609 Warsaw",
        "merchant": "DOP. MC 557519******1802",
        "amount": -5092.0,
        "currency": "PLN",
        "balance": 1896079.0,
        "id": 62
    },
    {
        "date": "2025-01-05",
        "description": "Prowizja za przewalutowanie transakcji dot.karty 557519******1802",
        "merchant": "PROWIZJA ZA PRZEWALUTOWANIE",
        "amount": -48.0,
        "currency": "PLN",
        "balance": 2043514.0,
        "id": 63
    },
    {
        "date": "2025-01-05",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 3.99 USD 3.99 USD 1 USD=4.2655 PLN NETFLIX.COM 408-724-9160",
        "merchant": "Netflix",
        "amount": -1702.0,
        "currency": "PLN",
        "balance": 2043562.0,
        "id": 64
    },
    {
        "date": "2025-01-05",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 67.00 PLN Netflix.com Los Gatos",
        "merchant": "Netflix",
        "amount": -6700.0,
        "currency": "PLN",
        "balance": 2047421.0,
        "id": 65
    },
    {
        "date": "2025-01-05",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 20.00 USD 20.00 USD 1 USD=4.2655 PLN CURSOR, AI POWERED IDE NEW YORK",
        "merchant": "DOP. MC 557519******1802",
        "amount": -8531.0,
        "currency": "PLN",
        "balance": 1901410.0,
        "id": 66
    },
    {
        "date": "2025-01-04",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 177.47 JOD 244.20 EUR 1 EUR=4.4281 PLN Odyssey Bistro Abdoun Abdoun Alsham",
        "merchant": "DOP. MC 557519******1802",
        "amount": -108134.0,
        "currency": "PLN",
        "balance": 1920480.0,
        "id": 67
    },
    {
        "date": "2025-01-04",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 21.57 PLN WESOLA PANI WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -2157.0,
        "currency": "PLN",
        "balance": 2045264.0,
        "id": 68
    },
    {
        "date": "2025-01-04",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 73.51 PLN CARREFOUR HIPERMARKET WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -7351.0,
        "currency": "PLN",
        "balance": 2054121.0,
        "id": 69
    },
    {
        "date": "2025-01-04",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 139.97 PLN TK Maxx Warsaw Promen",
        "merchant": "DOP. MC 557519******1802",
        "amount": -13997.0,
        "currency": "PLN",
        "balance": 2061472.0,
        "id": 70
    },
    {
        "date": "2025-01-04",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 35.30 PLN CZAS NA HERBATE WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -3530.0,
        "currency": "PLN",
        "balance": 2075469.0,
        "id": 71
    },
    {
        "date": "2025-01-04",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 197.83 PLN JMIDF SP.Z.O.O.HEBE R5 WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -19783.0,
        "currency": "PLN",
        "balance": 2078999.0,
        "id": 72
    },
    {
        "date": "2025-01-04",
        "description": "Prowizja za przewalutowanie transakcji dot.karty 557519******1802",
        "merchant": "PROWIZJA ZA PRZEWALUTOWANIE",
        "amount": -1254.0,
        "currency": "PLN",
        "balance": 2098782.0,
        "id": 73
    },
    {
        "date": "2025-01-04",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 105.03 USD 105.03 USD 1 USD=4.2655 PLN an.Nord*Products Amsterdam",
        "merchant": "DOP. MC 557519******1802",
        "amount": -44801.0,
        "currency": "PLN",
        "balance": 2100036.0,
        "id": 74
    },
    {
        "date": "2025-01-03",
        "description": "Zakup BLIK PayPro S.A. ul. Pastelowa 8 ref:85621031823 PayPro S.A. ul. Pastelowa 8",
        "merchant": "ZAKUP BLIK PAYPRO",
        "amount": -7000.0,
        "currency": "PLN",
        "balance": 2028614.0,
        "id": 75
    },
    {
        "date": "2025-01-03",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 11.95 JOD 16.50 EUR 1 EUR=4.4281 PLN Careem Food Jordan",
        "merchant": "DOP. MC 557519******1802",
        "amount": -7306.0,
        "currency": "PLN",
        "balance": 1910146.0,
        "id": 76
    },
    {
        "date": "2025-01-02",
        "description": "Pobranie opłaty za pakiet ubezp. Kredyt: 157234005 Pakiet: 176481 ROZLICZ.UBEZP PPP-HIPOTEKA",
        "merchant": "POBRANIE OPŁATY ZA",
        "amount": -20157.0,
        "currency": "PLN",
        "balance": 2162849.0,
        "id": 77
    },
    {
        "date": "2025-01-02",
        "description": "SPŁATA KREDYTU",
        "merchant": "SPŁATA KREDYTU",
        "amount": -343068.0,
        "currency": "PLN",
        "balance": 2183006.0,
        "id": 78
    },
    {
        "date": "2025-01-02",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 43.52 PLN WESOLA PANI WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -4352.0,
        "currency": "PLN",
        "balance": 2156877.0,
        "id": 79
    },
    {
        "date": "2025-01-02",
        "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 16.20 PLN CARREFOUR HIPERMARKET WARSZAWA",
        "merchant": "DOP. MC 557519******1802",
        "amount": -1620.0,
        "currency": "PLN",
        "balance": 2161229.0,
        "id": 80
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
    
    # Income - check for salary/wages (even if amount is negative, description indicates income)
    if "wynagrodzenie" in desc_lower or "salary" in desc_lower or "wage" in desc_lower:
        return "Income"
    
    # Debt Payments
    if "spłata kredytu" in desc_lower or "loan payment" in desc_lower or "debt" in desc_lower:
        return "Debt Payments"
    
    # Insurance
    if "ubezp" in desc_lower or "insurance" in desc_lower:
        return "Insurance"
    
    # Transportation
    if "bolt" in desc_lower or "uber" in desc_lower or "taxi" in desc_lower or "careem" in desc_lower:
        return "Transportation"
    
    # Entertainment
    if "netflix" in desc_lower:
        return "Entertainment"
    
    # Food & Groceries
    grocery_keywords = [
        "carrefour", "lidl", "zabka", "warzywa", "owoce", "groceries",
        "supermarket", "hipermarket", "wesola pani", "bistro", "restaurant",
        "food", "herbate", "cafe", "café"
    ]
    if any(kw in desc_lower for kw in grocery_keywords):
        return "Food & Groceries"
    
    # Shopping
    shopping_keywords = ["tk maxx", "hebe", "shopping", "store", "retail"]
    if any(kw in desc_lower for kw in shopping_keywords):
        return "Shopping"
    
    # Travel
    if "odyssey" in desc_lower or "travel" in desc_lower or "hotel" in desc_lower:
        return "Travel"
    
    # Software/Subscriptions (Other)
    if "cursor" in desc_lower or "ai powered ide" in desc_lower:
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
