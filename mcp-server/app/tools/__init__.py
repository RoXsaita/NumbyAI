"""MCP tool implementations"""
from .save_statement_summary import save_statement_summary_handler
from .financial_data import get_financial_data_handler
from .mutate_categories import mutate_categories_handler
from .fetch_preferences import fetch_preferences_handler, fetch_categorization_preferences_handler
from .save_preferences import save_preferences_handler, save_categorization_preferences_handler
from .category_helpers import PREDEFINED_CATEGORIES

__all__ = [
    "save_statement_summary_handler",
    "get_financial_data_handler",
    "mutate_categories_handler",
    "fetch_preferences_handler",
    "save_preferences_handler",
    # Backward compatibility aliases
    "fetch_categorization_preferences_handler",
    "save_categorization_preferences_handler",
    "PREDEFINED_CATEGORIES",
]

