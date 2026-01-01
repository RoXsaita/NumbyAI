"""
Tool Description Constants

Following OpenAI guidance: concise "Use this when..." descriptions with explicit parameters.
"""

import textwrap

# Shared constants
CATEGORY_LIST = textwrap.dedent("""
- Income: salary, wages, bonuses, interest, dividends
- Housing & Utilities: rent, utilities, internet, phone
- Food & Groceries: groceries, restaurants, coffee, food delivery
- Transportation: gas, transit, car payment, parking, rideshare
- Insurance: health, car, home, life insurance premiums
- Healthcare: medical bills, prescriptions, dental, vision
- Shopping: retail, clothing, electronics, household items, refunds
- Entertainment: movies, subscriptions, hobbies, gym
- Travel: flights, hotels, vacation expenses
- Debt Payments: credit card payments, loans (excluding auto/mortgage)
- Internal Transfers: own-account transfers, currency exchanges, linked deposits
- Investments: stock purchases, retirement contributions, brokerage transfers
- Other: anything else
""").strip()

CATEGORY_RULES = "ONE category per transaction. Refunds → original category. Own-account transfers → Internal Transfers."
PRIVACY_RULES = "App stores category totals only. Never include account numbers, IBANs, card numbers, or emails."

# ============================================================================
# FETCH_PREFERENCES - The Gateway Tool (call FIRST, always)
# ============================================================================
FETCH_PREFERENCES_DESCRIPTION = textwrap.dedent("""
Use this IMMEDIATELY when user mentions finance-app, asks "how does this work", wants help with budgeting, or at the start of ANY finance conversation. Also used as part of the save_statement_summary workflow.

**CRITICAL: Never respond to the user about finance topics without calling this tool first.**
The tool returns contextual guidance based on database state - follow it.

Onboarding (when settings missing or onboarding_complete=false):
1. Ask for functional_currency (ISO 4217: USD, EUR, GBP, etc.) - this is the currency for all saved data
2. Optional: bank_accounts_count, household profiles (e.g., ["Me", "Partner", "Joint"])
3. Save via save_preferences(preference_type="settings")
4. Privacy note: App stores summaries only (not raw transactions). User still shares data with OpenAI.
5. When ready for first statement: user provides CSV/Excel + NET transaction total.
6. USE ASCI Art to show the workflow, and concise final summary including of responsibilities (you and user)

Parameters:
- preference_type: Single type or array of types to fetch multiple at once
  * Single: "settings" | "categorization" | "parsing" | "list"
  * Multiple: ["settings", "categorization"] | ["settings", "parsing", "categorization"]
  * Examples: fetch both settings and categorization rules in one call
- bank_name (optional): for parsing rules
- user_id (optional)

When fetching multiple types, all results are returned in a single response under structuredContent.results.
""").strip()

# ============================================================================
# SAVE_PREFERENCES - Persist user data
# ============================================================================
SAVE_PREFERENCES_DESCRIPTION = textwrap.dedent("""
Use this when persisting settings, categorization rules, or parsing instructions immediately after learning them.

**CRITICAL: Data is NOT saved unless you call this. Never claim "saved" without tool output.**
Always save parsing rules after first-time bank setup or they're lost next session.

Parameters:
- preference_type: "settings" | "categorization" | "parsing"
- preferences: list of objects (schema below)
- user_id (optional)

Settings: {functional_currency, bank_accounts_count?, profiles?, onboarding_complete?}
Categorization: {name, rule, bank_name?, priority?}
Parsing: {name, bank_name, instructions: {steps[], key_patterns?, notes?}}
""").strip()

# ============================================================================
# GET_FINANCIAL_DATA - Dashboard/read tool
# ============================================================================
GET_FINANCIAL_DATA_DESCRIPTION = textwrap.dedent("""
Use this when rendering the dashboard or answering questions about saved data.
Read-only. Call after any save, or when user asks about spending/income/budgets. Also, used as part of the save_statement_summary workflow.

Never invent data - always call this first before describing financial information.

Parameters (all optional): user_id, bank_name, month_year (YYYY-MM), categories, profile, tab
- When called without parameters, defaults to "journey" tab
- If tab is "overview", it defaults to "journey" tab

Returns: structuredContent (data), _meta (widget payload), content (summary)
""").strip()

