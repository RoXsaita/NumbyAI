"""
Tool Description Constants

This module contains the description strings for all MCP tools.
Keeping them separate improves readability of main.py and allows
easier maintenance of tool documentation.
"""

import textwrap

# Shared category list formatted for tool descriptions
CATEGORY_LIST = """
• Income - salary, wages, bonuses, refunds, gifts received
• Housing & Utilities - rent, mortgage, utilities, internet, phone
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

SAVE_STATEMENT_SUMMARY_DESCRIPTION = textwrap.dedent("""
    Save category summaries from a bank statement analysis.

    When a user uploads a bank statement and requests analysis (e.g., "analyze", "categorize", "process"), execute this workflow autonomously:

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !! MANDATORY STEP 1: ALWAYS call fetch_categorization_preferences FIRST   !!
    !! This is NON-NEGOTIABLE. Apply user preferences before manual categorizing!!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    WORKFLOW STEPS:
    0. Think through the full workflow before starting
    1. >>> fetch_categorization_preferences <<< (MANDATORY - DO THIS FIRST, NO EXCEPTIONS)
    2. Parse all transactions from the statement
    3. Apply matching preference rules to transactions FIRST
    4. Manually categorize remaining transactions using predefined categories
       (CRITICAL: Assign categories BEFORE any aggregation)
    5. BUILD INTERNAL TRANSACTION TABLE (MANDATORY before step 6):
       - One row per transaction with: id/index, date, description, merchant, amount, category
       - Each transaction must have EXACTLY ONE category (no duplicates across categories)
       - If uncertain, assign to 'Other' and explain in statement_insights
    6. Aggregate by category: totals = SUM(transaction amounts in category), counts, date ranges
       - Category totals MUST be computed STRICTLY as the sum of transactions in each category
       - Do NOT modify totals directly or adjust to satisfy reconciliation
    7. Calculate statement_net_flow = ending_balance - beginning_balance
    8. RECONCILIATION CHECK (2.5% tolerance):
       - If SUM(category totals) differs from statement_net_flow by > 2.5%:
         → Plug the difference into "Other" category
         → Explain discrepancy to user (do NOT fail the workflow)
    9. Save category summaries using this tool (auto-reconciles)
    10. Suggest new categorization preferences if patterns detected (save_categorization_preferences)
    11. After categorizing all transactions and saving the statement summary, analyze recurring merchants or patterns and call save_categorization_preferences (batch) for any new rules that would reduce repeated manual categorization. Save ONLY essential, high-confidence rules.
    12. Render dashboard (get_financial_data)
    13. Share the top 5 transactions in each category and ask if the user wants any recategorization

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !! STRICT PROHIBITIONS - The model MUST NOT:                              !!
    !! • Reallocate amounts to force reconciliation                           !!
    !! • Invent transactions that don't exist in the statement                !!
    !! • Omit transactions from the statement                                 !!
    !! • Assign the same transaction to multiple categories                   !!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    CATEGORIES (use exactly, do not create new ones):
    {categories}

    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    !! AUTO-RECONCILIATION: This tool validates that the sum of all category  !!
    !! amounts matches statement_net_flow within 5%. If mismatch exceeds 5%,  !!
    !! the save is REJECTED. Ensure your 2.5% plug to 'Other' keeps it valid. !!
    !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    RECURRING TRANSACTION DETECTION:
    After categorizing, analyze the transaction table for recurring patterns:
    1. Group transactions by merchant/payee name (normalize variations like "NETFLIX*", "NETFLIX.COM")
    2. Identify recurring charges: same merchant, similar amount (±5%), monthly/weekly interval
    3. For each detected recurring charge, include in statement_insights:
       - Merchant name
       - Amount per occurrence
       - Frequency (monthly, weekly, etc.)
       - Category assigned
       - Total for the period

    Common recurring charges to look for:
    • Streaming: Netflix, Spotify, Disney+, Apple Music, YouTube Premium
    • Software: Adobe, Microsoft 365, Dropbox, iCloud, Google One
    • Fitness: Gym memberships, fitness apps
    • Insurance: Auto, health, home (often monthly)
    • Subscriptions: News, magazines, newsletters
    • Utilities: Phone, internet, electricity (if consistent amount)

    SAFETY GUIDELINES FOR INSIGHTS:
    Keep insights high-level and avoid sensitive financial details that may trigger safety filters.

    INSIGHTS FORMAT (split between statement and category levels):

    ═══════════════════════════════════════════════════════════════════════════════
    STATEMENT-LEVEL INSIGHTS (pass to statement_insights parameter)
    ═══════════════════════════════════════════════════════════════════════════════

    ## At a Glance
    [Single concise paragraph: overall summary of the statement period,
    and most notable spending categories. Keep to 2-4 sentences Do not duplicate insights done at the category level.]

    ## Recurring Charges Detected
    List all recurring charges found with:
    - Merchant: [name] - $XX.XX/month (Category)

    ## Key Observations
    - Month-over-month changes if prior data exists
    - Unusual one-time transactions
    - Spending trends or recommendations

    ═══════════════════════════════════════════════════════════════════════════════
    CATEGORY-LEVEL INSIGHTS (pass to insights field in each category_summary)
    ═══════════════════════════════════════════════════════════════════════════════

    For each material category, include an insights field with:

    Top transactions (include top 3-5 by amount):
    - [Transaction description] - [Amount]
    - [Transaction description] - [Amount]
    - [Transaction description] - [Amount]

    [One sentence about patterns or notable activity in this category]

    CRITICAL REDACTION RULES FOR PRIVACY:
    You MUST redact the following from insights to protect user privacy:
    1. Full account numbers - show last 4 digits only (e.g., "Account ****1234")
    2. IBANs - show country code and last 4 digits (e.g., "GB82 ****7654")
    3. SWIFT/BIC codes - show first 4 and last 3 characters (e.g., "DEUT****500")
    4. Full addresses - keep street name only, remove unit/apartment numbers
    5. User's full name - replace with "User" or omit entirely
    6. Credit card numbers - NEVER include, even partially
    7. Email addresses - redact local part (e.g., "****@domain.com")
    8. Any sensitive identifiers (SSN, tax ID, passport numbers, etc.)

    WHAT TO KEEP (these are useful and safe):
    - Merchant names (Uber, Netflix, Amazon, etc.) - KEEP THESE
    - Generic transaction descriptions
    - Dates and amounts
    - Category names

    Example of proper redaction:
    ❌ BAD: "Transfer to John Smith account GB82 WEST 1234 5698 7654 32"
    ✅ GOOD: "Transfer to external account GB82 ****7654"

    ❌ BAD: "Netflix charged card ending 4532"
    ✅ GOOD: "Netflix subscription - $15.99"

    PARAMETERS:
    • category_summaries (required): Array of dicts with:
      - category: Must match predefined categories
      - amount: Float (negative for expenses)
      - currency: Code like USD/EUR/PLN
      - month_year: YYYY-MM format
      - transaction_count: Optional, defaults to 0
      - insights: Optional, category-level insights (top transactions, patterns)
    • bank_name (required): e.g., "Santander", "Revolut", "Chase"
    • statement_net_flow (required): ending_balance - beginning_balance (validates sum of categories)
    • coverage_from (required): Earliest transaction date (YYYY-MM-DD)
    • coverage_to (required): Latest transaction date (YYYY-MM-DD)
    • statement_insights (optional): Statement-level insights (At a Glance, Recurring, Observations)
    • confirmation_text (optional): Description of save action
    • user_id (optional): Defaults to test user

    Returns count of saved summaries and details, or RECONCILIATION ERROR if mismatch >5%.
