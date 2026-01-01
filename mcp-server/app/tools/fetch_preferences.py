"""Unified tool to fetch preferences (settings, categorization rules, or parsing instructions)"""
from collections import defaultdict
from typing import Optional, List, Dict, Any, Literal, Union

from app.database import CategorizationPreference, CategorySummary, Budget, SessionLocal, resolve_user_id
from app.logger import create_logger, ErrorType
from app.tools.phase_instructions import (
    determine_user_phase,
    get_phase_instructions,
    get_phase_metadata,
    PHASE_METADATA,
)

logger = create_logger("fetch_preferences")

PreferenceType = Literal["categorization", "parsing", "settings", "list"]

# Settings preference name constant (only one settings record per user)
SETTINGS_PREFERENCE_NAME = "user_settings"


async def fetch_preferences_handler(
    preference_type: Union[PreferenceType, List[PreferenceType]] = "categorization",
    bank_name: Optional[str] = None,
    user_id: Optional[str] = None
) -> dict:
    """
    Fetch preferences based on type(s).

    Args:
        preference_type: Type(s) of preferences to fetch (can be single string or list):
            - "settings": Returns user settings (functional currency, onboarding status)
            - "categorization": Returns categorization rules for transaction categorization
            - "parsing": Returns parsing instructions for bank statements
            - "list": Returns summary of all available preferences (no full details)
            - ["settings", "categorization"]: Fetch multiple types at once
        bank_name: Optional filter by bank name (useful for parsing preferences)
        user_id: Optional user ID (defaults to test user)

    Returns:
        dict with preferences based on type(s). If multiple types requested, returns combined response.
    """
    started_at = logger.tool_call_start(
        "fetch_preferences",
        {"preference_type": preference_type, "bank_name": bank_name, "user_id": user_id}
    )

    db = SessionLocal()
    try:
        resolved_user_id = resolve_user_id(user_id)

        # Handle multiple preference types
        if isinstance(preference_type, list):
            return await _fetch_multiple_preferences(db, resolved_user_id, preference_type, bank_name, started_at)

        # Handle single preference type
        if preference_type == "settings":
            return await _fetch_user_settings(db, resolved_user_id, started_at)
        elif preference_type == "list":
            return await _fetch_list_summary(db, resolved_user_id, started_at)
        elif preference_type == "parsing":
            return await _fetch_parsing_preferences(db, resolved_user_id, bank_name, started_at)
        else:  # categorization (default)
            return await _fetch_categorization_preferences(db, resolved_user_id, bank_name, started_at)

    except Exception as e:
        logger.tool_call_error(
            "fetch_preferences",
            started_at,
            e,
            ErrorType.DB_ERROR if "database" in str(e).lower() else ErrorType.UNKNOWN_ERROR,
        )

        db.rollback()
        return {
            "structuredContent": {
                "kind": "error",
                "message": str(e),
            },
            "content": [{"type": "text", "text": f"Error fetching preferences: {str(e)}"}]
        }
    finally:
        db.close()


