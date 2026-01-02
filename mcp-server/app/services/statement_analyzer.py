"""
Statement Analyzer - Analyze statement structure using heuristics

This service analyzes bank statement CSV files using pattern matching and heuristics
to detect columns, date formats, currency, etc. without requiring AI.
"""
import pandas as pd
import re
from typing import Dict, Optional, List, Union
from app.database import SessionLocal, CategorizationPreference
from app.logger import create_logger

logger = create_logger("statement_analyzer")


def validate_column_reference(column_ref: Union[str, List[str]]) -> bool:
    """
    Validate that a column reference is a valid numeric index, not data.
    
    Args:
        column_ref: Column reference string or list of strings
        
    Returns:
        True if valid, False if it looks like data
    """
    # Handle array (for description columns)
    if isinstance(column_ref, list):
        return all(validate_column_reference(ref) for ref in column_ref)
    
    if not column_ref or not isinstance(column_ref, str):
        return False
    
    # Must be numeric string like "0", "1", "2"
    try:
        idx = int(column_ref)
        if idx < 0 or idx > 100:
            return False
        # Must be EXACTLY the string representation of the number (no extra chars)
        if column_ref != str(idx):
            return False
    except (ValueError, TypeError):
        return False
    
    # Additional checks: reject if it looks like data
    # Date pattern
    if re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$', column_ref):
        return False
    # Number with decimal
    if re.match(r'^\d+[.,]\d+$', column_ref):
        return False
    # Too long for a column index
    if len(column_ref) > 3:
        return False
    
    return True


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
    Analyze statement structure using heuristics (no AI needed).
    
    Args:
        file_path: Path to CSV file
        user_id: User ID for context (unused, kept for compatibility)
    
    Returns:
        Dict with analysis and detected structure
    """
    try:
        # Read first 30 rows for analysis (as strings to preserve formatting)
        df = pd.read_csv(file_path, nrows=30, dtype=str, keep_default_na=False)
        
        columns_found = [str(i) for i in range(len(df.columns))]
        
        # Detect date column and format
        date_column = None
        date_format = None
        date_patterns = [
            (r'^\d{4}-\d{2}-\d{2}$', 'YYYY-MM-DD'),
            (r'^\d{2}-\d{2}-\d{4}$', 'DD-MM-YYYY'),
            (r'^\d{2}/\d{2}/\d{4}$', 'DD/MM/YYYY'),
            (r'^\d{2}/\d{2}/\d{4}$', 'MM/DD/YYYY'),
            (r'^\d{4}/\d{2}/\d{2}$', 'YYYY/MM/DD'),
        ]
        
        for col_idx in range(min(5, len(df.columns))):  # Check first 5 columns
            col_data = df.iloc[:, col_idx].astype(str).str.strip()
            col_data = col_data[col_data != '']
            
            if len(col_data) < 3:
                continue
                
            # Check for date patterns
            best_matches = 0
            best_format = None
            for pattern, fmt in date_patterns:
                matches = sum(1 for val in col_data.head(20) if re.match(pattern, str(val)))
                if matches > best_matches:
                    best_matches = matches
                    best_format = fmt
            
            # If at least 60% match, consider it a date column
            if best_matches >= len(col_data.head(20)) * 0.6:
                date_column = str(col_idx)
                date_format = best_format
                break
        
        # Detect amount column (numeric with currency symbols or commas)
        amount_column = None
        for col_idx in range(len(df.columns)):
            col_data = df.iloc[:, col_idx].astype(str).str.strip()
            col_data = col_data[col_data != '']
            
            if len(col_data) < 3:
                continue
            
            # Check if column contains numeric values (with currency symbols, commas, etc.)
            numeric_count = 0
            for val in col_data.head(20):
                # Remove currency symbols, commas, spaces, parentheses
                cleaned = re.sub(r'[$€£¥,\s()]', '', str(val))
                # Check if it's a number (including negatives)
                if re.match(r'^-?\d+\.?\d*$', cleaned) or re.match(r'^-?\d+[.,]\d*$', cleaned):
                    numeric_count += 1
            
            # If most values are numeric, likely an amount column
            if numeric_count >= len(col_data.head(20)) * 0.7:
                amount_column = str(col_idx)
                break
        
        # Detect description column (longest text column, typically not date/amount)
        description_column = None
        max_avg_length = 0
        for col_idx in range(len(df.columns)):
            if f"Column {col_idx}" in [date_column, amount_column]:
                continue
                
            col_data = df.iloc[:, col_idx].astype(str).str.strip()
            col_data = col_data[col_data != '']
            
            if len(col_data) < 3:
                continue
            
            # Calculate average length
            avg_length = sum(len(str(val)) for val in col_data.head(20)) / len(col_data.head(20))
            
            if avg_length > max_avg_length and avg_length > 10:  # At least 10 chars average
                max_avg_length = avg_length
                description_column = str(col_idx)
        
        # Detect balance column (numeric, typically after amount column)
        balance_column = None
        if amount_column:
            amount_idx = int(amount_column.split()[-1])
            # Look for numeric columns after amount column
            for col_idx in range(amount_idx + 1, min(amount_idx + 3, len(df.columns))):
                col_data = df.iloc[:, col_idx].astype(str).str.strip()
                col_data = col_data[col_data != '']
                
                if len(col_data) < 3:
                    continue
                
                numeric_count = sum(1 for val in col_data.head(20) 
                                   if re.match(r'^-?\d+[.,]?\d*$', re.sub(r'[$€£¥,\s()]', '', str(val))))
                
                if numeric_count >= len(col_data.head(20)) * 0.7:
                    balance_column = str(col_idx)
                    break
        
        # Detect currency (look for currency symbols or codes in amount column)
        currency = "USD"  # Default
        if amount_column:
            amount_idx = int(amount_column.split()[-1])
            col_data = df.iloc[:, amount_idx].astype(str).str.strip()
            sample_values = ' '.join(col_data.head(10).tolist())
            
            currency_symbols = {
                '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', 'PLN': 'PLN',
                'USD': 'USD', 'EUR': 'EUR', 'GBP': 'GBP', 'JPY': 'JPY'
            }
            
            for symbol, code in currency_symbols.items():
                if symbol in sample_values:
                    currency = code
                    break
        
        # Detect if has headers (check if first row looks like headers vs data)
        has_headers = False
        if len(df) > 1:
            first_row = df.iloc[0].astype(str).str.strip()
            second_row = df.iloc[1].astype(str).str.strip()
            
            # If first row has mostly non-numeric, short values, likely headers
            first_row_numeric = sum(1 for val in first_row if re.match(r'^-?\d+[.,]?\d*$', re.sub(r'[$€£¥,\s()]', '', str(val))))
            second_row_numeric = sum(1 for val in second_row if re.match(r'^-?\d+[.,]?\d*$', re.sub(r'[$€£¥,\s()]', '', str(val))))
            
            # If first row has fewer numbers than second row, likely headers
            if first_row_numeric < second_row_numeric:
                has_headers = True
        
        # Default skip_rows (user will specify first_transaction_row in UI)
        skip_rows = 0
        
        # Default amount_positive_is (hard to detect without context)
        amount_positive_is = "debit"
        
        analysis = {
            "columns_found": columns_found,
            "date_column": date_column or "0",
            "description_column": description_column or "1",
            "amount_column": amount_column or "2",
            "balance_column": balance_column,
            "date_format": date_format or "DD/MM/YYYY",
            "currency": currency,
            "has_headers": has_headers,
            "skip_rows": skip_rows,
            "amount_positive_is": amount_positive_is,
            "questions": [],
            "confidence": "high" if date_column and amount_column and description_column else "medium"
        }
        
        logger.info("Statement structure analyzed (heuristics)", {
            "file_path": file_path,
            "date_column": date_column,
            "amount_column": amount_column,
            "description_column": description_column,
            "confidence": analysis.get("confidence")
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
    Build parsing schema from heuristic analysis and user responses.
    
    Args:
        analysis: Heuristic analysis dict with detected structure
        user_responses: User answers to questions (dict with question -> answer)
    
    Returns:
        Unified parsing schema dict
    """
    # Start with heuristic analysis
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
    # Validate column_mappings before saving
    column_mappings = schema.get('column_mappings', {})
    if column_mappings:
        invalid_refs = []
        for field_type, column_ref in column_mappings.items():
            if not validate_column_reference(column_ref):
                invalid_refs.append(f"{field_type}: {column_ref}")
        
        if invalid_refs:
            error_msg = (
                f"Invalid column mappings detected for bank '{bank_name}'. "
                f"The following fields contain data values instead of column indices: {', '.join(invalid_refs)}. "
                f"Column references must be numeric indices like '0', '1', '2'."
            )
            logger.error("Validation failed - refusing to save corrupted mappings", {
                "bank_name": bank_name,
                "user_id": user_id,
                "invalid_refs": invalid_refs,
                "column_mappings": column_mappings
            })
            raise ValueError(error_msg)
    
    logger.info("Column mappings validated successfully", {
        "bank_name": bank_name,
        "column_mappings": column_mappings
    })
    
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
