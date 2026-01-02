"""Database models and session management"""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Column, String, Numeric, Date, DateTime, ForeignKey, Index, UniqueConstraint,
    create_engine, Boolean, Integer, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings
from app.logger import create_logger

logger = create_logger("database")

Base = declarative_base()

# Test user configuration
TEST_USER_EMAIL = "test@local.dev"
TEST_USER_NAME = "Test User"


def _utc_now():
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

# Use String for SQLite, UUID for PostgreSQL
def UUIDColumn():
    """Return appropriate UUID column type based on database"""
    if settings.database_url.startswith("sqlite"):
        return Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    else:
        return Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

def UUIDForeignKey(foreign_key):
    """Return appropriate UUID foreign key column type based on database"""
    if settings.database_url.startswith("sqlite"):
        return Column(String(36), ForeignKey(foreign_key), nullable=False, index=True)
    else:
        return Column(PostgresUUID(as_uuid=True), ForeignKey(foreign_key), nullable=False, index=True)


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = UUIDColumn()
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_utc_now, nullable=False)

    # Relationships
    category_summaries = relationship("CategorySummary", back_populates="user", cascade="all, delete-orphan")
    statement_insights = relationship("StatementInsight", back_populates="user", cascade="all, delete-orphan")
    statement_periods = relationship("StatementPeriod", back_populates="user", cascade="all, delete-orphan")
    categorization_preferences = relationship("CategorizationPreference", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    categorization_rules = relationship("CategorizationRule", back_populates="user", cascade="all, delete-orphan")
    # DEPRECATED: keeping for backward compatibility during migration
    parsing_instructions = relationship("ParsingInstruction", back_populates="user", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="user", cascade="all, delete-orphan")


class CategorySummary(Base):
    """Category summary model - stores aggregated transaction data per bank/month/category"""
    __tablename__ = "category_summaries"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    bank_name = Column(String(100), nullable=False, index=True)
    month_year = Column(String(7), nullable=False, index=True)  # YYYY-MM format
    category = Column(String(100), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)  # Total amount for this category
    currency = Column(String(3), nullable=False)  # ISO currency code
    transaction_count = Column(Numeric, nullable=False)  # Number of transactions in this category
    profile = Column(String(50), nullable=True, index=True)  # Household profile (e.g., "Me", "Partner", "Joint")
    # DEPRECATED: Category-level insights removed per issue #88 - use StatementInsight instead
    # Keeping column for backward compatibility with existing data, but new saves set NULL
    insights = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="category_summaries")

    __table_args__ = (
        Index("idx_summaries_user_month", "user_id", "month_year"),
        Index("idx_summaries_user_bank_month", "user_id", "bank_name", "month_year"),
        Index("idx_summaries_user_category", "user_id", "category"),
        Index("idx_summaries_user_profile", "user_id", "profile"),
        # Allow same bank/month/category to be added multiple times (list-based)
        # This enables adding summaries over time with additional fields
    )


class StatementPeriod(Base):
    """Statement-level coverage window"""
    __tablename__ = "statement_periods"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    bank_name = Column(String(100), nullable=False, index=True)
    month_year = Column(String(7), nullable=False, index=True)  # YYYY-MM format
    coverage_from = Column(Date, nullable=False)
    coverage_to = Column(Date, nullable=False)
    profile = Column(String(50), nullable=True, index=True)  # Household profile (e.g., "Me", "Partner", "Joint")
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="statement_periods")

    __table_args__ = (
        Index("idx_stmt_period_user_bank_month", "user_id", "bank_name", "month_year", unique=True),
        Index("idx_stmt_period_user_profile", "user_id", "profile"),
    )


class StatementInsight(Base):
    """Statement insight model - stores high-level analysis of a specific statement"""
    __tablename__ = "statement_insights"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    bank_name = Column(String(100), nullable=False, index=True)
    month_year = Column(String(7), nullable=False, index=True)  # YYYY-MM format
    content = Column(String, nullable=False)  # Markdown content
    profile = Column(String(50), nullable=True, index=True)  # Household profile (e.g., "Me", "Partner", "Joint")
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="statement_insights")

    __table_args__ = (
        Index("idx_stmt_insight_user_bank_month", "user_id", "bank_name", "month_year", unique=True),
        Index("idx_stmt_insight_user_profile", "user_id", "profile"),
    )


class CategorizationPreference(Base):
    """Unified preference model for categorization rules and parsing instructions"""
    __tablename__ = "categorization_preferences"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    bank_name = Column(String(100), nullable=True, index=True)  # NULL = global rule (for categorization)
    name = Column(String(200), nullable=False)  # Human-readable rule/instruction name
    rule = Column(JSON, nullable=False)  # Structured rule or parsing instruction definition
    priority = Column(Integer, default=0, nullable=False)  # Higher = higher priority
    enabled = Column(Boolean, default=True, nullable=False)
    preference_type = Column(String(20), nullable=False, default="categorization")  # "categorization" or "parsing"
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="categorization_preferences")

    __table_args__ = (
        Index("idx_cat_pref_user_bank", "user_id", "bank_name"),
        Index("idx_cat_pref_user_priority", "user_id", "priority"),
        Index("idx_cat_pref_user_type", "user_id", "preference_type"),
    )


