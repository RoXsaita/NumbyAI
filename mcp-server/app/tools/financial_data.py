"""
UI Dashboard Tool - Category Summary Pivot Table Provider

This module provides category summary data in pivot table format for the dashboard widget.
It queries CategorySummary records and creates a pivot view with categories as rows and months as columns.

The widget receives raw pivot data and decides how to visualize it.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, Optional, List

from app.database import SessionLocal, CategorySummary, StatementInsight, StatementPeriod, Budget, CategorizationPreference, Transaction, resolve_user_id
from datetime import date
from app.logger import create_logger, ErrorType
from app.schemas.dashboard import (
    CoverageWindow,
    DashboardProps,
    InitialFilters,
    Metrics,
    PivotTable,
    SegmentMetric,
    Statement,
    TopVariance,
    CategorySummaryData,
    UserSettings,
)

# Create logger for this module
logger = create_logger("financial_data")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _decimal_to_float(value: Decimal | float | int | None) -> float:
    """Convert Decimal to float for JSON serialization."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _aggregate_transactions_to_summaries(
    transactions: List[Transaction],
    user_id: str
) -> List[CategorySummary]:
    """
    Aggregate transactions into CategorySummary-like objects for compatibility.
    
    This allows _build_dashboard_props to work with both Transaction and CategorySummary data.
    
    Args:
        transactions: List of Transaction objects
        user_id: User ID (for creating summary objects)
    
    Returns:
        List of CategorySummary-like objects (using CategorySummary model structure)
    """
    from collections import defaultdict
    
    # Group by bank_name, month_year, category, profile
    grouped = defaultdict(lambda: {
        'amount': Decimal('0'),
        'count': 0,
        'currency': 'USD',
        'profile': None
    })
    
    for tx in transactions:
        # Extract month_year from date
        month_year = tx.date.strftime('%Y-%m')
        key = (tx.bank_name, month_year, tx.category, tx.profile)
        
        grouped[key]['amount'] += Decimal(str(tx.amount))
        grouped[key]['count'] += 1
        grouped[key]['currency'] = tx.currency
        grouped[key]['profile'] = tx.profile
    
    # Convert to CategorySummary-like objects
    summaries = []
    for (bank_name, month_year, category, profile), data in grouped.items():
        # Create a minimal CategorySummary-like object
        # We'll use a simple object that has the same attributes
        class SummaryLike:
            def __init__(self):
                self.bank_name = bank_name
                self.month_year = month_year
                self.category = category
                self.amount = data['amount']
                self.currency = data['currency']
                self.transaction_count = data['count']
                self.profile = data['profile']
                self.insights = None
        
        summary = SummaryLike()
        summaries.append(summary)
    
    return summaries


# ============================================================================
# DATA AGGREGATION
# ============================================================================

INTERNAL_TRANSFER_KEYWORDS = (
    "transfer",
    "transfers",
    "cash",
    "savings",
)


def _get_budget_for_category(
    budget_lookup: Dict[str, Dict[str, float]],
    category: str,
    month: str,
) -> float:
    """
    Get budget for a category/month, falling back to default budget.
    
    Args:
        budget_lookup: Dict of {category: {month_year: amount, None: default_amount}}
        category: Category name
        month: Month in YYYY-MM format
    
    Returns:
        Budget amount (0.0 if no budget set)
    """
    if category not in budget_lookup:
        return 0.0
    cat_budgets = budget_lookup[category]
    # Try month-specific first, then default (None key)
    if month in cat_budgets:
        return cat_budgets[month]
    if None in cat_budgets:
        return cat_budgets[None]
    return 0.0


def _classify_category(name: str, total_amount: float) -> str:
    """Return inflows, outflows, or internal transfers classification."""
    lower = name.lower()
    if any(keyword in lower for keyword in INTERNAL_TRANSFER_KEYWORDS):
        return "internal_transfers"
    if total_amount >= 0:
        return "inflows"
    return "outflows"


