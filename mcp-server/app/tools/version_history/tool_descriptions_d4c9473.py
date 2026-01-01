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

SAVE_STATEMENT_SUMMARY_DESCRIPTION = textwrap.dedent("""
    Save category summaries from a bank statement analysis.

    When a user uploads a bank statement and requests analysis (e.g., "analyze", "categorize", "process"), execute this workflow autonomously:

    MANDATORY STEP 1: ALWAYS call fetch_categorization_preferences FIRST
    This is NON-NEGOTIABLE. Apply user preferences before manual categorizing.

    WORKFLOW STEPS:
    0. Think through the full workflow before starting
    1. fetch_categorization_preferences (MANDATORY - DO THIS FIRST, NO EXCEPTIONS)
    2. Reverse-engineer the statement, understand the structure, and parse all transactions from the statement
    3. BUILD INTERNAL TRANSACTION TABLE (MANDATORY before step 6):
       - One row per transaction with: id/index, date, description, merchant, amount, category
       - Each transaction must have EXACTLY ONE category (no duplicates across categories)
       - If uncertain, assign to 'Other' and explain in statement_insights    
    4. Apply matching preference rules to transactions FIRST
    5. Manually categorize remaining transactions using predefined categories
       (CRITICAL: Assign categories BEFORE any aggregation)
       IMPORTANT: Always categorize each transaction to its proper specific category based on merchant/description.
       Never lazily group massive totals (e.g., all inflows as Income, all outflows as Other). Categorize granularly.
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

    STRICT PROHIBITIONS - The model MUST NOT:
    • Reallocate amounts to force reconciliation
    • Invent transactions that don't exist in the statement
    • Omit transactions from the statement
    • Assign the same transaction to multiple categories

    CATEGORIES (use exactly, do not create new ones):
    {categories}

    AUTO-RECONCILIATION: This tool validates that the sum of all category amounts matches statement_net_flow within 5%.
    If mismatch exceeds 5%, the save is REJECTED. Ensure your 2.5% plug to 'Other' keeps it valid.

    STATEMENT INSIGHTS:
    Provide bullet-point insights instead of a narrative. Focus on the most material categories (those with the highest absolute totals) and highlight the largest transactions within those categories. Each bullet point should mention:
    - The category name.
    - The largest material transactions by amount, including payer/payee and date.
    - Any notable recurring patterns or unusual activity in that category.
    - Unusual material transactions

    SAFETY GUIDELINES FOR INSIGHTS:
    Keep insights high-level and avoid sensitive financial details that may trigger safety filters.

    PARAMETERS:
    • category_summaries (required): Array of dicts with:
      - category: Must match predefined categories
      - amount: Float (negative for expenses)
      - currency: Code like USD/EUR/PLN
      - month_year: YYYY-MM format
      - transaction_count: Optional, defaults to 0
    • bank_name (required): e.g., "Santander", "Revolut", "Chase"
    • statement_net_flow (required): ending_balance - beginning_balance (validates sum of categories)
    • coverage_from (required): Earliest transaction date (YYYY-MM-DD)
    • coverage_to (required): Latest transaction date (YYYY-MM-DD)
    • statement_insights (optional): Factual transaction narrative
    • confirmation_text (optional): Description of save action

    Returns count of saved summaries and details, or RECONCILIATION ERROR if mismatch >5%.
""").strip().replace("{categories}", CATEGORY_LIST)

GET_FINANCIAL_DATA_DESCRIPTION = textwrap.dedent("""
    # Role and Objective
This tool enables retrieval of the user's financial data and displays the widget dashboard. It is designed to support answering user questions related to spending, income, budgets, and financial insights by leveraging direct access to user financial information.

# Instructions
- Always call this tool when the user requests information regarding:
  - Spending patterns, expenses, or budgets
  - Income or cash flow
  - Specific categories (e.g., Food, Transportation)
  - Specific time periods (e.g., months, years)
  - Financial trends or comparisons
  - Transaction insights
  - Dashboard display
- Additionally, invoke this tool automatically at the end of the statement processing workflow to render the dashboard.

# Parameters
- `bank_name` (optional): Restrict to a specific bank (e.g., "Santander", "Revolut").
- `month_year` (optional): Filter by month in YYYY-MM format (e.g., "2025-07").
- `categories` (optional): Array of categories to filter (e.g., ["Food & Groceries"]).

# Returns
Filtered financial data, including:
- Category totals and breakdowns
- Monthly totals
- Key metrics (inflows, outflows, net cash)
- Statement insights (when available for the filtered period)
- Raw data for the dashboard widget

# Example Queries and Expected Tool Calls
- “What did I spend in July?” → call with `month_year="2025-07"`
- “Show my food expenses” → call with `categories=["Food & Groceries"]`
- “What’s my spending trend?” → call without filters for complete data

# Output Verbosity
- Respond in at most 2 short paragraphs or, if providing a bulleted list, use no more than 6 bullets, each limited to one concise line.
- Prioritize complete, actionable answers within the length cap. Do not increase length to restate politeness.
""").strip()

FETCH_CATEGORIZATION_PREFERENCES_DESCRIPTION = textwrap.dedent("""
Fetch saved categorization rules. MUST call FIRST before processing any bank statement.

Returns array of rules: `{"name": "...", "bank_name": null, "rule": {"conditions": {"merchant": "..."}, "category": "..."}}`

Apply matching rules before manual categorization. Empty array = no saved rules.
""").strip()

