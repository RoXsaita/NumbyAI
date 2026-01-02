"""
Tool Description Constants

Following OpenAI guidance: concise \"Use this when...\" descriptions with explicit parameters.
"""

from app.prompts import load_prompt, render_prompt

# ============================================================================
# FETCH_PREFERENCES - The Gateway Tool (call FIRST, always)
# ============================================================================
FETCH_PREFERENCES_DESCRIPTION = load_prompt("tool_descriptions/fetch_preferences.md").strip()

# ============================================================================
# SAVE_PREFERENCES - Persist user data
# ============================================================================
SAVE_PREFERENCES_DESCRIPTION = load_prompt("tool_descriptions/save_preferences.md").strip()

# ============================================================================
# GET_FINANCIAL_DATA - Dashboard/read tool
# ============================================================================
GET_FINANCIAL_DATA_DESCRIPTION = load_prompt("tool_descriptions/get_financial_data.md").strip()

# ============================================================================
# SAVE_STATEMENT_SUMMARY - Single month
# ============================================================================
CATEGORY_LIST = load_prompt("tool_descriptions/category_list.md").strip()
CATEGORY_RULES = load_prompt("tool_descriptions/category_rules.txt").strip()
PRIVACY_RULES = load_prompt("tool_descriptions/privacy_rules.txt").strip()
SAVE_STATEMENT_SUMMARY_DESCRIPTION = render_prompt(
    load_prompt("tool_descriptions/save_statement_summary.md").strip(),
    categories=CATEGORY_LIST,
    category_rules=CATEGORY_RULES,
    privacy=PRIVACY_RULES,
)

# ============================================================================
# MUTATE_CATEGORIES - Post-save adjustments
# ============================================================================
MUTATE_CATEGORIES_DESCRIPTION = load_prompt("tool_descriptions/mutate_categories.md").strip()

# ============================================================================
# SAVE_BUDGET - Budget targets
# ============================================================================
SAVE_BUDGET_DESCRIPTION = load_prompt("tool_descriptions/save_budget.md").strip()

# Backward compatibility
FETCH_CATEGORIZATION_PREFERENCES_DESCRIPTION = FETCH_PREFERENCES_DESCRIPTION
SAVE_CATEGORIZATION_PREFERENCES_DESCRIPTION = SAVE_PREFERENCES_DESCRIPTION
