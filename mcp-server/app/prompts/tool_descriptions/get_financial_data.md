Use this when rendering the dashboard or answering questions about saved data.
Read-only. Call after any save, or when user asks about spending/income/budgets. Also used as part of the save_statement_summary workflow.

Never invent data - always call this first before describing financial information.

Parameters (all optional): user_id, bank_name, month_year (YYYY-MM), categories, profile, tab
- When called without parameters, defaults to "journey" tab
- If tab is "overview", it defaults to "journey" tab

Returns: structuredContent (data), _meta (widget payload), content (summary)