""").strip().replace("{categories}", CATEGORY_LIST)

GET_FINANCIAL_DATA_DESCRIPTION = textwrap.dedent("""
    This tool allows you to retrieve the financial data of the user and show the widget dashboard. YOU HAVE ACCESS TO THE USER'S FINANCIAL DATA, YOU JUST NEED TO CALL THIS TOOL TO GET THE DATA AND answer user questions about their spending, income, and finances.

    ALWAYS call this tool when the user asks about:
    - Their spending patterns, expenses, or budget
    - Income or cash flow
    - Specific categories (Food, Transportation, etc.)
    - Specific time periods (months, years)
    - Financial trends or comparisons
    - Insights about their transactions
    - Asks you to show the dashboard

    Also call this automatically at the end of the statement processing workflow to render the dashboard.

    Parameters:
    • user_id (optional): User identifier (defaults to test user)
    • bank_name (optional): Filter by bank (e.g., "Santander", "Revolut")
    • month_year (optional): Filter by month in YYYY-MM format (e.g., "2025-07" for July)
    • categories (optional): Array of categories to include (e.g., ["Food & Groceries", "Transportation"])

    Returns filtered financial data including:
    • Category totals and breakdowns
    • Monthly totals
    • Metrics (inflows, outflows, net cash)
    • Statement insights (if available for the filtered period)
    • Raw data for the dashboard widget

    Example queries this tool answers:
    - "What did I spend in July?" → call with month_year="2025-07"
    - "Show my food expenses" → call with categories=["Food & Groceries"]
    - "What's my spending trend?" → call without filters for full data
