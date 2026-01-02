Use this IMMEDIATELY when user mentions finance-app, asks "how does this work", wants help with budgeting, or at the start of ANY finance conversation. Also used as part of the save_statement_summary workflow.

CRITICAL: Never respond to the user about finance topics without calling this tool first.
The tool returns contextual guidance based on database state - follow it.

Onboarding (when settings missing or onboarding_complete=false):
1. Ask for functional_currency (ISO 4217: USD, EUR, GBP, etc.) - this is the currency for all saved data
2. Optional: bank_accounts_count, household profiles (e.g., ["Me", "Partner", "Joint"])
3. Save via save_preferences(preference_type="settings")
4. Privacy note: App stores summaries only (not raw transactions). User still shares data with OpenAI.
5. When ready for first statement: user provides CSV/Excel + NET transaction total.
6. Use ASCII art to show the workflow, and a concise final summary including responsibilities (you and user)

Parameters:
- preference_type: Single type or array of types to fetch multiple at once
  * Single: "settings" | "categorization" | "parsing" | "list"
  * Multiple: ["settings", "categorization"] | ["settings", "parsing", "categorization"]
  * Examples: fetch both settings and categorization rules in one call
- bank_name (optional): for parsing rules
- user_id (optional)

When fetching multiple types, all results are returned in a single response under structuredContent.results.