# ============================================================================
# SAVE_STATEMENT_SUMMARY - Single month
# ============================================================================
SAVE_STATEMENT_SUMMARY_DESCRIPTION = textwrap.dedent("""
Run the workflow below Autonomously END-TO-END WITHOUT PAUSE and call this tool when the user provides you with a bank statement and the net flow amount.
Replaces existing data for same (user, bank_name, month_year).

PLEASE ACTIVATE DEEP THINKING MODE AND EXECUTE EACH STEP OF THE WORKFLOW IN DETAIL.
SAVE_STATEMENT_SUMMARY workflow:
1. IMMEDIATELY once statement + Net amount is received, fetch preferences for parsing and categorization
2. Reverse engineer the statement to understand the format based on bank conventions and derive the net flow amount from the statement.
3. CRITICAL: Assigning categories is the most complex step in the workflow. Break down the task into smaller steps and execute each step in detail.
   - Make sure the description is not horizentally truncated in the statement and fix (extend columnw with) as needed.
   - FIRST TIME SETUP: Assign every single transaction in the statement with categorization rules as your reference.
   - USER WITH EXISTING CATEGORIZATION PREFERENCES: USE RULES AND APPLY FUZZY VLOOKUP TO THE STATEMENT THEN MANUALLY CATEGORIZE THE REST.
4. Create pivot table using panda and numpy to aggregate the data by category as rows and months as columns. Include grand totals in the pivot table.
5. Match grand total with the NET FLOW Provided by the user. If there is <2.5% difference, plug the difference into "Other" category and explain the discrepancy to the user.
6. Save the monthly summary via save_statement_summary
7. Call get_financial_data to render the dashboard.
8. Summarise the highest 3-4 transactinos per category for the user (or very high lvl insight if its high volume transactions of a specific category)
9. Confirm if the user is happy with the categorization preferences.

Prerequisites: fetch_preferences for settings/parsing/categorization first.

Insights (capture what dashboard cannot show):
- Top 5-7 transactions by amount
- Recurring merchant patterns
- Notable items (large purchases, refunds)
Do NOT repeat category totals or flows totals.

Categories:
{categories}
{category_rules}

{privacy}

Parameters:
- category_summaries (required): list of {{category, amount, currency, month_year, transaction_count?}}
- bank_name (required)
- statement_net_flow (required): user-provided NET total
- coverage_from, coverage_to (required): YYYY-MM-DD
- statement_insights (required): transaction-level context
- confirmation_text, profile, user_id (optional)
""").strip().format(
    categories=CATEGORY_LIST,
    category_rules=CATEGORY_RULES,
    privacy=PRIVACY_RULES,
)

# ============================================================================
# MUTATE_CATEGORIES - Post-save adjustments
# ============================================================================
MUTATE_CATEGORIES_DESCRIPTION = textwrap.dedent("""
Use this when reclassifying or adjusting category totals AFTER data is saved.

Operations:
- TRANSFER (preferred): zero-sum move; use positive transfer_amount
- EDIT: set amount directly (may break reconciliation)

Parameters:
- operations (required): list of {type, from_category?, to_category?, transfer_amount?, category?, new_amount?, note?}
- bank_name, month_year, user_id (optional)

Call get_financial_data() after to refresh dashboard.
""").strip()

# ============================================================================
# SAVE_BUDGET - Budget targets
# ============================================================================
SAVE_BUDGET_DESCRIPTION = textwrap.dedent("""
Use this when setting or updating budget targets per category.

Parameters:
- budgets (required): list of {category, amount (positive), month_year?, currency?}
- user_id (optional)

Omit month_year for recurring budget. Call get_financial_data() after.
""").strip()

# Backward compatibility
FETCH_CATEGORIZATION_PREFERENCES_DESCRIPTION = FETCH_PREFERENCES_DESCRIPTION
SAVE_CATEGORIZATION_PREFERENCES_DESCRIPTION = SAVE_PREFERENCES_DESCRIPTION
