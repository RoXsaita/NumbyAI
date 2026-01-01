"""Write-only tool to save AI-aggregated category summaries"""
from datetime import date
from typing import List, Optional, Dict, Tuple

from app.database import (
    CategorizationPreference,
    CategorySummary,
    StatementInsight,
    StatementPeriod,
    SessionLocal,
    resolve_user_id,
)
from app.logger import create_logger, ErrorType
from app.tools.category_helpers import PREDEFINED_CATEGORIES
from app.tools.redaction import redact_insights, validate_no_sensitive_data

# Create logger for this module
logger = create_logger("save_statement_summary")

# Settings preference name constant (must match fetch_preferences.py and save_preferences.py)
SETTINGS_PREFERENCE_NAME = "user_settings"

# Reconciliation constants
# NOTE: Tolerance is 2.5% per spec and audit findings (#34)
RECONCILIATION_TOLERANCE_PCT = 0.025  # 2.5% tolerance for category sum vs statement net flow
MIN_RECONCILIATION_THRESHOLD = 1.0    # Minimum absolute threshold to avoid div-by-zero edge cases

SAVE_STATEMENT_SUMMARY_WORKFLOW_STEPS = (
    "SAVE_STATEMENT_SUMMARY workflow:\n"
    "1. IMMEDIATELY once statement + Net amount is received, fetch preferences for parsing and categorization\n"
    "2. Reverse engineer the statement to understand the format based on bank conventions and derive the net flow amount from the statement.\n"
    "3. Ensure you can view the full, non-truncated descriptions and vendor fields from the CSV before categorizing.\n"
    "4. CRITICAL: Assigning categories is the most complex step in the workflow. Break down the task into smaller steps and execute each step in detail.\n"
    "   - FIRST TIME SETUP: Assign every single transaction in the statement with categorization rules as your reference.\n"
    "   - USER WITH EXISTING CATEGORIZATION PREFERENCES: USE RULES AND APPLY FUZZY VLOOKUP TO THE STATEMENT THEN MANUALLY CATEGORIZE THE REST.\n"
    "5. Use Python fuzzy matching/regex to map vendors and descriptions to categories.\n"
    "6. Create pivot table using panda and numpy to aggregate the data by category as rows and months as columns. Include grand totals in the pivot table.\n"
    "7. Match grand total with the NET FLOW Provided by the user. If there is <2.5% difference, plug the difference into \"Other\" category and explain the discrepancy to the user.\n"
    "8. Before you run the save_statement_summary tool, check if the 'other' category represents more than 40% of the total. If yes, re-assess your categorization, and consider asking the user for additional details.\n"
    "9. Save the monthly summary via save_statement_summary\n"
    "10. Call get_financial_data to render the dashboard.\n"
    "11. Summarise the highest 3-4 transactinos per category for the user (or very high lvl insight if its high volume transactions of a specific category)\n"
    "12. Confirm if the user is happy with the categorization preferences."
)

SAVE_STATEMENT_SUMMARY_CONTRACT_MESSAGE = (
    "Please follow the instructions in the save_statement_summary tool contracts as follows:\n\n"
    f"{SAVE_STATEMENT_SUMMARY_WORKFLOW_STEPS}"
)


def _build_contract_error(reason: str, structured_overrides: Optional[Dict[str, object]] = None) -> dict:
    error_text = f"{reason}\n\n{SAVE_STATEMENT_SUMMARY_CONTRACT_MESSAGE}"
    structured_content = {"error": error_text}
    if structured_overrides:
        structured_content.update(structured_overrides)
    return {
        "structuredContent": structured_content,
        "content": [{"type": "text", "text": error_text}],
    }


def _get_registered_banks(db, user_id: str) -> Tuple[List[str], bool]:
    """
    Fetch the list of registered banks for a user from their settings.
    
    Returns:
        Tuple of (registered_banks list, settings_exist bool)
        - registered_banks: List of bank names (empty if not configured)
        - settings_exist: Whether user settings exist at all
    """
    settings_pref = (
        db.query(CategorizationPreference)
        .filter(
            CategorizationPreference.user_id == user_id,
            CategorizationPreference.preference_type == "settings",
            CategorizationPreference.name == SETTINGS_PREFERENCE_NAME,
            CategorizationPreference.enabled.is_(True)
        )
        .first()
    )
    
    if not settings_pref:
        return [], False
    
    settings = settings_pref.rule or {}
    registered_banks = settings.get("registered_banks", [])
    return registered_banks, True