""").strip()

FETCH_CATEGORIZATION_PREFERENCES_DESCRIPTION = textwrap.dedent("""
    Fetch all categorization preferences for transaction categorization.

    MUST be called FIRST when processing any bank statement. Returns user-defined rules
    for automatic transaction categorization.

    Parameters:
    • user_id (optional): User identifier (defaults to test user)

    Returns all enabled preferences sorted by:
    1. Bank-specific rules first
    2. Then by priority (higher first)

    Rule format example:
    {
        "name": "Uber rides",
        "bank_name": null,  // null = global
        "rule": {
            "conditions": {"merchant": "UBER*"},
            "category": "Transportation"
        },
        "priority": 0
    }
""").strip()

SAVE_CATEGORIZATION_PREFERENCES_DESCRIPTION = textwrap.dedent("""
    Batch save multiple categorization preference rules in a single call.

    Use this when you have multiple patterns to save - more efficient than individual calls.

    Parameters:
    • preferences (required): Array of preference objects, each containing:
      - name (required): Short rule name (e.g., "Uber rides")
      - rule (required): Structured rule with conditions and category:
        {
          "conditions": {"merchant": "UBER*"},
          "category": "Transportation"
        }
      - bank_name (optional): Bank name for bank-specific rule
      - priority (optional): Higher number = higher priority (default 0)
      - preference_id (optional): ID to update existing preference
    • user_id (optional): User identifier (defaults to test user)

    Example preferences array:
    [
      {"name": "Uber rides", "rule": {"conditions": {"merchant": "UBER*"}, "category": "Transportation"}},
      {"name": "Netflix", "rule": {"conditions": {"merchant": "NETFLIX*"}, "category": "Entertainment"}, "priority": 1}
    ]

    Returns summary with created/updated counts and results for each preference.
""").strip()

MUTATE_CATEGORIES_DESCRIPTION = textwrap.dedent("""
    Edit or transfer category amounts with automatic sign handling.

    Supports two operation types:
    1. EDIT - set a category's absolute total directly
    2. TRANSFER - move amounts between categories (ZERO-SUM, sign-aware)

    ═══════════════════════════════════════════════════════════════════════════════
    TRANSFER OPERATION - AUTOMATIC SIGN HANDLING (RECOMMENDED FOR RECLASSIFICATION)
    ═══════════════════════════════════════════════════════════════════════════════

    Use transfer for recategorizing transactions. The sign math is handled automatically:

    • transfer_amount: ALWAYS A POSITIVE NUMBER (the dollar amount being moved)
    • Sign is determined automatically based on the SOURCE category's current sign

    SIGN RULES (automatic):
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ If source is EXPENSE (negative, e.g., -500):                                │
    │   → Source becomes LESS negative: -500 + 100 = -400                         │
    │   → Destination becomes MORE negative: -200 - 100 = -300                    │
    │   → Net change: 0 ✓                                                         │
    │                                                                             │
    │ If source is INCOME (positive, e.g., +1000):                                │
    │   → Source becomes LESS positive: +1000 - 100 = +900                        │
    │   → Destination becomes MORE positive: +200 + 100 = +300                    │
    │   → Net change: 0 ✓                                                         │
    └─────────────────────────────────────────────────────────────────────────────┘

    Transfer Example:
    {"type": "transfer", "from_category": "Food & Groceries", "to_category": "Travel", "transfer_amount": 100}
      → Food & Groceries: -500 → -400 (expense reduced by 100)
      → Travel: -200 → -300 (expense increased by 100)
      → Net change: 0 (statement reconciliation preserved)

    ═══════════════════════════════════════════════════════════════════════════════
    EDIT OPERATION - DIRECT AMOUNT SETTING
    ═══════════════════════════════════════════════════════════════════════════════

    Use edit to set absolute final amounts. You must handle sign math yourself:
    {"type": "edit", "category": "Food & Groceries", "new_amount": -400.0}

    ⚠️ WARNING: Edits can break statement reconciliation. Use transfer when possible.

    ═══════════════════════════════════════════════════════════════════════════════

    Parameters:
    • operations (required): Array of operation objects:
      
      For TRANSFER (preferred for recategorization):
        - type: "transfer"
        - from_category: Source category name
        - to_category: Destination category name  
        - transfer_amount: Positive number (magnitude to move)
        - note: Optional description
      
      For EDIT (direct amount setting):
        - type: "edit"
        - category: Category name
        - new_amount: Signed amount (negative for expenses, positive for income)
        - note: Optional description

    • user_id (optional): User identifier (defaults to test user)
    • bank_name (optional): Filter by specific bank name
    • month_year (optional): Filter by specific month in YYYY-MM format

    Returns:
    • Updated DashboardProps snapshot with new category totals
    • change_summary: Array of operation results with detailed status messages

    After invoking this tool, immediately call get_financial_data to show the updated dashboard.
""").strip()
