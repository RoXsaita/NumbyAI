#!/usr/bin/env python3
"""Simple categorization script"""

import json

# Predefined categories
PREDEFINED_CATEGORIES = [
    "Income",
    "Housing & Utilities",
    "Food & Groceries",
    "Transportation",
    "Insurance",
    "Healthcare",
    "Shopping",
    "Entertainment",
    "Travel",
    "Debt Payments",
    "Internal Transfers",
    "Investments",
    "Other",
]

transactions = [
    {"date": "2025-01-05", "description": "Zakup BLIK PayPro S.A. ul. Pastelowa 8 ref:85674178538 PayPro S.A. ul. Pastelowa 8", "merchant": "ZAKUP BLIK PAYPRO", "amount": -14900.0, "currency": "PLN", "balance": 2028614.0, "id": 61},
    {"date": "2025-01-05", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 50.92 PLN BOLT.EU/O/2501051609 Warsaw", "merchant": "DOP. MC 557519******1802", "amount": -5092.0, "currency": "PLN", "balance": 1896079.0, "id": 62},
    {"date": "2025-01-05", "description": "Prowizja za przewalutowanie transakcji dot.karty 557519******1802", "merchant": "PROWIZJA ZA PRZEWALUTOWANIE", "amount": -48.0, "currency": "PLN", "balance": 2043514.0, "id": 63},
    {"date": "2025-01-05", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 3.99 USD 3.99 USD 1 USD=4.2655 PLN NETFLIX.COM 408-724-9160", "merchant": "Netflix", "amount": -1702.0, "currency": "PLN", "balance": 2043562.0, "id": 64},
    {"date": "2025-01-05", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 67.00 PLN Netflix.com Los Gatos", "merchant": "Netflix", "amount": -6700.0, "currency": "PLN", "balance": 2047421.0, "id": 65},
    {"date": "2025-01-05", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 20.00 USD 20.00 USD 1 USD=4.2655 PLN CURSOR, AI POWERED IDE NEW YORK", "merchant": "DOP. MC 557519******1802", "amount": -8531.0, "currency": "PLN", "balance": 1901410.0, "id": 66},
    {"date": "2025-01-04", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 177.47 JOD 244.20 EUR 1 EUR=4.4281 PLN Odyssey Bistro Abdoun Abdoun Alsham", "merchant": "DOP. MC 557519******1802", "amount": -108134.0, "currency": "PLN", "balance": 1920480.0, "id": 67},
    {"date": "2025-01-04", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 21.57 PLN WESOLA PANI WARSZAWA", "merchant": "DOP. MC 557519******1802", "amount": -2157.0, "currency": "PLN", "balance": 2045264.0, "id": 68},
    {"date": "2025-01-04", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 73.51 PLN CARREFOUR HIPERMARKET WARSZAWA", "merchant": "DOP. MC 557519******1802", "amount": -7351.0, "currency": "PLN", "balance": 2054121.0, "id": 69},
    {"date": "2025-01-04", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 139.97 PLN TK Maxx Warsaw Promen", "merchant": "DOP. MC 557519******1802", "amount": -13997.0, "currency": "PLN", "balance": 2061472.0, "id": 70},
    {"date": "2025-01-04", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 35.30 PLN CZAS NA HERBATE WARSZAWA", "merchant": "DOP. MC 557519******1802", "amount": -3530.0, "currency": "PLN", "balance": 2075469.0, "id": 71},
    {"date": "2025-01-04", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 197.83 PLN JMIDF SP.Z.O.O.HEBE R5 WARSZAWA", "merchant": "DOP. MC 557519******1802", "amount": -19783.0, "currency": "PLN", "balance": 2078999.0, "id": 72},
    {"date": "2025-01-04", "description": "Prowizja za przewalutowanie transakcji dot.karty 557519******1802", "merchant": "PROWIZJA ZA PRZEWALUTOWANIE", "amount": -1254.0, "currency": "PLN", "balance": 2098782.0, "id": 73},
    {"date": "2025-01-04", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 105.03 USD 105.03 USD 1 USD=4.2655 PLN an.Nord*Products Amsterdam", "merchant": "DOP. MC 557519******1802", "amount": -44801.0, "currency": "PLN", "balance": 2100036.0, "id": 74},
    {"date": "2025-01-03", "description": "Zakup BLIK PayPro S.A. ul. Pastelowa 8 ref:85621031823 PayPro S.A. ul. Pastelowa 8", "merchant": "ZAKUP BLIK PAYPRO", "amount": -7000.0, "currency": "PLN", "balance": 2028614.0, "id": 75},
    {"date": "2025-01-03", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 11.95 JOD 16.50 EUR 1 EUR=4.4281 PLN Careem Food Jordan", "merchant": "DOP. MC 557519******1802", "amount": -7306.0, "currency": "PLN", "balance": 1910146.0, "id": 76},
    {"date": "2025-01-02", "description": "Pobranie opłaty za pakiet ubezp. Kredyt: 157234005 Pakiet: 176481 ROZLICZ.UBEZP PPP-HIPOTEKA", "merchant": "POBRANIE OPŁATY ZA", "amount": -20157.0, "currency": "PLN", "balance": 2162849.0, "id": 77},
    {"date": "2025-01-02", "description": "SPŁATA KREDYTU", "merchant": "SPŁATA KREDYTU", "amount": -343068.0, "currency": "PLN", "balance": 2183006.0, "id": 78},
    {"date": "2025-01-02", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 43.52 PLN WESOLA PANI WARSZAWA", "merchant": "DOP. MC 557519******1802", "amount": -4352.0, "currency": "PLN", "balance": 2156877.0, "id": 79},
    {"date": "2025-01-02", "description": "DOP. MC 557519******1802 PŁATNOŚĆ KARTĄ 16.20 PLN CARREFOUR HIPERMARKET WARSZAWA", "merchant": "DOP. MC 557519******1802", "amount": -1620.0, "currency": "PLN", "balance": 2161229.0, "id": 80}
]

def categorize(tx):
    desc = tx["description"].lower()
    merchant = tx.get("merchant", "").lower()
    
    # Debt Payments
    if "spłata kredytu" in desc:
        return "Debt Payments"
    
    # Insurance
    if "ubezp" in desc or "insurance" in desc:
        return "Insurance"
    
    # Transportation
    if "bolt" in desc or "careem" in desc:
        return "Transportation"
    
    # Entertainment
    if "netflix" in desc:
        return "Entertainment"
    
    # Food & Groceries
    if any(kw in desc for kw in ["carrefour", "wesola pani", "bistro", "herbate", "careem food"]):
        return "Food & Groceries"
    
    # Shopping
    if "tk maxx" in desc or "hebe" in desc:
        return "Shopping"
    
    # Travel
    if "odyssey" in desc:
        return "Travel"
    
    # Software/Subscriptions
    if "cursor" in desc or "ai powered ide" in desc:
        return "Other"
    
    # Fees
    if "prowizja" in desc or "przewalutowanie" in desc:
        return "Other"
    
    # Payment services
    if "paypro" in desc or "blik" in desc:
        return "Other"
    
    # Unknown products/services
    if "nord" in desc or "products" in desc:
        return "Shopping"
    
    return "Other"

results = [{"id": tx["id"], "category": categorize(tx)} for tx in transactions]
print(json.dumps(results, indent=2))
