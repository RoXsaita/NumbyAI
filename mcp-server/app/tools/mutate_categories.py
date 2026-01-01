"""
Mutate Categories Tool - Edit and Transfer Category Amounts

This module provides tools to mutate category totals through:
1. Edit operations - set a category's total amount directly
2. Transfer operations - move amounts between categories (zero-sum, sign-aware)

TRANSFER SIGN RULES (automatic, zero-sum):
─────────────────────────────────────────────────────────────────────────────────
When transferring $X from Category A to Category B:

• If A is an EXPENSE (negative total, e.g., -500):
  → A increases by X (becomes less negative: -500 → -400)
  → B decreases by X (becomes more negative: -200 → -300)
  → Net change: 0 ✓

• If A is INCOME (positive total, e.g., +1000):
  → A decreases by X (becomes less positive: +1000 → +900)
  → B increases by X (becomes more positive: +200 → +300)
  → Net change: 0 ✓

This preserves statement reconciliation - the sum of all categories remains unchanged.

For SIGN CORRECTIONS (expense→income or vice versa), use two edit operations
since those represent actual changes to the statement's net flow.
─────────────────────────────────────────────────────────────────────────────────

All operations are performed server-side in a transaction to ensure data integrity.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.database import SessionLocal, CategorySummary, resolve_user_id
from app.logger import create_logger, ErrorType

# Create logger for this module
logger = create_logger("mutate_categories")


def mutate_categories_handler(
    operations: List[Dict[str, Any]],
    user_id: Optional[str] = None,
    bank_name: Optional[str] = None,
    month_year: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mutate category totals through edit or transfer operations.

    Args:
        operations: List of operation dicts. Each operation must have one of these types:
        
            EDIT operation - set absolute amount:
            - type: 'edit'
            - category: Category name (required)
            - new_amount: New total amount for category (required)
            - note: Optional note/description
            
            TRANSFER operation - move amount between categories (zero-sum):
            - type: 'transfer'
            - from_category: Source category name (required)
            - to_category: Destination category name (required)
            - transfer_amount: Positive amount to move (required)
            - note: Optional note/description
            
            Sign handling for transfers is AUTOMATIC:
            - If source is expense (negative): source gets less negative, dest gets more negative
            - If source is income (positive): source gets less positive, dest gets more positive
            - Net change is always 0 (preserves statement reconciliation)
            
        user_id: Optional user ID (defaults to test user)
        bank_name: Optional filter by bank name
        month_year: Optional filter by specific month (YYYY-MM)

    Returns:
        Dict with:
        - updated_categories: Dict of category names to their new amounts (only affected categories)
        - change_summary: Array of operation results with status messages
    """
    started_at = logger.tool_call_start(
        "mutate_categories",
        {
            "user_id": user_id,
            "bank_name": bank_name,
            "month_year": month_year,
            "operation_count": len(operations),
        },
    )

    db = SessionLocal()
    try:
        resolved_user_id = resolve_user_id(user_id)

        # Validate operations
        change_summary: List[Dict[str, Any]] = []
        
        for idx, op in enumerate(operations):
            op_type = op.get("type")
            
            if op_type not in ("edit", "transfer"):
                change_summary.append({
                    "message": (
                        f"Operation {idx + 1}: Invalid type '{op_type}'. "
                        "Supported types: 'edit' (set absolute amount), "
                        "'transfer' (move amount between categories, zero-sum)."
                    ),
                    "status": "error",
                    "category": "unknown",
                })
                continue
            
            if op_type == "edit":
                category = op.get("category")
                if not category:
                    change_summary.append({
                        "message": f"Operation {idx + 1}: Edit requires 'category' field.",
                        "status": "error",
                        "category": "unknown",
                    })
                    continue
                if "new_amount" not in op:
                    change_summary.append({
                        "message": f"Operation {idx + 1}: Edit requires 'new_amount' field.",
                        "status": "error",
                        "category": category,
                    })
                    continue
                new_amount = op.get("new_amount")
                if not isinstance(new_amount, (int, float)):
                    change_summary.append({
                        "message": f"Operation {idx + 1}: 'new_amount' must be a number.",
                        "status": "error",
                        "category": category,
                    })
                    continue
            
            elif op_type == "transfer":
                from_cat = op.get("from_category")
                to_cat = op.get("to_category")
                transfer_amount = op.get("transfer_amount")
                
                if not from_cat:
                    change_summary.append({
                        "message": f"Operation {idx + 1}: Transfer requires 'from_category' field.",
                        "status": "error",
                        "category": "unknown",
                    })
                    continue
                if not to_cat:
                    change_summary.append({
                        "message": f"Operation {idx + 1}: Transfer requires 'to_category' field.",
                        "status": "error",
                        "category": from_cat,
                    })
                    continue
                if from_cat == to_cat:
                    change_summary.append({
                        "message": f"Operation {idx + 1}: Cannot transfer to the same category.",
                        "status": "error",
                        "category": from_cat,
                    })
                    continue
                if transfer_amount is None:
                    change_summary.append({
                        "message": f"Operation {idx + 1}: Transfer requires 'transfer_amount' field.",
                        "status": "error",
                        "category": from_cat,
                    })
                    continue
                if not isinstance(transfer_amount, (int, float)):
                    change_summary.append({
                        "message": f"Operation {idx + 1}: 'transfer_amount' must be a number.",
                        "status": "error",
                        "category": from_cat,
                    })
                    continue
                if transfer_amount <= 0:
                    change_summary.append({
                        "message": (
                            f"Operation {idx + 1}: 'transfer_amount' must be positive. "
                            f"Got {transfer_amount}. Use a positive value - sign handling is automatic."
                        ),
                        "status": "error",
                        "category": from_cat,
                    })
                    continue

        # If any operations failed validation, return early
        if any(change["status"] == "error" for change in change_summary):
            logger.warn("Operations failed validation", {
                "failed_count": sum(1 for c in change_summary if c["status"] == "error"),
            })
            return {
                "updated_categories": {},
                "change_summary": change_summary,
                "status": "error",
            }

        # Fetch current category summaries
        query = db.query(CategorySummary).filter(
            CategorySummary.user_id == resolved_user_id
        )
        
        if bank_name:
            query = query.filter(CategorySummary.bank_name == bank_name)
        if month_year:
            query = query.filter(CategorySummary.month_year == month_year)
        
        summaries = query.all()
        
        if not summaries:
            logger.warn("No category summaries found", {
                "user_id": resolved_user_id,
                "bank_name": bank_name,
                "month_year": month_year,
            })
            return {
                "updated_categories": {},
                "change_summary": [{
                    "message": "No category summaries found to mutate.",
                    "status": "error",
                    "category": "unknown",
                }],
                "status": "error",
            }

        # Apply operations in a transaction
        try:
            for op in operations:
                op_type = op["type"]
                
                if op_type == "edit":
                    category = op["category"]
                    new_amount = Decimal(str(op["new_amount"]))
                    
                    # Find all summaries for this category (matching filters)
                    matching_summaries = [
                        s for s in summaries
                        if s.category == category
                        and (not bank_name or s.bank_name == bank_name)
                        and (not month_year or s.month_year == month_year)
                    ]
                    
                    if not matching_summaries:
                        # Create a new summary if none exists
                        # Use the first summary as a template for defaults, but require month_year
                        if not month_year:
                            change_summary.append({
                                "message": f"Month selection required to create new category '{category}'.",
                                "status": "error",
                                "category": category,
                            })
                            continue
                        
                        template = summaries[0] if summaries else None
                        if not template:
                            change_summary.append({
                                "message": f"No data available to create category '{category}'.",
                                "status": "error",
                                "category": category,
                            })
                            continue
                        
                        new_summary = CategorySummary(
                            user_id=resolved_user_id,
                            bank_name=bank_name or template.bank_name,
                            month_year=month_year,
                            category=category,
                            amount=new_amount,
                            currency=template.currency,
                            transaction_count=0,
                        )
                        db.add(new_summary)
                        change_summary.append({
                            "message": f"Created category '{category}' with amount {new_amount}.",
                            "status": "success",
                            "category": category,
                            "details": {
                                "category": category,
                                "old_amount": None,
                                "new_amount": float(new_amount),
                            },
                        })
                    else:
                        # Update existing summaries - distribute new_amount proportionally
                        # or replace all with a single summary
                        # For simplicity, we'll replace all matching summaries with a single one
                        old_amount = sum(Decimal(str(s.amount)) for s in matching_summaries)
                        total_count = sum(int(s.transaction_count) for s in matching_summaries)
                        currency = matching_summaries[0].currency
                        bank = matching_summaries[0].bank_name
                        month = matching_summaries[0].month_year
                        
                        # Delete old summaries
                        for s in matching_summaries:
                            db.delete(s)
                        
                        # Create single replacement summary
                        new_summary = CategorySummary(
                            user_id=resolved_user_id,
                            bank_name=bank,
                            month_year=month,
                            category=category,
                            amount=new_amount,
                            currency=currency,
                            transaction_count=total_count,
                        )
                        db.add(new_summary)
                        change_summary.append({
                            "message": f"Updated category '{category}': {old_amount} → {new_amount}.",
                            "status": "success",
                            "category": category,
                            "details": {
                                "category": category,
                                "old_amount": float(old_amount),
                                "new_amount": float(new_amount),
                            },
                        })
                
                elif op_type == "transfer":
                    from_cat = op["from_category"]
                    to_cat = op["to_category"]
                    transfer_amount = Decimal(str(op["transfer_amount"]))
                    note = op.get("note", "")
                    
                    # Find source category summary
                    from_summaries = [
                        s for s in summaries
                        if s.category == from_cat
                        and (not bank_name or s.bank_name == bank_name)
                        and (not month_year or s.month_year == month_year)
                    ]
                    
                    if not from_summaries:
                        change_summary.append({
                            "message": f"Source category '{from_cat}' not found.",
                            "status": "error",
                            "category": from_cat,
                        })
                        continue
                    
                    # Calculate current source total
                    from_current = sum(Decimal(str(s.amount)) for s in from_summaries)
                    
                    # Determine sign handling based on source category's sign
                    # If source is negative (expense): source gets +amount, dest gets -amount
                    # If source is positive (income): source gets -amount, dest gets +amount
                    is_expense = from_current < 0
                    
                    if is_expense:
                        # Moving expenses: source becomes less negative, dest becomes more negative
                        from_new = from_current + transfer_amount
                        to_delta = -transfer_amount
                        sign_explanation = f"expense transfer: {from_cat} +{transfer_amount} (less negative), {to_cat} -{transfer_amount} (more negative)"
                    else:
                        # Moving income: source becomes less positive, dest becomes more positive
                        from_new = from_current - transfer_amount
                        to_delta = transfer_amount
                        sign_explanation = f"income transfer: {from_cat} -{transfer_amount} (less positive), {to_cat} +{transfer_amount} (more positive)"
                    
                    # Find or create destination category summary
                    to_summaries = [
                        s for s in summaries
                        if s.category == to_cat
                        and (not bank_name or s.bank_name == bank_name)
                        and (not month_year or s.month_year == month_year)
                    ]
                    
                    if to_summaries:
                        to_current = sum(Decimal(str(s.amount)) for s in to_summaries)
                        to_new = to_current + to_delta
                    else:
                        # Destination doesn't exist - create it with just the transferred amount
                        to_current = Decimal("0")
                        to_new = to_delta
                    
                    # Update source category (replace all matching with single summary)
                    from_total_count = sum(int(s.transaction_count) for s in from_summaries)
                    from_currency = from_summaries[0].currency
                    from_bank = from_summaries[0].bank_name
                    from_month = from_summaries[0].month_year
                    
                    for s in from_summaries:
                        db.delete(s)
                    
                    from_replacement = CategorySummary(
                        user_id=resolved_user_id,
                        bank_name=from_bank,
                        month_year=from_month,
                        category=from_cat,
                        amount=from_new,
                        currency=from_currency,
                        transaction_count=from_total_count,
                    )
                    db.add(from_replacement)
                    
                    # Update destination category
                    if to_summaries:
                        to_total_count = sum(int(s.transaction_count) for s in to_summaries)
                        to_currency = to_summaries[0].currency
                        to_bank = to_summaries[0].bank_name
                        to_month = to_summaries[0].month_year
                        
                        for s in to_summaries:
                            db.delete(s)
                        
                        to_replacement = CategorySummary(
                            user_id=resolved_user_id,
                            bank_name=to_bank,
                            month_year=to_month,
                            category=to_cat,
                            amount=to_new,
                            currency=to_currency,
                            transaction_count=to_total_count,
                        )
                        db.add(to_replacement)
                    else:
                        # Create new destination category
                        if not month_year:
                            # Use source's month if no filter specified
                            dest_month = from_month
                        else:
                            dest_month = month_year
                        
                        to_replacement = CategorySummary(
                            user_id=resolved_user_id,
                            bank_name=bank_name or from_bank,
                            month_year=dest_month,
                            category=to_cat,
                            amount=to_new,
                            currency=from_currency,
                            transaction_count=0,
                        )
                        db.add(to_replacement)
                    
                    # Track the new summaries for subsequent operations
                    summaries = [s for s in summaries if s not in from_summaries and s not in to_summaries]
                    summaries.extend([from_replacement, to_replacement])
                    
                    change_summary.append({
                        "message": (
                            f"Transferred {transfer_amount} from '{from_cat}' to '{to_cat}'. "
                            f"{from_cat}: {from_current} → {from_new}, "
                            f"{to_cat}: {to_current} → {to_new}. "
                            f"Net change: 0. ({sign_explanation})"
                        ),
                        "status": "success",
                        "category": f"{from_cat} → {to_cat}",
                        "details": {
                            "from_category": from_cat,
                            "to_category": to_cat,
                            "transfer_amount": float(transfer_amount),
                            "from_old": float(from_current),
                            "from_new": float(from_new),
                            "to_old": float(to_current),
                            "to_new": float(to_new),
                            "net_change": 0,
                        },
                    })
            
            db.commit()
            logger.info("Category mutations applied successfully", {
                "operation_count": len(operations),
                "success_count": sum(1 for c in change_summary if c["status"] == "success"),
            })
            
        except Exception as e:
            db.rollback()
            logger.tool_call_error(
                "mutate_categories",
                started_at,
                e,
                ErrorType.DB_ERROR,
            )
            change_summary.append({
                "message": f"Database error: {str(e)}",
                "status": "error",
                "category": "unknown",
            })
            raise
        
        # Extract updated categories from change_summary (lean response)
        updated_categories: Dict[str, float] = {}
        for change in change_summary:
            if change.get("status") == "success":
                details = change.get("details", {})
                if "from_category" in details:
                    # Transfer operation - has from/to details
                    updated_categories[details["from_category"]] = details["from_new"]
                    updated_categories[details["to_category"]] = details["to_new"]
                elif "category" in details and "new_amount" in details:
                    # Edit operation - has category/new_amount
                    updated_categories[details["category"]] = details["new_amount"]
        
        logger.tool_call_end("mutate_categories", started_at, {
            "operation_count": len(operations),
            "success_count": sum(1 for c in change_summary if c["status"] == "success"),
        })
        
        return {
            "updated_categories": updated_categories,
            "change_summary": change_summary,
            "status": "success" if any(c["status"] == "success" for c in change_summary) else "error",
        }
        
    except Exception as e:
        logger.tool_call_error(
            "mutate_categories",
            started_at,
            e,
            ErrorType.UNKNOWN_ERROR,
        )
        raise
    
    finally:
        db.close()