def _build_dashboard_props(
    summaries: list[CategorySummary],
    bank_name: Optional[str],
    month_filter: Optional[str],
    initial_filters: Optional[InitialFilters] = None,
    statement_insights: Optional[str] = None,
    periods: Optional[list[StatementPeriod]] = None,
    budget_lookup: Optional[Dict[str, Dict[str, float]] | None] = None,
    available_months: Optional[List[str]] = None,
    available_banks: Optional[List[str]] = None,
    available_profiles: Optional[List[str]] = None,
    default_currency: str = "USD",
    user_settings: Optional[UserSettings] = None,
) -> DashboardProps:
    """Create the full dashboard payload from raw summaries."""
    # Handle empty summaries - return empty dashboard instead of raising error
    if not summaries:
        # Create empty dashboard structure
        empty_pivot = PivotTable(
            categories=[],
            months=[],
            actuals=[],
            budgets=[],
            transaction_counts=[],
            category_totals={},
            category_budget_totals={},
            month_totals={},
            month_budget_totals={},
            category_shares={},
            currency=default_currency,
        )
        
        empty_metrics = Metrics(
            inflows=0.0,
            outflows=0.0,
            internal_transfers=0.0,
            net_cash=0.0,
            budget_coverage_pct=0.0,
            latest_month=None,
            previous_month=None,
            month_over_month_delta=None,
            month_over_month_pct=None,
            segments=[],
            top_variances=[],
        )
        
        empty_statement = Statement(
            id="empty_dashboard",
            month="No data",
            bank=None,
            currency=default_currency,
        )
        
        empty_coverage = CoverageWindow(
            start=None,
            end=None,
        )
        
        return DashboardProps.create(
            statement=empty_statement,
            transactions=[],
            metrics=empty_metrics,
            pivot=empty_pivot,
            currency=default_currency,
            banks=available_banks or [],
            coverage=empty_coverage,
            initial_filters=initial_filters,
            statement_insights=statement_insights,
            category_summaries=[],
            available_months=available_months or [],
            available_banks=available_banks or [],
            available_profiles=available_profiles or [],
            user_settings=user_settings,
        )

    pivot_data: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    pivot_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    all_months = set()
    actual_months = set()  # Months with actual transaction data (not budget-only)
    all_categories = set()
    banks = set()
    currency = summaries[0].currency or "USD"

    category_summaries: List[CategorySummaryData] = []

    for summary in summaries:
        category = summary.category
        month = summary.month_year
        amount = _decimal_to_float(summary.amount)
        count = int(summary.transaction_count)

        pivot_data[category][month] += amount
        pivot_counts[category][month] += count
        all_months.add(month)
        actual_months.add(month)  # Track months with actual data
        all_categories.add(category)
        banks.add(summary.bank_name)

        category_summaries.append(
            CategorySummaryData(
                category=category,
                month=month,
                bank=summary.bank_name,
                amount=amount,
                count=count,
                profile=summary.profile,
                insights=summary.insights,
            )
        )

    # Include months that have budget data but no actual summaries
    # This ensures budget-only months appear in the dashboard
    # NOTE: These are NOT added to actual_months to avoid affecting latest_month calculation
    if budget_lookup:
        for category, month_budgets in budget_lookup.items():
            # Include category if it has any budget data (default or month-specific)
            all_categories.add(category)
            for month_year in month_budgets.keys():
                # Only add specific months to all_months (skip None/default budgets)
                if month_year is not None:
                    all_months.add(month_year)

    coverage_start = None
    coverage_end = None
    relevant_periods = []
    if periods:
        relevant_periods = [
            period for period in periods
            if period.bank_name in banks and period.month_year in all_months
        ]
        for period in relevant_periods:
            if coverage_start is None or period.coverage_from < coverage_start:
                coverage_start = period.coverage_from
            if coverage_end is None or period.coverage_to > coverage_end:
                coverage_end = period.coverage_to

    sorted_months = sorted(all_months)
    sorted_banks = sorted(banks)

    raw_rows: Dict[str, Dict[str, Any]] = {}
    month_totals = {month: 0.0 for month in sorted_months}
    month_budget_totals = {month: 0.0 for month in sorted_months}

    for category in all_categories:
        row_data: List[float] = []
        row_counts: List[int] = []
        for month in sorted_months:
            amount = round(pivot_data[category].get(month, 0.0), 2)
            count = pivot_counts[category].get(month, 0)
            row_data.append(amount)
            row_counts.append(count)

        total_amount = round(sum(row_data), 2)
        # Get budget for each month from budget_lookup, or use 0 if not set
        row_budget = []
        for month in sorted_months:
            if budget_lookup:
                budget_val = _get_budget_for_category(budget_lookup, category, month)
            else:
                budget_val = 0.0
            row_budget.append(round(budget_val, 2))
        budget_total = round(sum(row_budget), 2)

        for idx, month in enumerate(sorted_months):
            month_totals[month] += row_data[idx]
            month_budget_totals[month] += row_budget[idx]

        raw_rows[category] = {
            "actuals": row_data,
            "counts": row_counts,
            "budget": row_budget,
            "total": total_amount,
            "budget_total": budget_total,
        }

    sorted_categories = sorted(
        raw_rows.keys(),
        key=lambda key: abs(raw_rows[key]["total"]),
        reverse=True,
    )

    data_matrix = []
    budget_matrix = []
    counts_matrix = []
    category_totals: Dict[str, float] = {}
    category_budget_totals: Dict[str, float] = {}

    for category in sorted_categories:
        row = raw_rows[category]
        data_matrix.append(row["actuals"])
        budget_matrix.append(row["budget"])
        counts_matrix.append(row["counts"])
        category_totals[category] = row["total"]
        category_budget_totals[category] = row["budget_total"]

    classification_map = {
        cat: _classify_category(cat, category_totals[cat])
        for cat in sorted_categories
    }

    expense_total_abs = sum(
        abs(category_totals[cat])
        for cat in sorted_categories
        if category_totals[cat] < 0 and classification_map[cat] == "outflows"
    )
    category_shares = {
        cat: round(
            (abs(category_totals[cat]) / expense_total_abs * 100), 2
        ) if expense_total_abs and category_totals[cat] < 0 and classification_map[cat] == "outflows" else 0.0
        for cat in sorted_categories
    }

    segment_actual_totals = {
        "inflows": sum(
            category_totals[cat]
            for cat in sorted_categories
            if classification_map[cat] == "inflows"
        ),
        "outflows": sum(
            category_totals[cat]
            for cat in sorted_categories
            if classification_map[cat] == "outflows"
        ),
        "internal_transfers": sum(
            category_totals[cat]
            for cat in sorted_categories
            if classification_map[cat] == "internal_transfers"
        ),
    }
    segment_budget_totals = {
        "inflows": sum(
            category_budget_totals[cat]
            for cat in sorted_categories
            if classification_map[cat] == "inflows"
        ),
        "outflows": sum(
            category_budget_totals[cat]
            for cat in sorted_categories
            if classification_map[cat] == "outflows"
        ),
        "internal_transfers": sum(
            category_budget_totals[cat]
            for cat in sorted_categories
            if classification_map[cat] == "internal_transfers"
        ),
    }

    def _segment_metric(name: str) -> SegmentMetric:
        actual_signed = segment_actual_totals.get(name, 0.0)
        budget_signed = segment_budget_totals.get(name, 0.0)
        actual = abs(actual_signed)
        budget = abs(budget_signed)
        variance = actual - budget
        variance_pct = round((variance / budget * 100), 2) if budget else 0.0
        return SegmentMetric(
            name=name,
            actual=round(actual, 2),
            budget=round(budget, 2),
            variance=round(variance, 2),
            variance_pct=variance_pct,
        )

    segments = [_segment_metric(name) for name in ("inflows", "outflows", "internal_transfers")]

    inflows = round(max(segment_actual_totals["inflows"], 0.0), 2)
    outflows = round(abs(segment_actual_totals["outflows"]), 2)
    internal_transfers = round(abs(segment_actual_totals["internal_transfers"]), 2)
    net_cash = round(
        segment_actual_totals["inflows"]
        + segment_actual_totals["outflows"]
        + segment_actual_totals["internal_transfers"],
        2,
    )

    # Use actual_months (months with real transactions) for latest/previous month calculation
    # This avoids picking budget-only months as the "latest" month
    sorted_actual_months = sorted(actual_months)
    latest_month = sorted_actual_months[-1] if sorted_actual_months else None
    previous_month = sorted_actual_months[-2] if len(sorted_actual_months) > 1 else None
    month_over_month_delta = None
    month_over_month_pct = None
    if latest_month and previous_month:
        latest_value = month_totals[latest_month]
        previous_value = month_totals[previous_month]
        month_over_month_delta = round(latest_value - previous_value, 2)
        if previous_value:
            month_over_month_pct = round(
                month_over_month_delta / abs(previous_value) * 100,
                2,
            )

    expense_budget_abs = abs(segment_budget_totals.get("outflows", 0.0))
    budget_coverage_pct = (
        round(outflows / expense_budget_abs * 100, 2)
        if expense_budget_abs
        else 0.0
    )

    variance_records: List[TopVariance] = []
    for category in sorted_categories:
        classification = classification_map[category]
        if classification == "internal_transfers":
            continue
        row = raw_rows[category]
        actual_total = row["total"]
        budget_total = row["budget_total"]
        if classification == "outflows":
            actual_abs = abs(actual_total)
            budget_abs = abs(budget_total)
            variance_value = round(actual_abs - budget_abs, 2)
            variance_pct = round(
                (variance_value / budget_abs * 100), 2
            ) if budget_abs else 0.0
            direction = "over" if actual_abs > budget_abs else "under"
        else:
            variance_value = round(actual_total - budget_total, 2)
            budget_abs = abs(budget_total)
            variance_pct = round(
                (variance_value / budget_abs * 100), 2
            ) if budget_abs else 0.0
            direction = "over" if actual_total > budget_total else "under"
        variance_records.append(
            TopVariance(
                category=category,
                actual=round(actual_total, 2),
                budget=round(budget_total, 2),
                variance=variance_value,
                variance_pct=variance_pct,
                direction=direction,
            )
        )

    top_variances = sorted(
        variance_records,
        key=lambda var: abs(var.variance),
        reverse=True,
    )[:5]

    pivot_table = PivotTable(
        categories=sorted_categories,
        months=sorted_months,
        actuals=data_matrix,
        budgets=budget_matrix,
        transaction_counts=counts_matrix,
        category_totals={
            cat: round(category_totals[cat], 2) for cat in sorted_categories
        },
        category_budget_totals={
            cat: round(category_budget_totals[cat], 2) for cat in sorted_categories
        },
        month_totals={month: round(month_totals[month], 2) for month in sorted_months},
        month_budget_totals={
            month: round(month_budget_totals[month], 2) for month in sorted_months
        },
        category_shares=category_shares,
        currency=currency,
    )

    metrics = Metrics(
        inflows=inflows,
        outflows=outflows,
        internal_transfers=internal_transfers,
        net_cash=net_cash,
        budget_coverage_pct=budget_coverage_pct,
        latest_month=latest_month,
        previous_month=previous_month,
        month_over_month_delta=month_over_month_delta,
        month_over_month_pct=month_over_month_pct,
        segments=segments,
        top_variances=top_variances,
    )

    statement_month = (
        month_filter
        if month_filter
        else (latest_month if len(sorted_months) == 1 else "Multi-period")
    )
    statement = Statement(
        id=f"pivot_{summaries[0].id}",
        month=statement_month or "Multi-period",
        bank=bank_name or (sorted_banks[0] if sorted_banks else None),
        currency=currency,
    )

    coverage = CoverageWindow(
        start=coverage_start.isoformat() if coverage_start else None,
        end=coverage_end.isoformat() if coverage_end else None,
    )

    return DashboardProps.create(
        statement=statement,
        transactions=[],
        metrics=metrics,
        pivot=pivot_table,
        currency=currency,
        banks=list(sorted_banks),
        coverage=coverage,
        initial_filters=initial_filters,
        statement_insights=statement_insights,
        category_summaries=category_summaries,
        available_months=available_months or list(sorted_months),
        available_banks=available_banks or list(sorted_banks),
        available_profiles=available_profiles or [],
        user_settings=user_settings,
    )

