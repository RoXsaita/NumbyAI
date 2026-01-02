Use this when persisting settings, categorization rules, or parsing instructions immediately after learning them.

CRITICAL: Data is NOT saved unless you call this. Never claim "saved" without tool output.
Always save parsing rules after first-time bank setup or they're lost next session.

Parameters:
- preference_type: "settings" | "categorization" | "parsing"
- preferences: list of objects (schema below)
- user_id (optional)

Settings: {functional_currency, bank_accounts_count?, profiles?, onboarding_complete?}
Categorization: {name, rule, bank_name?, priority?}
Parsing: {name, bank_name, instructions: {steps[], key_patterns?, notes?}}

Categorization rule fields (examples):
- {merchant_pattern, category}
- {description_pattern, category}
- {conditions: {merchant, amount_min, amount_max}, category}
