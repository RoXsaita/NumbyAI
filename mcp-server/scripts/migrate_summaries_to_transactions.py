"""
Migration script to convert CategorySummary records to Transaction placeholders

Note: Since CategorySummary only contains aggregated data, we can only create
placeholder transactions. Real transaction data will come from new statement uploads.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, CategorySummary, Transaction, User
from app.logger import create_logger
from datetime import datetime
from decimal import Decimal

logger = create_logger("migration")


def migrate_summaries_to_transactions():
    """Convert CategorySummary records to Transaction placeholders"""
    db = SessionLocal()
    
    try:
        # Get all category summaries
        summaries = db.query(CategorySummary).all()
        
        logger.info("Starting migration", {"summary_count": len(summaries)})
        
        migrated_count = 0
        
        for summary in summaries:
            # Parse month_year to get date range
            try:
                year, month = map(int, summary.month_year.split('-'))
                # Use first day of month as transaction date
                tx_date = datetime(year, month, 1).date()
            except (ValueError, AttributeError):
                logger.warn("Invalid month_year format", {
                    "summary_id": str(summary.id),
                    "month_year": summary.month_year
                })
                continue
            
            # Create a placeholder transaction
            # Since we don't have individual transaction details, create one placeholder
            # with the total amount
            transaction = Transaction(
                user_id=summary.user_id,
                date=tx_date,
                description=f"Migrated from CategorySummary: {summary.category}",
                merchant=None,
                amount=summary.amount,
                currency=summary.currency,
                category=summary.category,
                bank_name=summary.bank_name,
                statement_period_id=None,  # Can't link to period without more info
                profile=summary.profile,
            )
            
            db.add(transaction)
            migrated_count += 1
        
        db.commit()
        logger.info("Migration completed", {"migrated_count": migrated_count})
        
        return migrated_count
        
    except Exception as e:
        db.rollback()
        logger.error("Migration failed", {"error": str(e)})
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Migrating CategorySummary records to Transaction placeholders...")
    count = migrate_summaries_to_transactions()
    print(f"Migration complete: {count} transactions created")