async def _fetch_user_settings(db, user_id: str, started_at) -> dict:
    """Fetch user settings with contextual guidance based on database state."""
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

    # Build data overview regardless of settings status
    data_overview = await _build_data_overview(db, user_id)
    total_months = data_overview.get("total_months", 0)
    
    # Check for categorization and parsing preferences
    cat_count = db.query(CategorizationPreference).filter(
        CategorizationPreference.user_id == user_id,
        CategorizationPreference.preference_type == "categorization",
        CategorizationPreference.enabled.is_(True)
    ).count()
    
    parsing_count = db.query(CategorizationPreference).filter(
        CategorizationPreference.user_id == user_id,
        CategorizationPreference.preference_type == "parsing",
        CategorizationPreference.enabled.is_(True)
    ).count()

    logger.tool_call_end("fetch_preferences", started_at, {
        "mode": "settings",
        "found": settings_pref is not None,
        "data_overview_banks": len(data_overview.get("banks", [])),
        "total_months": total_months
    })

    # === CASE 1: Empty database - brand new user ===
    if not settings_pref and not data_overview.get("banks") and cat_count == 0 and parsing_count == 0:
        # New users get the beginner phase personality
        phase = "beginner"
        phase_metadata = get_phase_metadata(phase)
        phase_instructions = get_phase_instructions(phase)
        
        workflow_text = (
            "Welcome! I'm your Finance Tutor, here to help get you started with NumbyAI and prepare you for your financial mastery journey."
            "This app helps you track your income andspending, set budgets, and gain insights into your financial habits. "
            "To get started, explore the dashboard and follow your journey path. "
            "You'll need to ask me to generate the dashboard whenever you want to see your financial overview - something like: show me the dashboard."
            "The app will guide you through each step—look for the journey milestones and the '?' help icons for detailed instructions. "
            "The App is designed to guide you step by step through the process and gives example prompts (that you will need to tweak based on your profile) for each step.\n\n"
            "---\n" + phase_instructions
        )
        return {
            "structuredContent": {
                "kind": "user_settings",
                "settings": None,
                "onboarding_complete": False,
                "data_overview": data_overview,
                "phase": phase,
                "phase_metadata": phase_metadata,
                "ai_instructions": workflow_text,
            },
            "content": [{"type": "text", "text": workflow_text}]
        }

    # === CASE 2: No settings but has some data (edge case) ===
    if not settings_pref:
        phase = "beginner"
        phase_metadata = get_phase_metadata(phase)
        phase_instructions = get_phase_instructions(phase)
        
        guidance_text = (
            "SETTINGS MISSING - Complete onboarding.\n"
            "1. Ask user: 'Which banks do you use?' (e.g., 'I have Revolut, HSBC, Santander')\n"
            "2. Ask user for functional_currency (ISO 4217: USD, EUR, GBP).\n"
            "3. Save via save_preferences(preference_type='settings', preferences=[{\n"
            '     "registered_banks": ["Revolut", "HSBC", "Santander"],\n'
            '     "functional_currency": "USD",\n'
            '     "onboarding_complete": true\n'
            "   }])\n"
            "IMPORTANT: Only registered banks can be used with save_statement_summary.\n\n"
            "---\n" + phase_instructions
        )
        return {
            "structuredContent": {
                "kind": "user_settings",
                "settings": None,
                "onboarding_complete": False,
                "data_overview": data_overview,
                "phase": phase,
                "phase_metadata": phase_metadata,
                "ai_instructions": guidance_text,
            },
            "content": [{"type": "text", "text": guidance_text}]
        }

    # Extract settings from the rule field
    settings = settings_pref.rule or {}
    # Only get functional_currency if it's actually set (not defaulted)
    functional_currency = settings.get("functional_currency")  # None if not set
    bank_accounts_count = settings.get("bank_accounts_count")
    onboarding_complete = settings.get("onboarding_complete", False)
    profiles = settings.get("profiles", [])
    registered_banks = settings.get("registered_banks", [])
    
    # For display/guidance purposes, use USD as default, but don't include in settings dict
    functional_currency_display = functional_currency or "USD"

    # === CASE 3: Settings exist but onboarding not complete ===
    if not onboarding_complete:
        phase = "beginner"
        phase_metadata = get_phase_metadata(phase)
        phase_instructions = get_phase_instructions(phase)
        
        # Check if banks are registered
        banks_note = ""
        if not registered_banks:
            banks_note = (
                "MISSING: Ask user 'Which banks do you use?' and save registered_banks. "
                "Only registered banks can be used with save_statement_summary.\n"
            )
        else:
            banks_note = f"Registered banks: {', '.join(registered_banks)}.\n"
        
        guidance_text = (
            f"ONBOARDING INCOMPLETE - Currency: {functional_currency_display}.\n"
            f"{banks_note}"
            "Ask user for first bank statement (CSV/Excel) + NET transaction total. "
            "After saving, update onboarding_complete to true via save_preferences.\n\n"
            "---\n" + phase_instructions
        )
        # Build settings dict - only include functional_currency if actually set
        settings_dict = {
            "bank_accounts_count": bank_accounts_count,
            "registered_banks": registered_banks,
            "profiles": profiles,
            "onboarding_complete": False,
        }
        if functional_currency is not None:
            settings_dict["functional_currency"] = functional_currency
        
        return {
            "structuredContent": {
                "kind": "user_settings",
                "settings": settings_dict,
                "onboarding_complete": False,
                "data_overview": data_overview,
                "phase": phase,
                "phase_metadata": phase_metadata,
                "ai_instructions": guidance_text,
            },
            "content": [{"type": "text", "text": guidance_text}]
        }

    # === CASE 4: Fully onboarded user - use AI personality phase system ===
    # Build settings dict - only include functional_currency if actually set
    settings_dict = {
        "bank_accounts_count": bank_accounts_count,
        "registered_banks": registered_banks,
        "profiles": profiles,
        "onboarding_complete": True,
    }
    if functional_currency is not None:
        settings_dict["functional_currency"] = functional_currency

    # Build context strings for guidance
    banks_with_data = ", ".join(b["name"] for b in data_overview.get("banks", []))
    date_range = data_overview.get("date_range", {})
    range_str = f" ({date_range.get('from')} to {date_range.get('to')})" if date_range else ""
    budget_count = data_overview.get("budgets_configured", 0)

    # Determine AI personality phase based on user data
    phase = determine_user_phase(total_months=total_months, budgets_configured=budget_count)
    phase_metadata = get_phase_metadata(phase)
    phase_instructions = get_phase_instructions(phase)
    
    # Build context-aware guidance combining phase personality with current state
    registered_banks_str = ", ".join(registered_banks) if registered_banks else "None"
    context_header = (
        f"USER CONTEXT: {total_months} month(s) saved. "
        f"Registered banks: {registered_banks_str}. "
        f"Banks with data: {banks_with_data}{range_str}. "
        f"Budgets: {budget_count}.\n\n"
    )
    
    # Combine phase personality instructions with context
    ai_instructions = context_header + phase_instructions

    return {
        "structuredContent": {
            "kind": "user_settings",
            "settings": settings_dict,
            "onboarding_complete": True,
            "data_overview": data_overview,
            "phase": phase,
            "phase_metadata": phase_metadata,
            "ai_instructions": ai_instructions,
        },
        "content": [{"type": "text", "text": ai_instructions}]
    }


