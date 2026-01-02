# Codebase Review - NumbyAI

Scope: Full repo scan with emphasis on statement processing, categorization quality ("Other" overuse), and cleanup.

## Key findings (highest impact)

1) Categorization rules are stored but never applied in the main pipeline, so user preferences do not improve results.
   - Pipeline reads `CategorizationRule`, while the UI saves `CategorizationPreference` rules, and the rule learning helper is unused.
   - Files: `mcp-server/app/main.py:1303`, `mcp-server/app/tools/save_preferences.py`, `mcp-server/app/tools/fetch_preferences.py`, `mcp-server/app/services/cursor_agent_service.py:748`, `web/src/widgets/dashboard.tsx:3110`.

2) LLM categorization output is not validated; missing/invalid results silently default to "Other" for large portions of the dataset.
   - Any JSON parse failure or missing IDs yields empty lists and the fallback path assigns "Other".
   - Files: `mcp-server/app/services/cursor_agent_service.py:190-437`, `mcp-server/app/main.py:1342-1355`.

3) Auto-parsing schema generation is incompatible with current column mapping validation.
   - Heuristic analyzer emits values like "Column 0" but `_resolve_column_name` only accepts numeric indices. When no header mapping is supplied, this path fails.
   - Files: `mcp-server/app/services/statement_analyzer.py:239-289`, `mcp-server/app/tools/statement_parser.py:306-340`.

4) The statement summary save step can reject results ("Other" too large, reconciliation failure) but the pipeline ignores the response and returns success.
   - Files: `mcp-server/app/main.py:1434-1459`, `mcp-server/app/tools/save_statement_summary.py:248-334`.

5) Transaction updates do not sync CategorySummary or StatementPeriod, so the dashboard can drift from edits.
   - `PATCH /api/transactions` updates Transaction rows without re-aggregation.
   - Files: `mcp-server/app/main.py:1707-1741`, `mcp-server/app/tools/financial_data.py:623-662`.

6) Security/auth is mostly bypassed in core endpoints, and login/register do not hash or verify passwords.
   - Test user is injected in most endpoints; password handling is TODO.
   - Files: `mcp-server/app/main.py:1037`, `mcp-server/app/main.py:1928-1988`.

## Proposed updates (from -> to)

| Area | From (current) | To (proposed) | Reason/Why | Conclusion/Impact |
| --- | --- | --- | --- | --- |
| Categorization rules | Pipeline uses `CategorizationRule`, UI saves `CategorizationPreference` rules, and learning is unused (`mcp-server/app/main.py:1303`) | Unify rule storage/engine: apply `CategorizationPreference` rules deterministically before LLM; optionally migrate into `CategorizationRule` and delete one model | Current rules are effectively ignored, causing "Other" overuse and inconsistent categorization | Immediate quality lift; preferences start to actually drive categorization |
| LLM output validation | Accepts any LLM output; missing IDs default to "Other" (`mcp-server/app/services/cursor_agent_service.py:394`) | Validate: must return 1:1 IDs, categories in enum; retry failed batches; fallback to rule engine / heuristics for leftovers | Prevents silent failure and mass "Other" assignments | Fewer bad batches; auditable categorization confidence |
| Auto schema build | Heuristic output uses "Column N"; parser only accepts numeric indices (`statement_analyzer.py:239`, `statement_parser.py:306`) | Normalize analysis output to numeric strings; allow parser to resolve "Column N" if found | Current fallback path breaks parsing when user doesn't map headers | Eliminates a common auto-parsing failure path |
| Error handling in pipeline | `save_statement_summary_handler` return is ignored (`main.py:1434`) | Inspect response; if error, return structured failure to UI or retry recategorization | Prevents false success when summary is rejected | Ensures dashboards reflect saved data |
| Categorization data used | `vendor_payee` and raw `category` fields parsed but dropped (`statement_parser.py:159-280`, `normalize_transaction`) | Include vendor/payee in normalized payload and LLM prompt; prefer vendor/payee as merchant | Higher-quality signal for categorization | Reduced "Other"; more consistent merchant grouping |
| Rule schema | UI writes `{ pattern, category }` while backend expects flexible rules and never evaluates them (`dashboard.tsx:3110`, `save_preferences.py`) | Define a single rule schema (e.g., `merchant_pattern`, `bank_name`, `amount_range`, `category`) and a deterministic evaluator | Prevents rule drift and ambiguity | Rules become reliable and testable |
| Transaction edits | Category edits mutate Transaction only (`main.py:1707`) | Re-aggregate summaries on edits OR deprecate summaries and compute from transactions consistently | Fixes data drift between Transaction and summaries | Dashboard reflects latest edits |
| Performance | `get_financial_data_handler` loads all transactions into memory (`financial_data.py:627`) | Aggregate in SQL or add pagination + cached rollups | Scales better with larger datasets | Faster dashboard and lower memory |
| Monetary precision | Amounts stored as float at multiple steps (`statement_parser.py:266`, `normalize_transaction`) | Keep Decimal through pipeline or store integer cents | Avoids rounding mismatches and reconciliation errors | More accurate analytics |
| Auth/security | Passwords are not hashed; test user injected (`main.py:1928`, `main.py:1037`) | Implement proper password hashing/verification and enforce auth for write endpoints | Security and data isolation | Production-ready auth |
| UI API base URL | `process.env.API_BASE_URL` in browser (`web/src/lib/api-client.ts:8`) | Use `import.meta.env.VITE_API_BASE_URL` or a shared config module | Prevent runtime ReferenceError in browser builds | More reliable deployments |
| Dashboard TODOs | Category mutations and delete rule are no-ops (`dashboard.tsx:2896`, `dashboard.tsx:3139`) | Implement API endpoints for rule deletion and transaction mutation linkage | UI suggests features that don’t persist | Consistent behavior and user trust |

## Categorization improvements (focused plan)

- Deterministic rule pass: apply saved rules (case-insensitive + regex) before LLM.
- Normalization layer: map synonyms ("Groceries" -> "Food & Groceries") and reject out-of-enum categories.
- Two-stage LLM: first pass on remaining uncategorized; second pass only on "Other" with extra context.
- Merchant extraction: use `vendor_payee` when present; enhance extraction with regex list and merchant normalization.
- Learning loop: call `learn_merchant_rules` after successful categorization, gated by confidence thresholds.

## Dead code / cleanup candidates (not referenced by app code)

- `mcp-server/analyze_*.py`, `mcp-server/categorize_*.py`, `mcp-server/categorize_*_request.py`, `mcp-server/categorize_*_task.py`, `mcp-server/categorize_*_standalone.py` (standalone experiments).
- JSON outputs: `mcp-server/categorization_results*.json`, `mcp-server/categorize_output*.json`, `mcp-server/categorized_transactions*.json`, `mcp-server/*_analysis.json`.
- Runtime artifacts: `mcp-server/uploads/*`, `mcp-server/finance_recon.db`, `mcp-server/finance_recon.db.backup`, `mcp-server/audit/*`.
- Legacy UI: `web/src/components/ChatInterface.tsx`, `web/src/components/ChatMessage.tsx`, `web/src/components/QuestHelpModal.tsx`, `web/src/components/MilestoneCard.tsx`, `web/src/components/Mascot.tsx`, `web/src/lib/mascot-data.ts`, `web/src/assets/mascots/*`.
- Historical descriptions: `mcp-server/app/tools/version_history/*`.

## Additional refactoring notes

- Centralize category constants in a shared schema (server + web) to prevent drift.
- Make `CategorizationRule` vs `CategorizationPreference` a single source of truth.
- Gate debug logging in `SimpleUpload` behind the config debug flag.