def _validate_bank_name(bank_name: str, registered_banks: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that a bank name matches one of the registered banks (case-insensitive).
    
    Returns:
        Tuple of (is_valid, matched_bank_name)
        - is_valid: True if bank name matches a registered bank
        - matched_bank_name: The canonical bank name from registered_banks (preserves original casing)
    """
    if not registered_banks:
        return True, bank_name  # No banks registered = allow any (backward compatibility)
    
    bank_name_lower = bank_name.strip().lower()
    for registered in registered_banks:
        if registered.lower() == bank_name_lower:
            return True, registered  # Return the canonical name
    
    return False, None


async def save_statement_summary_handler(
    category_summaries: List[dict],
    bank_name: str,
    statement_net_flow: float,
    confirmation_text: Optional[str] = None,
    statement_insights: Optional[str] = None,
    coverage_from: str = "",
    coverage_to: str = "",
    profile: Optional[str] = None,
    user_id: Optional[str] = None
) -> dict:
    """
    Save AI-aggregated category summaries to database.

    The AI provides pre-aggregated category summaries (not individual transactions).
    Each summary represents the total for a category within a statement period.

    RECONCILIATION: The sum of all category amounts is automatically validated against
    statement_net_flow. If the difference exceeds 2.5%, the save is REJECTED.

    Args:
        category_summaries: List of category summary objects with:
            - category: Category name (must be valid predefined category) [REQUIRED]
            - amount: Total amount for category (negative for outflows, positive for inflows) [REQUIRED]
            - currency: Currency code (e.g., "USD", "EUR") [REQUIRED]
            - month_year: Month identifier (YYYY-MM format) [REQUIRED]
            - transaction_count: Number of transactions in this category [OPTIONAL, defaults to 0]
        bank_name: Bank name for identification (e.g., "Santander", "Revolut")
        statement_net_flow: Net flow from statement (ending_balance - beginning_balance) [REQUIRED]
        confirmation_text: Optional text describing the save action [OPTIONAL]
        statement_insights: Human-readable bullet-point insights [OPTIONAL]
        coverage_from: Earliest transaction date (ISO format YYYY-MM-DD) [REQUIRED]
        coverage_to: Latest transaction date (ISO format YYYY-MM-DD) [REQUIRED]
        profile: Household profile tag (e.g., "Me", "Partner", "Joint") [OPTIONAL]
        user_id: Optional user ID (uses test user if omitted)

    Returns:
        dict with saved summary count and details, or error if reconciliation fails
    """
    # Normalize profile (strip whitespace, None if empty)
    if profile:
        profile = profile.strip()
        if not profile:
            profile = None

    # Log tool call start
    started_at = logger.tool_call_start(
        "save_statement_summary",
        {
            "bank_name": bank_name,
            "user_id": user_id,
            "profile": profile,
            "category_summary_count": len(category_summaries) if category_summaries else 0,
            "statement_net_flow": statement_net_flow,
            "confirmation_text_len": len(confirmation_text) if confirmation_text else 0,
            "has_statement_insights": bool(statement_insights),
            "coverage_from": coverage_from,
            "coverage_to": coverage_to,
        }
    )

    db = SessionLocal()
    try:
        resolved_user_id = resolve_user_id(user_id)

        # Basic validation
        if not category_summaries:
            return _build_contract_error("No category summaries provided")

        if not bank_name:
            return _build_contract_error("bank_name is required")

        # ============================================================
        # BANK NAME VALIDATION - Prevent drift and duplications
        # ============================================================
        # Check if user has registered banks in their settings
        registered_banks, settings_exist = _get_registered_banks(db, resolved_user_id)
        
        if not settings_exist:
            # User hasn't completed onboarding - require settings first
            return {
                "structuredContent": {
                    "kind": "onboarding_required",
                    "error": "User settings not found. Complete onboarding first.",
                },
                "content": [{
                    "type": "text",
                    "text": (
                        "❌ ONBOARDING REQUIRED\n\n"
                        "Before saving statement summaries, the user must complete onboarding:\n"
                        "1. Call fetch_preferences(preference_type='settings') to check current state\n"
                        "2. Ask user which banks they use (e.g., 'I have Revolut, HSBC, and Santander')\n"
                        "3. Save via save_preferences(preference_type='settings', preferences=[{\n"
                        '     "registered_banks": ["Revolut", "HSBC", "Santander"],\n'
                        '     "functional_currency": "USD",\n'
                        '     "onboarding_complete": true\n'
                        "   }])\n\n"
                        "Only registered banks can be used with save_statement_summary."
                    )
                }]
            }
        
        if registered_banks:
            # Validate bank_name against registered banks
            is_valid_bank, canonical_bank_name = _validate_bank_name(bank_name, registered_banks)
            
            if not is_valid_bank:
                return {
                    "structuredContent": {
                        "kind": "bank_not_registered",
                        "provided_bank": bank_name,
                        "registered_banks": registered_banks,
                        "error": f"Bank '{bank_name}' is not registered.",
                    },
                    "content": [{
                        "type": "text",
                        "text": (
                            f"❌ BANK NOT REGISTERED\n\n"
                            f"The bank '{bank_name}' is not in the user's registered banks.\n\n"
                            f"Registered banks: {', '.join(registered_banks)}\n\n"
                            f"Options:\n"
                            f"1. Use one of the registered bank names (check for typos/casing)\n"
                            f"2. If this is a new bank, add it first via save_preferences:\n"
                            f"   save_preferences(preference_type='settings', preferences=[{{\n"
                            f'     "registered_banks": {registered_banks + [bank_name]}\n'
                            f"   }}])\n\n"
                            f"This prevents bank name drift (e.g., 'Revolut' vs 'revolut' vs 'REVOLUT')."
                        )
                    }]
                }
            
            # Use canonical bank name to prevent casing drift
            bank_name = canonical_bank_name

        # Check required fields for category summaries
        # transaction_count defaults to 0 if not provided
        # NOTE: Category-level insights REMOVED per issue #88 - only statement-level insights are used
        required_fields = ["category", "amount", "currency", "month_year"]
        for i, summary in enumerate(category_summaries):
            missing = [f for f in required_fields if f not in summary]
            if missing:
                return _build_contract_error(
                    f"Category summary {i+1} missing: {', '.join(missing)}"
                )

            # Validate category is in predefined list
            if summary["category"] not in PREDEFINED_CATEGORIES:
                return _build_contract_error(
                    f"Invalid category '{summary['category']}'. Must be one of: {', '.join(PREDEFINED_CATEGORIES)}"
                )

        if all(summary["category"] == "Other" for summary in category_summaries):
            return _build_contract_error(
                "Invalid categorization: all transactions summarized as 'Other'. Provide a breakdown across categories."
            )

        total_abs_amount = sum(abs(float(s["amount"])) for s in category_summaries)
        other_abs_amount = sum(
            abs(float(s["amount"]))
            for s in category_summaries
            if s["category"] == "Other"
        )
        other_ratio = (other_abs_amount / total_abs_amount) if total_abs_amount else 0.0
        has_non_other_non_zero = any(
            s["category"] != "Other" and abs(float(s["amount"])) > 0
            for s in category_summaries
        )

        if other_ratio > 0.6 and has_non_other_non_zero:
            categorization_rule_count = (
                db.query(CategorizationPreference)
                .filter(
                    CategorizationPreference.user_id == resolved_user_id,
                    CategorizationPreference.preference_type == "categorization",
                    CategorizationPreference.enabled.is_(True),
                )
                .count()
            )
            statement_count = (
                db.query(StatementPeriod)
                .filter(StatementPeriod.user_id == resolved_user_id)
                .count()
            )
            additional_preference_note = ""
            if categorization_rule_count < 10 and statement_count < 5:
                additional_preference_note = (
                    "\n- Consider strengthening categorization rules and adding more preferences. "
                    "Ask the user about the most material transactions, where they should be "
                    "categorized, and any other details needed."
                )

            message = (
                "Categorization rejected.\n\n"
                f"The category \"other\" is {other_ratio:.0%} of total.  Please consider the following:\n"
                "- Re-assess your categorization. Did you run the full workflow as per "
                "save_statement_summary tool contract?\n"
                "- Ensure the full vendor names and transaction descriptions are visible in the CSV (not vertically \n"
                "truncated). If not, fix it.\n"
                "- use Python-based fuzzy matching and/or regex to categorise based on preferences."
                f"{additional_preference_note}"
            )
            return _build_contract_error(message)

        # ============================================================
        # RECONCILIATION CHECK - Auto-validate category sum vs statement
        # ============================================================
        calculated_net_flow = sum(float(s["amount"]) for s in category_summaries)
        diff = abs(calculated_net_flow - statement_net_flow)

        # Use tolerance percentage with minimum threshold to avoid div-by-zero
        threshold = max(
            abs(statement_net_flow) * RECONCILIATION_TOLERANCE_PCT,
            MIN_RECONCILIATION_THRESHOLD
        )

        if diff > threshold:
            pct_diff = (diff / max(abs(statement_net_flow), 1.0)) * 100
            contract_text = (
                "Reconciliation failed.\n\n"
                f"{SAVE_STATEMENT_SUMMARY_CONTRACT_MESSAGE}"
            )
            detailed_text = (
                f"❌ RECONCILIATION FAILED\n\n"
                f"Categories sum: {calculated_net_flow:.2f}\n"
                f"User-provided transaction total: {statement_net_flow:.2f}\n"
                f"Difference: {diff:.2f} ({pct_diff:.1f}%)\n\n"
                f"Exceeds {RECONCILIATION_TOLERANCE_PCT * 100:.1f}% threshold. Please verify:\n"
                f"• Ask user to confirm their NET transaction total is correct\n"
                f"• Verify all transactions are categorized\n"
                f"• Check for missed or duplicate entries\n\n"
                f"Fix and resubmit.\n\n"
                f"{SAVE_STATEMENT_SUMMARY_CONTRACT_MESSAGE}"
            )
            return {
                "structuredContent": {
                    "kind": "reconciliation_error",
                    "calculated_net_flow": calculated_net_flow,
                    "statement_net_flow": statement_net_flow,
                    "difference": diff,
                    "threshold": threshold,
                    "percent_diff": pct_diff,
                    "error": contract_text,
                },
                "content": [{
                    "type": "text",
                    "text": detailed_text
                }]
            }

        # Enforce single statement context and required coverage window
        statement_months = {summary["month_year"] for summary in category_summaries}
        if len(statement_months) != 1:
            return _build_contract_error(
                "Multiple statement periods detected. All category summaries must share the same month_year so coverage can be stored at the statement level."
            )
        statement_month_year = statement_months.pop()

        if not coverage_from or not coverage_to:
            return _build_contract_error(
                "coverage_from and coverage_to are required. Provide coverage_from and coverage_to once for the statement (YYYY-MM-DD)."
            )

        try:
            coverage_from_date = date.fromisoformat(coverage_from)
            coverage_to_date = date.fromisoformat(coverage_to)
        except ValueError:
            return _build_contract_error("Invalid coverage date format. coverage_from and coverage_to must be YYYY-MM-DD.")

        if coverage_from_date > coverage_to_date:
            return _build_contract_error("coverage_from must be on or before coverage_to.")

        logger.info("Received category summaries", {
            "bank_name": bank_name,
            "category_count": len(category_summaries),
        })

        # Delete existing summaries for this statement period to ensure idempotency.
        # When a user reprocesses a statement (e.g., corrected data), we want to
        # replace the old summaries, not append to them. This matches the upsert
        # pattern used for StatementPeriod and StatementInsight.
        db.query(CategorySummary).filter(
            CategorySummary.user_id == resolved_user_id,
            CategorySummary.bank_name == bank_name,
            CategorySummary.month_year == statement_month_year
        ).delete(synchronize_session=False)

        # Upsert statement-level coverage window
        period = db.query(StatementPeriod).filter(
            StatementPeriod.user_id == resolved_user_id,
            StatementPeriod.bank_name == bank_name,
            StatementPeriod.month_year == statement_month_year
        ).first()

        if period:
            period.coverage_from = coverage_from_date
            period.coverage_to = coverage_to_date
            period.profile = profile
        else:
            new_period = StatementPeriod(
                user_id=resolved_user_id,
                bank_name=bank_name,
                month_year=statement_month_year,
                coverage_from=coverage_from_date,
                coverage_to=coverage_to_date,
                profile=profile,
            )
            db.add(new_period)

        # Save statement insights if provided (with redaction for privacy)
        if statement_insights and category_summaries:
            month_year = statement_month_year

            # Apply server-side redaction as defense in depth
            redacted_insights = redact_insights(statement_insights)

            # Validate and log if sensitive data detected after redaction
            is_safe, detected_patterns = validate_no_sensitive_data(redacted_insights)
            if not is_safe:
                logger.warn("Sensitive data patterns detected after redaction", {
                    "bank_name": bank_name,
                    "month_year": month_year,
                    "patterns": detected_patterns,
                })

            # Upsert statement insight with redacted content
            existing_insight = db.query(StatementInsight).filter(
                StatementInsight.user_id == resolved_user_id,
                StatementInsight.bank_name == bank_name,
                StatementInsight.month_year == month_year
            ).first()

            if existing_insight:
                existing_insight.content = redacted_insights
                existing_insight.profile = profile
            else:
                new_insight = StatementInsight(
                    user_id=resolved_user_id,
                    bank_name=bank_name,
                    month_year=month_year,
                    content=redacted_insights,
                    profile=profile,
                )
                db.add(new_insight)

        # Save category summaries directly (no aggregation needed)
        # NOTE: Category-level insights REMOVED per issue #88 - only statement-level insights are used
        saved_count = 0
        saved_summaries = []

        for summary_data in category_summaries:
            # Default transaction_count to 0 if not provided
            transaction_count = int(summary_data.get("transaction_count", 0))

            summary = CategorySummary(
                user_id=resolved_user_id,
                bank_name=bank_name,
                month_year=summary_data["month_year"],
                category=summary_data["category"],
                amount=float(summary_data["amount"]),
                currency=summary_data["currency"],
                transaction_count=transaction_count,
                profile=profile,  # Household profile tag
                insights=None,  # Category-level insights removed - use statement_insights instead
            )
            db.add(summary)
            saved_count += 1
            saved_summaries.append({
                "category": summary_data["category"],
                "amount": float(summary_data["amount"]),
                "count": transaction_count,
                "month": summary_data["month_year"],
                "profile": profile,
            })

        db.commit()

        logger.info("Category summaries saved", {
            "bank_name": bank_name,
            "saved": saved_count,
        })

        # Log successful completion
        logger.tool_call_end("save_statement_summary", started_at, {
            "bank_name": bank_name,
            "saved": saved_count,
        })

        # Get currency from first summary
        currency = category_summaries[0]["currency"] if category_summaries else "USD"

        # Return simple success response
        other_nudge = ""
        if other_ratio >= 0.4:
            categorization_rule_count = (
                db.query(CategorizationPreference)
                .filter(
                    CategorizationPreference.user_id == resolved_user_id,
                    CategorizationPreference.preference_type == "categorization",
                    CategorizationPreference.enabled.is_(True),
                )
                .count()
            )
            statement_count = (
                db.query(StatementPeriod)
                .filter(StatementPeriod.user_id == resolved_user_id)
                .count()
            )
            additional_preference_note = ""
            if categorization_rule_count < 10 and statement_count < 5:
                additional_preference_note = (
                    "\n- Consider strengthening categorization rules and adding more preferences. "
                    "Ask the user about the most material transactions, where they should be "
                    "categorized, and any other details needed."
                )

            other_nudge = (
                "\n\n"
                f"The category \"other\" is {other_ratio:.0%} of total.  Please consider the following:\n"
                "- Re-assess your categorization. Did you run the full workflow as per "
                "save_statement_summary tool contract?\n"
                "- Ensure the full vendor names and transaction descriptions are visible in the CSV (not vertically \n"
                "truncated). If not, fix it.\n"
                "- use Python-based fuzzy matching and/or regex to categorise based on preferences."
                f"{additional_preference_note}"
            )

        summary_list = "\n".join([
            f"  • {s['category']}: {currency} {s['amount']:.2f} ({s['count']} transactions)"
            for s in saved_summaries
        ])

        profile_text = f" [{profile}]" if profile else ""
        return {
            "structuredContent": {
                "kind": "save_result",
                "bank_name": bank_name,
                "profile": profile,
                "saved": saved_count,
                "summaries": saved_summaries,
                "other_category_ratio": other_ratio,
            },
            "content": [{
                "type": "text",
                "text": (
                    f"✓ Saved {saved_count} category summaries for {bank_name}{profile_text} "
                    f"({statement_month_year}):\n\n{summary_list}{other_nudge}"
                )
            }]
        }

    except Exception as e:
        # Log error
        logger.tool_call_error(
            "save_statement_summary",
            started_at,
            e,
            ErrorType.DB_ERROR if "database" in str(e).lower() else ErrorType.UNKNOWN_ERROR,
        )

        db.rollback()
        return _build_contract_error(
            f"Error saving category summaries: {str(e)}",
            structured_overrides={"kind": "error", "message": str(e)},
        )
    finally:
        db.close()