SAVE_CATEGORIZATION_PREFERENCES_DESCRIPTION = textwrap.dedent("""
Save categorization rules for AMBIGUOUS or USER-REQUESTED patterns only.

## When to call
- User explicitly requests a categorization rule
- Merchant name is ambiguous (e.g., "ACME LLC" could be multiple categories)
- Recurring pattern that defies standard category logic

## When NOT to call
- Obvious categorizations (Uber→Transportation, Netflix→Entertainment, Walmart→Shopping)
- Standard merchant-to-category mappings any model would infer
- One-off transactions

## Parameters
- **preferences**: Array of `{name, rule: {conditions: {merchant: "..."}, category: "..."}, bank_name (optional)}`

Returns `{created_count, updated_count}`.
""").strip()

MUTATE_CATEGORIES_DESCRIPTION = textwrap.dedent("""
# Edit or Transfer Category Amounts (Automatic Sign Handling)

This module supports two operation types:

1. **EDIT** – Set a category's absolute total directly.
2. **TRANSFER** – Move amounts between categories (**zero-sum, sign-aware**).

---
## Checklist (Before proceeding):
- Determine operation type (EDIT or TRANSFER) for each action.
- Validate and format all amounts and category names.
- Apply sign-handling rules according to the operation.
- Record operation in the change summary.
- Invoke dashboard update and confirm status.

---
## TRANSFER OPERATION – Automatic Sign Handling *(Recommended for Transaction Reclassification)*

Use **transfer** to recategorize transactions. All sign math is handled automatically:

- **transfer_amount:** *Always a positive number* (the dollar amount being moved).
- The sign is determined automatically based on the **source** category's current sign.

**Automatic Sign Rules:**
```
If source is EXPENSE (negative, e.g., -500):
    → Source becomes LESS negative:    -500 + 100 = -400
    → Destination becomes MORE negative: -200 - 100 = -300
    → Net change: 0 ✓

If source is INCOME (positive, e.g., +1000):
    → Source becomes LESS positive:    +1000 - 100 = +900
    → Destination becomes MORE positive: +200 + 100 = +300
    → Net change: 0 ✓
```

**Transfer Example:**
```json
{"type": "transfer", "from_category": "Food & Groceries", "to_category": "Travel", "transfer_amount": 100}
```
- Food & Groceries: -500 → -400 (expense reduced by 100)
- Travel: -200 → -300 (expense increased by 100)
- Net change: 0 (statement reconciliation preserved)

---
## EDIT OPERATION – Direct Amount Setting

Use **edit** to set category totals directly. *You must handle sign math yourself*:
```json
{"type": "edit", "category": "Food & Groceries", "new_amount": -400.0}
```
⚠️ WARNING: Edits can break statement reconciliation. Use transfer whenever possible.

---
## Parameters
- **operations** *(required)*: Array of operation objects:
  - For **TRANSFER** (preferred for recategorization):
    - `type`: "transfer"
    - `from_category`: Source category name
    - `to_category`: Destination category name
    - `transfer_amount`: Positive number (magnitude to move)
    - `note`: *(Optional)* Description
  - For **EDIT** (direct amount setting):
    - `type`: "edit"
    - `category`: Category name
    - `new_amount`: Signed amount (negative for expenses, positive for income)
    - `note`: *(Optional)* Description
- **bank_name** *(optional)*: Filter by specific bank
- **month_year** *(optional)*: Filter by month (YYYY-MM)

## Returns
- Updated `DashboardProps` snapshot with new category totals
- `change_summary`: Array of operation results with detailed status messages

After invoking this tool, immediately call `get_financial_data` to show the updated dashboard. After calling, validate the returned dashboard snapshot for correctness and state next steps or remediations if needed.
""").strip()

SAVE_BUDGET_DESCRIPTION = textwrap.dedent("""
# Role and Objective
Save or update budget targets for spending categories. This tool enables users to set financial goals for their expenses.

# Instructions
Use this tool when the user wants to:
- Set a budget for a category (e.g., "Set my food budget to $500")
- Update an existing budget
- Set default budgets or month-specific budgets

## Parameters
- **budgets** (required): Array of budget objects, each containing:
  - `category` (required): Must match one of the predefined categories:
    Income, Housing & Utilities, Food & Groceries, Transportation, Insurance,
    Healthcare, Shopping, Entertainment, Travel, Debt Payments, Internal Transfers,
    Investments, Other
  - `amount` (required): Budget target (positive number)
  - `month_year` (optional): YYYY-MM format. Omit for default budget
  - `currency` (optional): Default USD

## Example
```json
{
  "budgets": [
    {"category": "Food & Groceries", "amount": 500, "month_year": "2024-11"},
    {"category": "Entertainment", "amount": 200}
  ]
}
```

## Returns
Summary of created/updated budgets with counts and details for each budget entry.

## Output Format
```json
{
  "created_count": <integer>,
  "updated_count": <integer>,
  "results": [
    {
      "input_index": <integer>,
      "success": <boolean>,
      "budget_id": <string>,
      "category": <string>,
      "amount": <float>,
      "month_year": <string|null>,
      "error": <string|null>
    }
  ]
}
```

## Output Verbosity
- Limit responses to at most 2 short paragraphs or 6 concise bullets.
- Prioritize complete and actionable answers within this length cap.
""").strip()
