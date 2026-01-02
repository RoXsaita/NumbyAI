Use this when reclassifying or adjusting category totals after data is saved.

Operations:
- transfer (preferred): zero-sum move; use positive transfer_amount
- edit: set amount directly (may break reconciliation)

Parameters:
- operations (required): list of {type, from_category?, to_category?, transfer_amount?, category?, new_amount?, note?}
- bank_name, month_year, user_id (optional)

Call get_financial_data() after to refresh dashboard.
