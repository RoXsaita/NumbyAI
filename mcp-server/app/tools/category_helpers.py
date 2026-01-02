"""
Category Helpers - Category Constants

This module contains category constants used throughout the application.

Used by:
- save_statement_summary.py - for category validation
- main.py - for category constants in tool descriptions
"""

# Predefined category options
# These 13 categories are used throughout the application for transaction categorization
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

CATEGORY_SYNONYMS = {
    "salary": "Income",
    "wages": "Income",
    "payroll": "Income",
    "rent": "Housing & Utilities",
    "utilities": "Housing & Utilities",
    "groceries": "Food & Groceries",
    "food": "Food & Groceries",
    "restaurant": "Food & Groceries",
    "restaurants": "Food & Groceries",
    "transport": "Transportation",
    "transit": "Transportation",
    "rideshare": "Transportation",
    "medical": "Healthcare",
    "health": "Healthcare",
    "insurance": "Insurance",
    "shopping": "Shopping",
    "entertainment": "Entertainment",
    "travel": "Travel",
    "debt": "Debt Payments",
    "loan": "Debt Payments",
    "credit card payment": "Debt Payments",
    "transfer": "Internal Transfers",
    "transfers": "Internal Transfers",
    "investing": "Investments",
    "investment": "Investments",
}


def normalize_category(category: str) -> str | None:
    """Normalize category strings to canonical names."""
    if not category or not isinstance(category, str):
        return None
    cleaned = category.strip()
    if not cleaned:
        return None
    for canonical in PREDEFINED_CATEGORIES:
        if cleaned.lower() == canonical.lower():
            return canonical
    synonym = CATEGORY_SYNONYMS.get(cleaned.lower())
    if synonym:
        return synonym
    return None


def is_valid_category(category: str) -> bool:
    """Return True if category is a known canonical category."""
    return normalize_category(category) is not None