async def _fetch_multiple_preferences(
    db, 
    user_id: str, 
    preference_types: List[PreferenceType],
    bank_name: Optional[str],
    started_at
) -> dict:
    """Fetch multiple preference types at once and combine results."""
    results = {}
    all_content_parts = []
    
    # Deduplicate and validate types
    unique_types = list(dict.fromkeys(preference_types))  # Preserve order while removing dupes
    
    # Fetch each type
    for pref_type in unique_types:
        if pref_type == "settings":
            result = await _fetch_user_settings(db, user_id, started_at)
            results["settings"] = result.get("structuredContent")
            all_content_parts.append(f"Settings: {result['content'][0]['text']}")
        elif pref_type == "list":
            result = await _fetch_list_summary(db, user_id, started_at)
            results["list"] = result.get("structuredContent")
            all_content_parts.append(f"Summary: {result['content'][0]['text']}")
        elif pref_type == "parsing":
            result = await _fetch_parsing_preferences(db, user_id, bank_name, started_at)
            results["parsing"] = result.get("structuredContent")
            all_content_parts.append(f"Parsing: {result['content'][0]['text']}")
        elif pref_type == "categorization":
            result = await _fetch_categorization_preferences(db, user_id, bank_name, started_at)
            results["categorization"] = result.get("structuredContent")
            all_content_parts.append(f"Categorization: {result['content'][0]['text']}")
    
    logger.tool_call_end("fetch_preferences", started_at, {
        "mode": "multiple",
        "types": unique_types,
        "count": len(unique_types)
    })
    
    # Build combined response
    combined_text = "\n\n".join(all_content_parts)
    
    return {
        "structuredContent": {
            "kind": "multiple_preferences",
            "types_fetched": unique_types,
            "results": results,
        },
        "content": [{
            "type": "text",
            "text": f"Fetched {len(unique_types)} preference type(s):\n\n{combined_text}"
        }]
    }


