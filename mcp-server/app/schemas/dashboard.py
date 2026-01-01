"""
Dashboard Data Schema - Pydantic Models

This module defines Pydantic models that mirror the Zod schema in
shared/schemas/dashboard.schema.ts, ensuring consistent data contracts
between the Python MCP server and TypeScript widgets.

Key principles:
1. Server sends RAW data (transactions, metrics), not UI structure
2. Widget controls visualization
3. Runtime validation on both server and client
4. Single source of truth for data contract
"""

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ============================================================================
# TRANSACTION SCHEMA
# ============================================================================

class Transaction(BaseModel):
    """Individual transaction record"""
    id: str
    transaction_date: str  # ISO 8601 date string
    description: str
    amount: float  # Positive = inflow, Negative = outflow
    currency: str
    category: str

    # Optional fields
    merchant: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    class Config:
        # Allow arbitrary types for DB model conversion
        from_attributes = True


# ============================================================================
# STATEMENT SCHEMA
# ============================================================================

class Statement(BaseModel):
    """Statement metadata"""
    id: str
    month: str  # e.g., "2024-01" or "January 2024"
    bank: Optional[str] = None
    currency: str

    # Optional fields
    account_number: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None

    class Config:
        from_attributes = True


# ============================================================================
# METRICS SCHEMA
# ============================================================================

class CategoryBreakdown(BaseModel):
    """Category breakdown (spending by category)"""
    category: str
    amount: float  # Total absolute value
    count: int     # Number of transactions
    percentage: Optional[float] = None  # % of total spending


class DailyTotal(BaseModel):
    """Daily aggregated data for time series"""
    date: str  # ISO 8601 date
    inflows: float
    outflows: float
    net: float


class CoverageWindow(BaseModel):
    """Overall data coverage window"""
    start: Optional[str] = None
    end: Optional[str] = None


class PivotTable(BaseModel):
    """Pivot table structure with budgets"""
    categories: List[str]
    months: List[str]
    actuals: List[List[float]]
    budgets: List[List[float]]
    transaction_counts: List[List[int]]
    category_totals: Dict[str, float]
    category_budget_totals: Dict[str, float]
    month_totals: Dict[str, float]
    month_budget_totals: Dict[str, float]
    category_shares: Dict[str, float]
    currency: str


class SegmentMetric(BaseModel):
    """Inflows/outflows/internal transfer metrics"""
    name: Literal['inflows', 'outflows', 'internal_transfers']
    actual: float
    budget: float
    variance: float
    variance_pct: float


class TopVariance(BaseModel):
    """Top variance highlight"""
    category: str
    actual: float
    budget: float
    variance: float
    variance_pct: float
    direction: Literal['over', 'under']


class InitialFilters(BaseModel):
    """Initial filters for the dashboard widget"""
    bank_name: Optional[str] = None
    month_year: Optional[str] = None
    profile: Optional[str] = None  # Household profile filter (e.g., "Me", "Partner", "Joint")
    default_tab: Optional[str] = None  # Default tab to show (e.g., "journey", "overview", "cashflow")


class Metrics(BaseModel):
    """Computed metrics for the dashboard"""
    inflows: float
    outflows: float
    internal_transfers: float
    net_cash: float
    budget_coverage_pct: float
    latest_month: Optional[str] = None
    previous_month: Optional[str] = None
    month_over_month_delta: Optional[float] = None
    month_over_month_pct: Optional[float] = None
    segments: List[SegmentMetric] = Field(default_factory=list)
    top_variances: List[TopVariance] = Field(default_factory=list)


class CategorySummaryData(BaseModel):
    """Minimal category summary data for client-side filtering"""
    category: str
    month: str
    bank: str
    amount: float
    count: int
    profile: Optional[str] = None  # Household profile (e.g., "Me", "Partner", "Joint")
    # DEPRECATED: Category-level insights removed per issue #88 - use statement_insights instead
    # Keeping field for backward compatibility with existing data, but new saves set null
    insights: Optional[str] = None


class UserSettings(BaseModel):
    """User settings for progression tracking (only includes actually set values, not defaults)"""
    functional_currency: Optional[str] = None
    bank_accounts_count: Optional[int] = None
    registered_banks: Optional[List[str]] = None
    profiles: Optional[List[str]] = None
    onboarding_complete: Optional[bool] = None


# ============================================================================
# DASHBOARD PROPS SCHEMA (Main Contract)
# ============================================================================

class DashboardProps(BaseModel):
    """
    Complete dashboard data passed from server to widget

    This is the single source of truth for the data contract.
    The MCP tool returns this structure, and the widget receives it.
    """
    kind: Literal['dashboard'] = 'dashboard'
    generated_at: str  # ISO 8601 timestamp

    # Core data
    statement: Statement
    transactions: List[Transaction] = Field(default_factory=list)
    metrics: Metrics
    pivot: PivotTable
    category_summaries: List[CategorySummaryData] = Field(default_factory=list)

    # Context
    currency: str
    banks: List[str]
    coverage: CoverageWindow
    
    # Available filter options (always contains ALL options regardless of current filter)
    # These allow users to change filters even when AI requested filtered data
    available_months: List[str] = Field(default_factory=list)
    available_banks: List[str] = Field(default_factory=list)
    available_profiles: List[str] = Field(default_factory=list)  # Household profiles in use
    
    # New fields for widget initialization and insights
    initial_filters: Optional[InitialFilters] = None
    statement_insights: Optional[str] = None
    
    # User settings for progression tracking (only includes actually set values, not defaults)
    user_settings: Optional[UserSettings] = None

    # Optional metadata
    version: Optional[str] = '2.0.0'

    @classmethod
    def create(
        cls,
        statement: Statement,
        transactions: List[Transaction],
        metrics: Metrics,
        pivot: PivotTable,
        currency: str,
        banks: List[str],
        coverage: CoverageWindow,
        initial_filters: Optional[InitialFilters] = None,
        statement_insights: Optional[str] = None,
        category_summaries: List[CategorySummaryData] = [],
        available_months: List[str] = [],
        available_banks: List[str] = [],
        available_profiles: List[str] = [],
        user_settings: Optional[UserSettings] = None,
    ) -> "DashboardProps":
        """Factory method to create DashboardProps with auto-generated timestamp"""
        return cls(
            kind='dashboard',
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            statement=statement,
            transactions=transactions,
            metrics=metrics,
            pivot=pivot,
            currency=currency,
            banks=banks,
            coverage=coverage,
            available_months=available_months,
            available_banks=available_banks,
            available_profiles=available_profiles,
            initial_filters=initial_filters,
            statement_insights=statement_insights,
            category_summaries=category_summaries,
            user_settings=user_settings,
            version='2.3.0',  # Bump version for profile support
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_dashboard_props(data: dict) -> DashboardProps:
    """
    Validate and parse dashboard props

    Raises:
        pydantic.ValidationError: If data doesn't match schema
    """
    return DashboardProps(**data)
