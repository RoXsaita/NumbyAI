"""
Tool Description Constants

This module contains the description strings for all MCP tools.
Keeping them separate improves readability of main.py and allows
easier maintenance of tool documentation.
"""

import textwrap

# Shared category list formatted for tool descriptions
CATEGORY_LIST = """
• Income - salary, wages, bonuses, gifts received
• Housing & Utilities - rent, utilities, internet, phone
• Food & Groceries - groceries, restaurants, coffee, food delivery
• Transportation - gas, transit, car payment, parking, rideshare
• Insurance - health, car, home, life insurance premiums
• Healthcare - medical bills, prescriptions, dental, vision
• Shopping - retail, clothing, electronics, household items
• Entertainment - movies, subscriptions, hobbies, gym
• Travel - flights, hotels, vacation expenses
• Debt Payments - credit card payments, loans (excluding auto/mortgage)
• Internal Transfers - bank-to-bank transfers, internal movements
• Investments - stock purchases, retirement contributions, dividends
• Other - anything that doesn't fit above (ALSO: reconciliation plug if needed)
""".strip()

# System-level instructions - the model sees this in the tool list as guiding context
SYSTEM_INSTRUCTIONS_DESCRIPTION = textwrap.dedent("""
    # Role
    Finance Budgeting Assistant. Ingest bank statements, categorize transactions, persist summaries, render dashboards.

    # Trigger
    User uploads a statement OR requests analysis/categorization → execute full workflow autonomously. No confirmation needed.

    # Workflow
    1. `fetch_categorization_preferences` — load saved rules, apply to matching transactions first
    2. Parse statement — extract every transaction (date, description, merchant, amount) into internal table
    3. Categorize — assign each transaction to exactly ONE predefined category; uncertain → "Other"
    4. Reconcile — if ∑categories ≠ statement_net_flow by >2.5%, plug delta to "Other"
    5. `save_statement_summary` — persists data; rejects if totals mismatch >5%
    6. `get_financial_data` — render dashboard with fresh data

    # Integrity (non-negotiable)
    - One transaction → one category (no duplicates)
    - Category total = sum(transactions in category), never manually adjusted
    - Never invent, drop, or reallocate transactions

    # Gatekeeper
    `save_statement_summary` validates everything. Rejection → fix transaction table, retry. No save → no dashboard.
""").strip()

SAVE_STATEMENT_SUMMARY_DESCRIPTION = textwrap.dedent("""
    Use this tool to persist the reconciled results of a full bank-statement analysis. Call it exactly once per uploaded statement after the user has explicitly asked you to analyze/categorize/process the data. If the request is hypothetical, the statement is missing, or balances/dates are unclear, ask for clarification or the original file instead of calling the tool.

    Before calling:
    1. fetch_categorization_preferences and apply every matching rule up front.
    2. Reverse-engineer the statement format, extract every transaction, and build an internal table (id/index, date, description, merchant, signed amount, single category). Do not invent, duplicate, or drop rows; put uncertain entries in “Other” and explain the reason later.
    3. Categorize transactions granularly using only the categories listed below, then aggregate totals/counts per category. Never lump entire inflow/outflow buckets or assign a transaction to multiple categories.
    4. Compute coverage_from/coverage_to (YYYY-MM-DD), month_year (YYYY-MM), and statement_net_flow = ending_balance − beginning_balance from the statement itself. If metadata conflicts with user recollection, prefer the document values and note the discrepancy in statement_insights.
    5. Reconcile totals: if ∑category amounts differs from statement_net_flow by more than 2.5%, move the delta into “Other”, describe the plug, and confirm the adjusted totals fall within this tool’s ±5% auto-validation. If a rejection still occurs, fix the transaction table before retrying.
    6. Capture material patterns (top merchants, recurring spend, unusual spikes) so statement_insights can be delivered as concise bullet items referencing category names, payer/payee, dates, and why any adjustments were needed.

    Required arguments:
    • category_summaries – array of objects with {category (from list), amount (negative expenses), currency ISO code (e.g., USD), month_year YYYY-MM, transaction_count (0 allowed), insights (category-level patterns/merchants)}. Omit the call if any required field is unknown.
    • bank_name – canonical bank label from the statement header.
    • statement_net_flow – ending minus beginning balance after reconciliation.
    • coverage_from / coverage_to – earliest and latest transaction dates in YYYY-MM-DD.

    Optional arguments:
    • statement_insights – bullet-format narrative focused on the most material categories, notable merchants/dates, recurring behaviors, discrepancies, and reconciliation plugs.
    • confirmation_text – short status message to show the user.

    After a successful save, decide whether new save_categorization_preferences rules are warranted and refresh the dashboard via get_financial_data so the user immediately sees the updated data.

    Categories (use exactly, no additions or renames):
    {categories}
""").strip().replace("{categories}", CATEGORY_LIST)

GET_FINANCIAL_DATA_DESCRIPTION = textwrap.dedent("""
    Retrieve financial data and render the dashboard. Call for any spending/income/budget query or after statement processing.

    Parameters (all optional):
    • bank_name – filter by bank
    • month_year – filter by YYYY-MM
    • categories – array of category names

    Returns category totals, monthly totals, metrics, and insights.
""").strip()

FETCH_CATEGORIZATION_PREFERENCES_DESCRIPTION = textwrap.dedent("""
    Fetch saved categorization rules. Call FIRST before processing any statement. Apply matching rules before manual categorization.
""").strip()

SAVE_CATEGORIZATION_PREFERENCES_DESCRIPTION = textwrap.dedent("""
    Save categorization rules for AMBIGUOUS or USER-REQUESTED patterns only. Skip obvious mappings (Uber→Transportation, Netflix→Entertainment).

    Parameters:
    • preferences – array of {name, rule: {conditions: {merchant}, category}, bank_name (optional)}
""").strip()

MUTATE_CATEGORIES_DESCRIPTION = textwrap.dedent("""
    Edit or transfer category amounts.

    Operations:
    • TRANSFER (preferred) – zero-sum move between categories; sign handled automatically. Use positive transfer_amount.
    • EDIT – set category total directly (signed). Can break reconciliation; avoid if possible.

    Parameters:
    • operations – array of:
      - transfer: {type, from_category, to_category, transfer_amount, note?}
      - edit: {type, category, new_amount, note?}
    • bank_name, month_year (optional filters)

    Returns updated dashboard snapshot. Call get_financial_data after to render.
""").strip()

SAVE_BUDGET_DESCRIPTION = textwrap.dedent("""
    Save or update budget targets per category.

    Parameters:
    • budgets – array of {category, amount (positive), month_year? (YYYY-MM), currency? (default USD)}

    Omit month_year for a default budget. Returns created/updated counts.
""").strip()