class Budget(Base):
    """Budget model - stores user-defined budget targets per category/month
    
    NOTE: The unique index on (user_id, category, month_year) does NOT prevent
    multiple rows with NULL month_year due to SQL NULL semantics (NULL != NULL).
    The save_budget handler must explicitly check for existing NULL values
    before inserting new default budgets.
    """
    __tablename__ = "budgets"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    category = Column(String(100), nullable=False, index=True)
    month_year = Column(String(7), nullable=True, index=True)  # YYYY-MM format, NULL = default budget
    amount = Column(Numeric(12, 2), nullable=False)  # Budget target amount (positive for expenses)
    currency = Column(String(3), nullable=False, default="USD")
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="budgets")

    __table_args__ = (
        # NOTE: This unique index does NOT prevent multiple NULLs for month_year.
        # Application code in save_budget.py handles this explicitly.
        Index("idx_budget_user_category_month", "user_id", "category", "month_year", unique=True),
        Index("idx_budget_user_category", "user_id", "category"),
    )


class ParsingInstruction(Base):
    """DEPRECATED: Parsing instruction model - keeping for backward compatibility"""
    __tablename__ = "parsing_instructions"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    bank_name = Column(String(100), nullable=False, index=True)
    file_format = Column(String(20), nullable=False, index=True)  # pdf, csv, xlsx, other
    instructions = Column(String, nullable=False)  # Markdown instructions
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="parsing_instructions")

    __table_args__ = (
        Index("idx_parsing_instr_user_bank_format", "user_id", "bank_name", "file_format", unique=True),
    )


class Insight(Base):
    """Insight model - DEPRECATED: keeping for backward compatibility during migration"""
    __tablename__ = "insights"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    title = Column(String(500), nullable=False, index=True)  # Short title/summary
    period = Column(String(7), nullable=True, index=True)  # Optional YYYY-MM for monthly insights
    insight_type = Column(String(50), nullable=False, index=True)  # spending_pattern, categorization_preference, transaction_detail, monthly_summary, general
    content = Column(String, nullable=False)  # Markdown content
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="insights")

    __table_args__ = (
        Index("idx_insights_user_type", "user_id", "insight_type"),
        Index("idx_insights_user_period", "user_id", "period"),
        Index("idx_insights_title", "title"),
    )


class Transaction(Base):
    """Transaction model - stores individual transaction records"""
    __tablename__ = "transactions"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    date = Column(Date, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    merchant = Column(String(200), nullable=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)  # Negative for expenses, positive for income
    currency = Column(String(3), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    bank_name = Column(String(100), nullable=False, index=True)
    statement_period_id = UUIDForeignKey("statement_periods.id")
    profile = Column(String(50), nullable=True, index=True)  # Household profile (e.g., "Me", "Partner", "Joint")
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="transactions")
    statement_period = relationship("StatementPeriod")

    __table_args__ = (
        Index("idx_transactions_user_date", "user_id", "date"),
        Index("idx_transactions_user_category", "user_id", "category"),
        Index("idx_transactions_user_merchant", "user_id", "merchant"),
        Index("idx_transactions_user_bank_date", "user_id", "bank_name", "date"),
    )


class CategorizationRule(Base):
    """Categorization rule model - stores learned merchant → category mappings"""
    __tablename__ = "categorization_rules"

    id = UUIDColumn()
    user_id = UUIDForeignKey("users.id")
    merchant_pattern = Column(String(200), nullable=False)  # Regex or exact match pattern
    category = Column(String(100), nullable=False)
    confidence_score = Column(Integer, default=1, nullable=False)  # Number of times matched
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="categorization_rules")

    __table_args__ = (
        Index("idx_cat_rules_user_merchant", "user_id", "merchant_pattern"),
        Index("idx_cat_rules_user_enabled", "user_id", "enabled"),
    )


# Database engine and session
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_or_create_test_user() -> str:
    """
    Get or create a test user for local development.
    
    Returns:
        str: User ID (UUID as string for SQLite compatibility)
    """
    db = SessionLocal()
    try:
        test_user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
        
        if not test_user:
            test_user = User(
                email=TEST_USER_EMAIL,
                name=TEST_USER_NAME
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        
        return str(test_user.id)
    finally:
        db.close()


def resolve_user_id(user_id: str | None = None, require_auth: bool = False) -> str:
    """
    Resolve and validate a user_id.
    
    For multi-user support: if require_auth is True, user_id must be provided and valid.
    Otherwise, falls back to test user for development.
    
    Args:
        user_id: Optional user ID string to validate
        require_auth: If True, user_id is required and must exist (no test user fallback)
        
    Returns:
        str: Valid user ID
        
    Raises:
        ValueError: If require_auth is True and user_id is None or invalid
    """
    # If no user_id provided
    if not user_id:
        if require_auth:
            raise ValueError("User ID is required but not provided")
        return get_or_create_test_user()
    
    user_id_str = str(user_id)
    
    # Validate that this user_id exists in the database
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.id == user_id_str).first()
        if existing_user:
            return user_id_str
        else:
            # User doesn't exist
            if require_auth:
                raise ValueError(f"User ID {user_id_str} does not exist")
            # Fall back to test user for development
            logger.warn("User ID not found, falling back to test user", {"user_id": user_id_str})
            return get_or_create_test_user()
    finally:
        db.close()