# ============================================================================
# MAIN HANDLER
# ============================================================================

def get_financial_data_handler(
    user_id: Optional[str] = None,
    bank_name: Optional[str] = None,
    month_year: Optional[str] = None,
    categories: Optional[List[str]] = None,
    profile: Optional[str] = None,
    tab: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch category summaries and return filtered financial data.

    Args:
        user_id: Optional user ID (defaults to test user)
        bank_name: Optional filter by bank name
        month_year: Optional filter by specific month (YYYY-MM)
        categories: Optional list of categories to include
        profile: Optional household profile filter (e.g., "Me", "Partner", "Joint")
        tab: Optional tab to show (if "overview", defaults to "journey")

    Returns:
        Dict with:
        - structuredContent: Filtered financial data for AI
        - _meta: Full dashboard data for widget
        - content: Text response for ChatGPT
    """
    # Normalize profile
    if profile:
        profile = profile.strip()
        if not profile:
            profile = None

    # Handle tab parameter: if "overview" is specified, default to "journey"
    if tab and tab.strip().lower() == "overview":
        tab = "journey"
    
    # Track if any filters are applied
    has_filters = bool(bank_name or month_year or categories or profile)
    # Only statement-level filters (bank or month) should trigger insight fetching
    has_statement_scope = bool(bank_name or month_year or profile)
    
    # Log tool call start
    started_at = logger.tool_call_start(
        "get_financial_data",
        {"user_id": user_id, "bank_name": bank_name, "month_year": month_year, "categories": categories, "profile": profile},
    )

    db = SessionLocal()
    try:
        resolved_user_id = resolve_user_id(user_id)

        logger.debug("Fetching category summaries from database", {
            "user_id": resolved_user_id,
            "bank_name": bank_name,
            "month_year": month_year,
            "categories": categories,
            "profile": profile,
        })

        # =====================================================================
        # FETCH DATA: Try Transaction table first, fall back to CategorySummary
        # =====================================================================
        
        # Try to fetch from Transaction table first
        all_transactions = db.query(Transaction).filter(
            Transaction.user_id == resolved_user_id
        ).all()
        
        # If we have transactions, aggregate them
        if all_transactions:
            logger.info("Using Transaction table for aggregation", {
                "transaction_count": len(all_transactions)
            })
            all_summaries = _aggregate_transactions_to_summaries(all_transactions, resolved_user_id)
            
            # Apply filters to transactions before aggregation
            filtered_transactions_query = db.query(Transaction).filter(
                Transaction.user_id == resolved_user_id
            )
            if bank_name:
                filtered_transactions_query = filtered_transactions_query.filter(Transaction.bank_name == bank_name)
            if month_year:
                # Filter by date range for the month
                year, month = map(int, month_year.split('-'))
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                date_from = date(year, month, 1)
                date_to = date(year, month, last_day)
                filtered_transactions_query = filtered_transactions_query.filter(
                    Transaction.date >= date_from,
                    Transaction.date <= date_to
                )
            if categories:
                filtered_transactions_query = filtered_transactions_query.filter(Transaction.category.in_(categories))
            if profile:
                filtered_transactions_query = filtered_transactions_query.filter(Transaction.profile == profile)
            
            filtered_transactions = filtered_transactions_query.all()
            filtered_summaries = _aggregate_transactions_to_summaries(filtered_transactions, resolved_user_id) if filtered_transactions else []
        else:
            # Fall back to CategorySummary table
            logger.info("Falling back to CategorySummary table", {
                "user_id": resolved_user_id
            })
            all_summaries = db.query(CategorySummary).filter(
                CategorySummary.user_id == resolved_user_id
            ).all()
            
            # Fetch FILTERED summaries for structuredContent (AI payload)
            filtered_query = db.query(CategorySummary).filter(
                CategorySummary.user_id == resolved_user_id
            )
            if bank_name:
                filtered_query = filtered_query.filter(CategorySummary.bank_name == bank_name)
            if month_year:
                filtered_query = filtered_query.filter(CategorySummary.month_year == month_year)
            if categories:
                filtered_query = filtered_query.filter(CategorySummary.category.in_(categories))
            if profile:
                filtered_query = filtered_query.filter(CategorySummary.profile == profile)
            filtered_summaries = filtered_query.all()
        
        # Collect available profiles from all summaries
        available_profiles = set()
        for s in all_summaries:
            if s.profile:
                available_profiles.add(s.profile)
        
        # Fetch ALL periods (unfiltered) for widget
        all_periods = db.query(StatementPeriod).filter(
            StatementPeriod.user_id == resolved_user_id
        ).all()
        
        # Fetch FILTERED periods for AI coverage window
        filtered_periods_query = db.query(StatementPeriod).filter(
            StatementPeriod.user_id == resolved_user_id
        )
        if bank_name:
            filtered_periods_query = filtered_periods_query.filter(StatementPeriod.bank_name == bank_name)
        if month_year:
            filtered_periods_query = filtered_periods_query.filter(StatementPeriod.month_year == month_year)
        if profile:
            filtered_periods_query = filtered_periods_query.filter(StatementPeriod.profile == profile)
        filtered_periods = filtered_periods_query.all()

        # Fetch user budgets
        budget_query = db.query(Budget).filter(Budget.user_id == resolved_user_id)
        all_budgets = budget_query.all()
        
        # Build budget lookup: {category: {month_year: amount, None: default}}
        budget_lookup: Dict[str, Dict[str, float]] = {}
        for b in all_budgets:
            if b.category not in budget_lookup:
                budget_lookup[b.category] = {}
            # month_year can be None (default budget) or specific month
            key = b.month_year  # None for default, "YYYY-MM" for specific
            budget_lookup[b.category][key] = _decimal_to_float(b.amount)
        
        # Fetch user's functional currency from settings (for empty dashboard)
        # Also fetch actual user settings for progression tracking (without defaults)
        default_currency = "USD"  # Default fallback
        user_settings = None
        settings_pref = (
            db.query(CategorizationPreference)
            .filter(
                CategorizationPreference.user_id == resolved_user_id,
                CategorizationPreference.preference_type == "settings",
                CategorizationPreference.name == "user_settings",
                CategorizationPreference.enabled.is_(True)
            )
            .first()
        )
        if settings_pref and settings_pref.rule:
            settings_dict = settings_pref.rule
            # Get currency for display (with default)
            default_currency = settings_dict.get("functional_currency", "USD")
            
            # Build user_settings object - only include fields that are actually set (not defaulted)
            user_settings_dict = {}
            if "functional_currency" in settings_dict:
                user_settings_dict["functional_currency"] = settings_dict["functional_currency"]
            if "bank_accounts_count" in settings_dict:
                user_settings_dict["bank_accounts_count"] = settings_dict["bank_accounts_count"]
            if "registered_banks" in settings_dict:
                user_settings_dict["registered_banks"] = settings_dict["registered_banks"]
            if "profiles" in settings_dict:
                user_settings_dict["profiles"] = settings_dict["profiles"]
            if "onboarding_complete" in settings_dict:
                user_settings_dict["onboarding_complete"] = settings_dict["onboarding_complete"]
            
            # Only create UserSettings object if we have at least one field
            if user_settings_dict:
                user_settings = UserSettings(**user_settings_dict)

        # Collect available months and banks from ALL summaries (for widget dropdowns)
        available_months_set = set()
        available_banks_set = set()
        for s in all_summaries:
            if s.month_year:
                available_months_set.add(s.month_year)
            if s.bank_name:
                available_banks_set.add(s.bank_name)
        
        # Also include months that have budget data
        for category, month_budgets in budget_lookup.items():
            for m in month_budgets.keys():
                if m is not None:
                    available_months_set.add(m)
        
        available_months = sorted(available_months_set)
        available_banks = sorted(available_banks_set)

        # Prepare initial filters and fetch statement insights
        # Always set initial_filters to include default_tab
        # Default to 'journey' tab when no parameters are provided or if tab is "overview"
        default_tab_value = None
        if not has_filters and not tab:
            # No filters and no tab specified: default to journey
            default_tab_value = 'journey'
        elif tab:
            # Tab explicitly specified: use it (already handled "overview" -> "journey" above)
            default_tab_value = tab.strip().lower() if tab else None
        
        initial_filters = InitialFilters(
            bank_name=bank_name if bank_name else None,
            month_year=month_year if month_year else None,
            profile=profile if profile else None,
            default_tab=default_tab_value,
        )
        statement_insights = None
        
        # Fetch statement insights - ALWAYS for widget, filtered for specific requests
        # When no filters: fetch ALL insights so dashboard shows highlights by default
        insight_query = db.query(StatementInsight).filter(
            StatementInsight.user_id == resolved_user_id
        ).order_by(StatementInsight.month_year.desc())  # Most recent first
        
        if has_statement_scope:
            # Apply filters when specific bank/month/profile requested
            if bank_name:
                insight_query = insight_query.filter(StatementInsight.bank_name == bank_name)
            if month_year:
                insight_query = insight_query.filter(StatementInsight.month_year == month_year)
            if profile:
                insight_query = insight_query.filter(StatementInsight.profile == profile)
        
        stmt_insights = insight_query.all()
        if stmt_insights:
            # Format insights with month headers for clarity when multiple months
            if len(stmt_insights) > 1 and not month_year:
                # Group by month when showing all insights
                insight_parts = []
                for si in stmt_insights:
                    month_label = si.month_year or "Unknown"
                    bank_label = f" ({si.bank_name})" if si.bank_name else ""
                    insight_parts.append(f"## {month_label}{bank_label}\n{si.content}")
                statement_insights = "\n\n".join(insight_parts)
            else:
                # Single insight or filtered - show directly
                statement_insights = "\n\n---\n\n".join([si.content for si in stmt_insights])

        # Log if no data found, but continue to build empty dashboard
        if not all_summaries:
            logger.info("No category summaries found - returning empty dashboard", {
                "user_id": resolved_user_id,
                "bank_name": bank_name,
                "month_year": month_year,
            })
        
        # Check if filtered query returned any results
        # Even if filter doesn't match, we still build the full dashboard for _meta
        # so the widget can render and let users change filters
        filter_no_match = has_filters and not filtered_summaries
        if filter_no_match:
            filter_desc_items = []
            if bank_name:
                filter_desc_items.append(f"bank={bank_name}")
            if month_year:
                filter_desc_items.append(f"month={month_year}")
            if categories:
                filter_desc_items.append(f"categories={categories}")
            if profile:
                filter_desc_items.append(f"profile={profile}")
            logger.warn("No summaries match the filter", {"filters": filter_desc_items})

        logger.info("Fetched category summaries", {
            "all_count": len(all_summaries),
            "filtered_count": len(filtered_summaries) if has_filters else len(all_summaries),
        })

        # =====================================================================
        # BUILD WIDGET PAYLOAD (_meta): Contains ALL data, widget filters client-side
        # =====================================================================
        dashboard_props = _build_dashboard_props(
            all_summaries,  # Use ALL summaries (empty list if no data)
            bank_name=None,  # No filter for widget data
            month_filter=None,  # No filter for widget data
            initial_filters=initial_filters,  # Tell widget which month/bank/profile to display initially
            statement_insights=statement_insights,
            periods=all_periods,  # All periods for full coverage
            budget_lookup=budget_lookup if all_summaries else None,  # Only include budgets if we have data
            available_months=available_months,
            available_banks=available_banks,
            available_profiles=sorted(list(available_profiles)),
            default_currency=default_currency,
            user_settings=user_settings,
        )
        pivot_table = dashboard_props.pivot

        logger.info("Widget pivot table created", {
            "categories": len(pivot_table.categories),
            "months": len(pivot_table.months),
            "banks": len(dashboard_props.banks),
        })

        # Build full payload for widget (_meta) - do this BEFORE checking filter_no_match
        # so we can include it in the response even when filter doesn't match
        full_payload = dashboard_props.model_dump()
        full_payload["summary_count"] = len(all_summaries)

        # =====================================================================
        # HANDLE FILTER NO MATCH: Return error with dashboard still available
        # =====================================================================
        if filter_no_match:
            filter_desc_items = []
            if bank_name:
                filter_desc_items.append(f"bank={bank_name}")
            if month_year:
                filter_desc_items.append(f"month={month_year}")
            if categories:
                filter_desc_items.append(f"categories={categories}")
            
            # Return error message but INCLUDE _meta so widget can still render
            return {
                "structuredContent": {
                    "kind": "error",
                    "message": f"No data found for filter: {', '.join(filter_desc_items)}",
                },
                "_meta": full_payload,  # Widget can still render with full data
                "content": [
                    {
                        "type": "text",
                        "text": f"No category summaries found for the specified filter ({', '.join(filter_desc_items)}). The dashboard is showing all available data.",
                    }
                ],
            }

        # =====================================================================
        # BUILD AI PAYLOAD (structuredContent): Strictly filtered data only
        # =====================================================================
        # Use filtered_summaries if filters applied, otherwise all_summaries
        ai_summaries = filtered_summaries if has_filters else all_summaries
        ai_periods = filtered_periods if has_filters else all_periods
        
        # Build filtered dashboard for AI (no budgets to avoid adding extra months)
        ai_dashboard = _build_dashboard_props(
            ai_summaries,
            bank_name=bank_name,
            month_filter=month_year,
            initial_filters=None,  # Not needed for AI
            statement_insights=None,  # Added separately below
            periods=ai_periods,
            budget_lookup=None,  # Don't include budgets - keeps data clean
            available_months=None,
            available_banks=None,
            default_currency=default_currency,
            user_settings=user_settings,
        )
        ai_metrics = ai_dashboard.metrics
        ai_pivot = ai_dashboard.pivot

        # Log successful completion
        logger.tool_call_end("get_financial_data", started_at, {
            "all_summaries": len(all_summaries),
            "filtered_summaries": len(ai_summaries),
            "ai_months": len(ai_pivot.months),
            "has_filters": has_filters,
        })

        # Create summary text from FILTERED data
        filter_desc = []
        if bank_name:
            filter_desc.append(f"bank: {bank_name}")
        if month_year:
            filter_desc.append(f"month: {month_year}")
        if categories:
            filter_desc.append(f"categories: {', '.join(categories)}")
        filter_context = f" (filtered by {', '.join(filter_desc)})" if filter_desc else ""
        
        # Handle empty data case
        if not ai_summaries:
            summary_text = "Dashboard is ready, but no financial data has been saved yet.\n\n"
            summary_text += "To get started:\n"
            summary_text += "1. Use fetch_preferences to check your settings and get onboarding guidance\n"
            summary_text += "2. Save your first bank statement using save_statement_summary\n"
            summary_text += "3. The dashboard will automatically update with your data\n\n"
            summary_text += f"Your functional currency is set to: {default_currency}"
        else:
            summary_text = f"Financial data{filter_context}:\n"
            summary_text += f"  • {len(ai_pivot.categories)} categories\n"
            summary_text += f"  • {len(ai_pivot.months)} month(s): {', '.join(ai_pivot.months) if ai_pivot.months else 'None'}\n"
            summary_text += f"  • {len(ai_dashboard.banks)} bank(s): {', '.join(ai_dashboard.banks) if ai_dashboard.banks else 'None'}\n"
            summary_text += f"  • Total inflows: {ai_pivot.currency} {ai_metrics.inflows:,.2f}\n"
            summary_text += f"  • Total outflows: {ai_pivot.currency} {ai_metrics.outflows:,.2f}\n"
            summary_text += f"  • Net cash: {ai_pivot.currency} {ai_metrics.net_cash:,.2f}\n"
            
            if statement_insights:
                summary_text += f"\nInsights:\n{statement_insights}"

        # full_payload already built above (before filter_no_match check)
        
        # =====================================================================
        # CREATE LIGHTWEIGHT AI PAYLOAD: Strictly filtered, minimal fields
        # =====================================================================
        model_payload = {
            "statement": {
                "id": ai_dashboard.statement.id,
                "month": month_year or ai_metrics.latest_month or "Multi-period",
                "bank": bank_name or (ai_dashboard.banks[0] if ai_dashboard.banks else None),
                "currency": ai_dashboard.currency,
            },
            # Simplified metrics - only for the filtered period
            "metrics": {
                "inflows": ai_metrics.inflows,
                "outflows": ai_metrics.outflows,
                "internal_transfers": ai_metrics.internal_transfers,
                "net_cash": ai_metrics.net_cash,
                # Only include month-over-month if we have multiple months in filtered data
                **({"month_over_month_delta": ai_metrics.month_over_month_delta,
                    "month_over_month_pct": ai_metrics.month_over_month_pct}
                   if len(ai_pivot.months) > 1 else {}),
            },
            # Coverage window for filtered data only
            "coverage": {
                "start": ai_dashboard.coverage.start,
                "end": ai_dashboard.coverage.end,
            },
            "banks": list(ai_dashboard.banks),
            "currency": ai_dashboard.currency,
            "summary_count": len(ai_summaries),
            # Include statement insights for AI to reference
            "statement_insights": statement_insights,
            # Lightweight pivot summary - strictly filtered
            "pivot_summary": {
                "categories": list(ai_pivot.categories),
                "months": list(ai_pivot.months),
                "category_totals": ai_pivot.category_totals,
                "month_totals": ai_pivot.month_totals,
            }
        }

        return {
            "structuredContent": model_payload,
            "_meta": full_payload,
            "content": [
                {
                    "type": "text",
                    "text": summary_text,
                }
            ],
        }

    except Exception as e:
        # Log error
        logger.tool_call_error(
            "get_financial_data",
            started_at,
            e,
            ErrorType.DB_ERROR if "database" in str(e).lower() else ErrorType.UNKNOWN_ERROR,
        )
        raise

    finally:
        db.close()
