"""
Statement Analyzer - Reverse engineer statement structure using Cursor Agent

This service uses Cursor Agent to analyze bank statement CSV files and
interactively determine their structure through Q&A with the user.
"""
import pandas as pd
from typing import Dict, Optional
from app.services.cursor_agent_service import analyze_statement_structure
from app.database import SessionLocal, CategorizationPreference
from app.logger import create_logger

logger = create_logger("statement_analyzer")


def check_existing_parsing_preferences(bank_name: str, user_id: str) -> Optional[Dict]:
    """
    Check if parsing preferences exist for this bank.
    
    Args:
        bank_name: Bank name to check
        user_id: User ID
    
    Returns:
        Parsing schema dict if found, None otherwise
    """
    db = SessionLocal()
    try:
        pref = db.query(CategorizationPreference).filter(
            CategorizationPreference.user_id == user_id,
            CategorizationPreference.bank_name == bank_name,
            CategorizationPreference.preference_type == "parsing",
            CategorizationPreference.enabled.is_(True)
        ).first()
        
        if pref and pref.rule:
            logger.info("Found existing parsing preferences", {
                "bank_name": bank_name,
                "user_id": user_id
            })
            return pref.rule
        else:
            return None
    finally:
        db.close()


def analyze_statement_structure_from_file(file_path: str, user_id: str) -> Dict:
    """
    Analyze statement structure by reading CSV and calling Cursor Agent.
    
    Args:
        file_path: Path to CSV file
        user_id: User ID for context
    
    Returns:
        Dict with analysis and questions
    """
    try:
        # Read first 50 rows for analysis
        df = pd.read_csv(file_path, nrows=50)
        
        # Convert to string representation
        csv_sample = df.to_string()
        
        # Call Cursor Agent to analyze
        analysis = analyze_statement_structure(csv_sample, user_id)
        
        logger.info("Statement structure analyzed", {
            "file_path": file_path,
            "confidence": analysis.get("confidence", "unknown")
        })
        
        return analysis
        
    except Exception as e:
        logger.error("Failed to analyze statement structure", {
            "file_path": file_path,
            "error": str(e)
        })
        raise


def build_parsing_schema(analysis: Dict, user_responses: Dict) -> Dict:
    """
    Build parsing schema from AI analysis and user responses.
    
    Args:
        analysis: AI analysis dict with detected structure
        user_responses: User answers to questions (dict with question -> answer)
    
    Returns:
        Unified parsing schema dict
    """
    # Start with AI analysis
    schema = {
        "column_mappings": {
            "date": analysis.get("date_column", ""),
            "description": analysis.get("description_column", ""),
            "amount": analysis.get("amount_column", ""),
        },
        "date_format": analysis.get("date_format", "MM/DD/YYYY"),
        "currency": analysis.get("currency", "USD"),
        "has_headers": analysis.get("has_headers", True),
        "skip_rows": analysis.get("skip_rows", 0),
        "amount_positive_is": analysis.get("amount_positive_is", "debit"),
    }
    
    # Add balance column if detected
    if analysis.get("balance_column"):
        schema["column_mappings"]["balance"] = analysis["balance_column"]
    
    # Override with user responses
    if "date_column" in user_responses:
        schema["column_mappings"]["date"] = user_responses["date_column"]
    if "description_column" in user_responses:
        schema["column_mappings"]["description"] = user_responses["description_column"]
    if "amount_column" in user_responses:
        schema["column_mappings"]["amount"] = user_responses["amount_column"]
    if "balance_column" in user_responses:
        schema["column_mappings"]["balance"] = user_responses["balance_column"]
    if "date_format" in user_responses:
        schema["date_format"] = user_responses["date_format"]
    if "currency" in user_responses:
        schema["currency"] = user_responses["currency"]
    if "has_headers" in user_responses:
        schema["has_headers"] = user_responses["has_headers"]
    if "skip_rows" in user_responses:
        schema["skip_rows"] = int(user_responses["skip_rows"])
    if "amount_positive_is" in user_responses:
        schema["amount_positive_is"] = user_responses["amount_positive_is"]
    
    return schema


def save_parsing_schema(schema: Dict, bank_name: str, user_id: str, file_format: str = "csv") -> None:
    """
    Save parsing schema as CategorizationPreference for future use.
    
    Args:
        schema: Parsing schema dict
        bank_name: Bank name
        user_id: User ID
        file_format: File format (csv, xlsx, etc.)
    """
    db = SessionLocal()
    try:
        # Check if preference already exists
        existing = db.query(CategorizationPreference).filter(
            CategorizationPreference.user_id == user_id,
            CategorizationPreference.bank_name == bank_name,
            CategorizationPreference.preference_type == "parsing",
            CategorizationPreference.name == f"parsing_{bank_name}_{file_format}"
        ).first()
        
        if existing:
            # Update existing
            existing.rule = schema
            existing.updated_at = db.query(CategorizationPreference).filter(
                CategorizationPreference.id == existing.id
            ).first().updated_at
            logger.info("Updated parsing preferences", {
                "bank_name": bank_name,
                "user_id": user_id
            })
        else:
            # Create new
            pref = CategorizationPreference(
                user_id=user_id,
                bank_name=bank_name,
                name=f"parsing_{bank_name}_{file_format}",
                rule=schema,
                preference_type="parsing",
                enabled=True,
                priority=0
            )
            db.add(pref)
            logger.info("Saved new parsing preferences", {
                "bank_name": bank_name,
                "user_id": user_id
            })
        
        db.commit()
        
    finally:
        db.close()
