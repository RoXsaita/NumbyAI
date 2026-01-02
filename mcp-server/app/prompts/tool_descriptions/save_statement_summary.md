Run the workflow below autonomously end-to-end without pause and call this tool when the user provides you with a bank statement and the net flow amount.
Replaces existing data for same (user, bank_name, month_year).

Please activate deep thinking mode and execute each step of the workflow in detail.
SAVE_STATEMENT_SUMMARY workflow:
1. Immediately once statement + net amount is received, fetch preferences for parsing and categorization
2. Reverse engineer the statement to understand the format based on bank conventions and derive the net flow amount from the statement.
3. Critical: Assigning categories is the most complex step in the workflow. Break down the task into smaller steps and execute each step in detail.
   - Make sure the description is not horizontally truncated in the statement and fix as needed.
   - First time setup: Assign every single transaction in the statement with categorization rules as your reference.
   - User with existing categorization preferences: use rules and apply fuzzy lookup to the statement, then manually categorize the rest.
4. Create pivot table using panda and numpy to aggregate the data by category as rows and months as columns. Include grand totals in the pivot table.
5. Match grand total with the net flow provided by the user. If there is <2.5% difference, plug the difference into "Other" category and explain the discrepancy to the user.
6. Save the monthly summary via save_statement_summary
7. Call get_financial_data to render the dashboard.
8. Summarize the highest 3-4 transactions per category for the user (or high-level insight if high volume transactions of a specific category)
9. Confirm if the user is happy with the categorization preferences.

Prerequisites: fetch_preferences for settings/parsing/categorization first.

Insights (capture what dashboard cannot show):
- Top 5-7 transactions by amount
- Recurring merchant patterns
- Notable items (large purchases, refunds)
Do not repeat category totals or flow totals.

Categories:
{{categories}}
{{category_rules}}

{{privacy}}

Parameters:
- category_summaries (required): list of {category, amount, currency, month_year, transaction_count?}
- bank_name (required)
- statement_net_flow (required): user-provided net total
- coverage_from, coverage_to (required): YYYY-MM-DD
- statement_insights (required): transaction-level context
- confirmation_text, profile, user_id (optional)
