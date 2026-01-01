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
    2. Parse all transactions from the statement
    3. Apply matching preference rules to transactions FIRST
    4. Manually categorize remaining transactions using predefined categories
       (CRITICAL: Assign categories BEFORE any aggregation)
       IMPORTANT: Always categorize each transaction to its proper specific category based on merchant/description.
       Never lazily group massive totals (e.g., all inflows as Income, all outflows as Other). Categorize granularly.
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
    • user_id (optional): Defaults to test user

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
- `user_id` (optional): User identifier (defaults to test user).
- `bank_name` (optional): Restrict search to a specific bank (e.g., "Santander", "Revolut").
- `month_year` (optional): Filter by month in YYYY-MM format (e.g., "2025-07").
- `categories` (optional): Array of categories to include (e.g., ["Food & Groceries", "Transportation"]).

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
# Role and Objective
Fetch all categorization preferences required for transaction categorization. This endpoint MUST be called FIRST when processing any bank statement to retrieve user-defined rules for automatic transaction categorization.

# Instructions
- Always call this endpoint before any transaction processing.
- Return a list of enabled user-defined categorization rules for the given user.

## Parameters
- `user_id` (optional, string): User identifier. Defaults to test user if not provided.

## Returns
A JSON array of all enabled categorization preferences for the user, sorted in this order:
1. Bank-specific rules first (where `bank_name` is not null).
2. Then by priority, with higher integer values first.

Each rule object MUST include:
- `name` (string): Rule name.
- `bank_name` (string|null): The bank this rule applies to or null for global application.
- `rule` (object):
    - `conditions` (object): Transaction match conditions, e.g., `{ "merchant": "UBER*" }`
    - `category` (string): Output category label.
- `priority` (integer): Rule priority (higher is processed before lower priority rules).

- If the user has no preferences, return an empty JSON array (`[]`).
- If the specified `user_id` does not exist, return an error object: `{ "error": "User not found" }`

## Example Rule Object
```json
{
    "name": "Uber rides",
    "bank_name": null,
    "rule": {
        "conditions": {"merchant": "UBER*"},
        "category": "Transportation"
    },
    "priority": 0
}
```

## Output Format
- Success: JSON array of rule objects as described above.
- No preferences: Empty array `[]`.
- User not found: `{ "error": "User not found" }`

## Output Verbosity
- Keep the response concise: output should not exceed 2 short paragraphs or, if using bullets, a maximum of 6 bullets (1 line each).
- Prioritize delivering complete and actionable answers within this length cap.
""").strip()

SAVE_CATEGORIZATION_PREFERENCES_DESCRIPTION = textwrap.dedent("""
Batch save multiple categorization preference rules in a single API call.

Use this endpoint when you have several patterns to save—this is more efficient than making individual calls for each preference.

### Parameters
- **preferences** (required): Array of preference objects. Each object includes:
  - **name** (required): Short rule name (e.g., "Uber rides")
  - **rule** (required): Structured rule object containing conditions and the target category. Example:
    ```json
    {
      "conditions": { "merchant": "UBER*" },
      "category": "Transportation"
    }
    ```
  - **bank_name** (optional): Bank name for bank-specific rules
  - **priority** (optional): Integer, where a higher number represents higher priority (default is 0)
  - **preference_id** (optional): If provided, updates the existing preference with this ID
- **user_id** (optional): User identifier (defaults to the test user if omitted)

#### Example preferences array
```json
[
  {
    "name": "Uber rides",
    "rule": { "conditions": { "merchant": "UBER*" }, "category": "Transportation" }
  },
  {
    "name": "Netflix",
    "rule": { "conditions": { "merchant": "NETFLIX*" }, "category": "Entertainment" },
    "priority": 1
  }
]
```

### Returns
A summary with counts of created and updated preferences, along with a detailed result for each preference in the same order as the input array.

#### Output Format & Verbosity
The response is a JSON object with the following structure:
```json
{
  "created_count": <integer>,
  "updated_count": <integer>,
  "results": [
    {
      "input_index": <integer>,
      "success": <boolean>,
      "preference_id": <string>,
      "error": <string|null>
    },
    ...
  ]
}
```
- If a preference fails validation or cannot be processed, the respective result entry will have `"success": false` and a non-null `"error"` message explaining the issue (e.g., missing required field).
- Successfully processed preferences will have `"success": true`, a `"preference_id"` referencing the created or updated preference, and `"error": null`.
- The order of `results` always matches the order of the input preferences array.

**Output Verbosity:**
- Limit all descriptions and summaries to at most 2 short paragraphs.
- If you use bulleted information, use no more than 6 concise bullets (1 line each).
- Prioritize complete, actionable answers within these length caps.""").strip()

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
- **user_id** *(optional)*: User identifier (defaults to test user)
- **bank_name** *(optional)*: Filter by specific bank name
- **month_year** *(optional)*: Filter by month in YYYY-MM format

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
  - `amount` (required): Budget target amount (positive number)
  - `month_year` (optional): Specific month in YYYY-MM format. If omitted, sets as default budget
  - `currency` (optional): Currency code (default: USD)
- **user_id** (optional): User identifier (defaults to test user)

## Example Input
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