async def _build_data_overview(db, user_id: str) -> dict:
    """Build a detailed overview of user's saved data."""
    # Get all category summaries for this user
    summaries = db.query(CategorySummary).filter(
        CategorySummary.user_id == user_id
    ).all()
    
    if not summaries:
        return {
            "banks": [],
            "total_months": 0,
            "date_range": None,
            "categories_used": [],
            "budgets_configured": 0,
            "profiles_in_use": [],
        }
    
    # Aggregate bank data
    bank_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "months": set(),
        "profiles": set(),
    })
    all_months = set()
    all_categories = set()
    all_profiles = set()
    
    for s in summaries:
        bank_data[s.bank_name]["months"].add(s.month_year)
        if s.profile:
            bank_data[s.bank_name]["profiles"].add(s.profile)
            all_profiles.add(s.profile)
        all_months.add(s.month_year)
        all_categories.add(s.category)
    
    # Count budgets
    budget_count = db.query(Budget).filter(Budget.user_id == user_id).count()
    
    # Build banks array
    banks_list = []
    for bank_name, data in sorted(bank_data.items()):
        banks_list.append({
            "name": bank_name,
            "months": len(data["months"]),
            "profiles": sorted(list(data["profiles"])),
        })
    
    # Calculate date range
    sorted_months = sorted(all_months)
    date_range = None
    if sorted_months:
        date_range = {
            "from": sorted_months[0],
            "to": sorted_months[-1],
        }
    
    return {
        "banks": banks_list,
        "total_months": len(all_months),
        "date_range": date_range,
        "categories_used": sorted(list(all_categories)),
        "budgets_configured": budget_count,
        "profiles_in_use": sorted(list(all_profiles)),
    }


async def _fetch_list_summary(db, user_id: str, started_at) -> dict:
    """Return summary of available preferences without full details."""
    # Get settings
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
    
    # Get counts by type
    categorization_prefs = (
        db.query(CategorizationPreference)
        .filter(
            CategorizationPreference.user_id == user_id,
            CategorizationPreference.enabled.is_(True),
            CategorizationPreference.preference_type == "categorization"
        )
        .all()
    )
    
    parsing_prefs = (
        db.query(CategorizationPreference)
        .filter(
            CategorizationPreference.user_id == user_id,
            CategorizationPreference.enabled.is_(True),
            CategorizationPreference.preference_type == "parsing"
        )
        .all()
    )

    # Build settings summary
    settings_data = settings_pref.rule if settings_pref else None
    functional_currency = settings_data.get("functional_currency") if settings_data else None
    onboarding_complete = settings_data.get("onboarding_complete", False) if settings_data else False

    # Build categorization summary
    cat_global = sum(1 for p in categorization_prefs if p.bank_name is None)
    cat_bank_specific = [p for p in categorization_prefs if p.bank_name is not None]
    cat_banks = list(set(p.bank_name for p in cat_bank_specific))

    # Build parsing summary (group by bank)
    parsing_banks = list(set(p.bank_name for p in parsing_prefs if p.bank_name))

    summary = {
        "settings": {
            "configured": settings_pref is not None,
            "functional_currency": functional_currency,
            "onboarding_complete": onboarding_complete,
        },
        "categorization": {
            "total": len(categorization_prefs),
            "global_rules": cat_global,
            "bank_specific_rules": len(cat_bank_specific),
            "banks": cat_banks,
        },
        "parsing": {
            "total": len(parsing_prefs),
            "banks": parsing_banks,
        }
    }

    logger.tool_call_end("fetch_preferences", started_at, {"mode": "list"})

    # Build human-readable summary
    text_parts = []
    if settings_pref:
        text_parts.append(f"Settings: Functional currency {functional_currency or 'not set'}, onboarding {'complete' if onboarding_complete else 'incomplete'}")
    else:
        text_parts.append("Settings: Not configured (onboarding needed)")
    
    if summary["categorization"]["total"]:
        text_parts.append(f"Categorization: {summary['categorization']['total']} rules ({cat_global} global, {len(cat_bank_specific)} bank-specific)")
    else:
        text_parts.append("Categorization: No rules saved")
    
    if summary["parsing"]["banks"]:
        text_parts.append(f"Parsing: Instructions for {', '.join(parsing_banks)}")
    else:
        text_parts.append("Parsing: No bank instructions saved")

    return {
        "structuredContent": {
            "kind": "preferences_summary",
            "summary": summary,
        },
        "content": [{
            "type": "text",
            "text": "Available preferences:\n• " + "\n• ".join(text_parts)
        }]
    }


async def _fetch_categorization_preferences(db, user_id: str, bank_name: Optional[str], started_at) -> dict:
    """Fetch categorization rules."""
    query = (
        db.query(CategorizationPreference)
        .filter(
            CategorizationPreference.user_id == user_id,
            CategorizationPreference.enabled.is_(True),
            CategorizationPreference.preference_type == "categorization"
        )
    )
    
    # Optional bank filter
    if bank_name:
        query = query.filter(
            (CategorizationPreference.bank_name == bank_name) | 
            (CategorizationPreference.bank_name.is_(None))
        )
    
    preferences = (
        query.order_by(
            CategorizationPreference.bank_name.is_(None),
            CategorizationPreference.priority.desc()
        )
        .all()
    )

    result_preferences: List[Dict[str, Any]] = []
    for pref in preferences:
        result_preferences.append({
            "id": str(pref.id),
            "name": pref.name,
            "bank_name": pref.bank_name,
            "rule": pref.rule,
            "priority": pref.priority,
        })

    logger.tool_call_end("fetch_preferences", started_at, {
        "mode": "categorization",
        "count": len(result_preferences)
    })

    if not result_preferences:
        return {
            "structuredContent": {
                "kind": "categorization_preferences",
                "preferences": [],
                "count": 0,
            },
            "content": [{
                "type": "text",
                "text": "No categorization preferences found. Categorize transactions manually."
            }]
        }

    # Build concise summary
    global_count = sum(1 for p in result_preferences if p["bank_name"] is None)
    bank_specific = [p for p in result_preferences if p["bank_name"] is not None]
    bank_names = list(set(p["bank_name"] for p in bank_specific))

    summary_parts = []
    if global_count:
        summary_parts.append(f"{global_count} global")
    if bank_names:
        summary_parts.append(f"{len(bank_specific)} bank-specific ({', '.join(bank_names)})")

    return {
        "structuredContent": {
            "kind": "categorization_preferences",
            "preferences": result_preferences,
            "count": len(result_preferences),
        },
        "content": [{
            "type": "text",
            "text": f"Loaded {len(result_preferences)} categorization rules: {', '.join(summary_parts)}. Apply these rules when categorizing."
        }]
    }


async def _fetch_parsing_preferences(db, user_id: str, bank_name: Optional[str], started_at) -> dict:
    """Fetch parsing instructions for bank statements, including user's functional currency."""
    # First, get user's functional currency from settings
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
    
    functional_currency = None
    if settings_pref and settings_pref.rule:
        functional_currency = settings_pref.rule.get("functional_currency")
    
    # Now get parsing preferences
    query = (
        db.query(CategorizationPreference)
        .filter(
            CategorizationPreference.user_id == user_id,
            CategorizationPreference.enabled.is_(True),
            CategorizationPreference.preference_type == "parsing"
        )
    )
    
    # Filter by bank name if provided
    if bank_name:
        query = query.filter(CategorizationPreference.bank_name == bank_name)
    
    preferences = query.order_by(CategorizationPreference.updated_at.desc()).all()

    result_preferences: List[Dict[str, Any]] = []
    for pref in preferences:
        result_preferences.append({
            "id": str(pref.id),
            "name": pref.name,
            "bank_name": pref.bank_name,
            "instructions": pref.rule,  # Rule field contains parsing instructions
            "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
        })

    logger.tool_call_end("fetch_preferences", started_at, {
        "mode": "parsing",
        "count": len(result_preferences),
        "bank_name": bank_name,
        "functional_currency": functional_currency
    })

    # Build currency conversion note
    currency_note = ""
    if functional_currency:
        currency_note = f" Convert all amounts to {functional_currency} (user's functional currency)."

    if not result_preferences:
        bank_msg = f" for {bank_name}" if bank_name else ""
        return {
            "structuredContent": {
                "kind": "parsing_preferences",
                "preferences": [],
                "count": 0,
                "bank_name": bank_name,
                "functional_currency": functional_currency,
            },
            "content": [{
                "type": "text",
                "text": f"No parsing instructions found{bank_msg}. Parse the statement and document your approach after processing.{currency_note}"
            }]
        }

    # Build summary
    banks = list(set(p["bank_name"] for p in result_preferences if p["bank_name"]))
    bank_summary = f" for {', '.join(banks)}" if banks else ""

    return {
        "structuredContent": {
            "kind": "parsing_preferences",
            "preferences": result_preferences,
            "count": len(result_preferences),
            "bank_name": bank_name,
            "functional_currency": functional_currency,
        },
        "content": [{
            "type": "text",
            "text": f"Loaded {len(result_preferences)} parsing instruction(s){bank_summary}. Follow these steps when parsing this bank's statements.{currency_note}"
        }]
    }


# Backward compatibility alias
async def fetch_categorization_preferences_handler(
    user_id: Optional[str] = None
) -> dict:
    """Backward-compatible wrapper - calls fetch_preferences with categorization type."""
    return await fetch_preferences_handler(
        preference_type="categorization",
        user_id=user_id
    )
