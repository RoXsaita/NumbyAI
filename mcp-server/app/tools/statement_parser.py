"""
Statement Parser - CSV/Excel parsing and transaction extraction

This module handles parsing of bank statement files (CSV/Excel) and extracting
transaction data. It applies parsing schemas (from CategorizationPreference)
to normalize transaction data.
"""
import pandas as pd
import re
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
from app.logger import create_logger

logger = create_logger("statement_parser")


def parse_csv_statement(file_path: str, schema: Dict) -> List[Dict]:
    """
    Parse CSV/Excel statement using provided schema.
    
    Args:
        file_path: Path to CSV/Excel file
        schema: Parsing schema with column mappings, date format, etc.
                Expected keys:
                - column_mappings: {date: "Column A", description: "Column B", amount: "Column C", ...}
                - date_format: "MM/DD/YYYY" or similar
                - currency: "USD" or similar
                - has_headers: bool
                - skip_rows: int
                - amount_positive_is: "debit" or "credit"
    
    Returns:
        List of raw transaction dicts with: date, description, amount, balance (if available)
    """
    try:
        # Determine file type
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path, header=0 if schema.get('has_headers', True) else None, 
                             skiprows=schema.get('skip_rows', 0))
        else:
            df = pd.read_csv(file_path, header=0 if schema.get('has_headers', True) else None,
                           skiprows=schema.get('skip_rows', 0))
        
        logger.info("Parsed statement file", {
            "file_path": file_path,
            "rows": len(df),
            "columns": list(df.columns)
        })
        
        # Get column mappings
        column_mappings = schema.get('column_mappings', {})
        date_col = column_mappings.get('date')
        description_col = column_mappings.get('description')
        amount_col = column_mappings.get('amount')
        balance_col = column_mappings.get('balance')  # Optional
        
        # Validate required columns exist
        if not date_col or not description_col or not amount_col:
            raise ValueError(f"Missing required column mappings: date={date_col}, description={description_col}, amount={amount_col}")
        
        # Map column names (handle both column names and indices like "Column A")
        date_col_name = _resolve_column_name(df, date_col)
        description_col_name = _resolve_column_name(df, description_col)
        amount_col_name = _resolve_column_name(df, amount_col)
        balance_col_name = _resolve_column_name(df, balance_col) if balance_col else None
        
        if not date_col_name or not description_col_name or not amount_col_name:
            raise ValueError(f"Could not resolve column names from mappings")
        
        # Parse transactions
        transactions = []
        date_format = schema.get('date_format', '%Y-%m-%d')
        currency = schema.get('currency', 'USD')
        amount_positive_is = schema.get('amount_positive_is', 'debit')
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                date_str = str(row[date_col_name]).strip()
                date = _parse_date(date_str, date_format)
                
                # Get description
                description = str(row[description_col_name]).strip()
                
                # Parse amount
                amount_str = str(row[amount_col_name]).strip()
                amount = _parse_amount(amount_str)
                
                # Apply sign convention: if amount_positive_is="credit" and amount is positive, it's income
                # If amount_positive_is="debit" and amount is positive, it's expense (make negative)
                if amount_positive_is == 'debit' and amount > 0:
                    amount = -abs(amount)  # Expenses are negative
                elif amount_positive_is == 'credit' and amount < 0:
                    amount = abs(amount)  # Credits are positive
                
                # Get balance if available
                balance = None
                if balance_col_name and pd.notna(row.get(balance_col_name)):
                    balance_str = str(row[balance_col_name]).strip()
                    balance = _parse_amount(balance_str)
                
                transaction = {
                    'date': date,
                    'description': description,
                    'amount': float(amount),
                    'currency': currency,
                    'balance': float(balance) if balance is not None else None,
                }
                
                transactions.append(transaction)
                
            except Exception as e:
                logger.warn("Failed to parse transaction row", {
                    "row": idx,
                    "error": str(e)
                })
                continue
        
        logger.info("Extracted transactions from statement", {
            "total": len(transactions),
            "file_path": file_path
        })
        
        return transactions
        
    except Exception as e:
        logger.error("Failed to parse statement file", {
            "file_path": file_path,
            "error": str(e)
        })
        raise


def _resolve_column_name(df: pd.DataFrame, column_ref: str) -> Optional[str]:
    """
    Resolve column reference to actual column name.
    
    Handles:
    - Column names directly: "Date", "Transaction Description"
    - Column indices: "Column A", "Column B" (0-indexed: A=0, B=1, etc.)
    - Column indices as numbers: "0", "1", "2"
    """
    if not column_ref:
        return None
    
    # Try direct column name match
    if column_ref in df.columns:
        return column_ref
    
    # Try column index format "Column A", "Column B", etc.
    column_index_match = re.match(r'^Column\s+([A-Z])$', column_ref, re.IGNORECASE)
    if column_index_match:
        letter = column_index_match.group(1).upper()
        col_idx = ord(letter) - ord('A')
        if 0 <= col_idx < len(df.columns):
            return df.columns[col_idx]
    
    # Try numeric index
    try:
        col_idx = int(column_ref)
        if 0 <= col_idx < len(df.columns):
            return df.columns[col_idx]
    except ValueError:
        pass
    
    return None


def _parse_date(date_str: str, date_format: str) -> datetime:
    """Parse date string using provided format."""
    # Common date format mappings
    format_mappings = {
        'MM/DD/YYYY': '%m/%d/%Y',
        'DD/MM/YYYY': '%d/%m/%Y',
        'YYYY-MM-DD': '%Y-%m-%d',
        'MM-DD-YYYY': '%m-%d-%Y',
        'DD-MM-YYYY': '%d-%m-%Y',
    }
    
    # Map format string
    python_format = format_mappings.get(date_format, date_format)
    
    # Try parsing with the format
    try:
        return datetime.strptime(date_str, python_format).date()
    except ValueError:
        # Try common formats as fallback
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Could not parse date: {date_str} with format: {date_format}")


def _parse_amount(amount_str: str) -> Decimal:
    """Parse amount string, handling currency symbols, commas, parentheses for negatives."""
    # Remove currency symbols
    amount_str = re.sub(r'[$€£¥]', '', amount_str)
    
    # Remove commas
    amount_str = amount_str.replace(',', '')
    
    # Handle parentheses for negatives (accounting format)
    if amount_str.startswith('(') and amount_str.endswith(')'):
        amount_str = '-' + amount_str[1:-1]
    
    # Remove whitespace
    amount_str = amount_str.strip()
    
    try:
        return Decimal(amount_str)
    except Exception as e:
        raise ValueError(f"Could not parse amount: {amount_str}")


def extract_merchant(description: str) -> str:
    """
    Extract merchant name from transaction description.
    
    Uses pattern matching to identify common merchant patterns:
    - "AMZN" → "Amazon"
    - "UBER" → "Uber"
    - "STARBUCKS" → "Starbucks"
    - etc.
    
    Args:
        description: Full transaction description
    
    Returns:
        Extracted merchant name, or original description if no pattern matches
    """
    description_upper = description.upper()
    
    # Common merchant patterns
    merchant_patterns = {
        r'\bAMZN\b': 'Amazon',
        r'\bUBER\b': 'Uber',
        r'\bUBER\s*EATS\b': 'Uber Eats',
        r'\bSTARBUCKS\b': 'Starbucks',
        r'\bWALMART\b': 'Walmart',
        r'\bTARGET\b': 'Target',
        r'\bCOSTCO\b': 'Costco',
        r'\bNETFLIX\b': 'Netflix',
        r'\bSPOTIFY\b': 'Spotify',
        r'\bAPPLE\b': 'Apple',
        r'\bGOOGLE\b': 'Google',
        r'\bMICROSOFT\b': 'Microsoft',
        r'\bPAYPAL\b': 'PayPal',
        r'\bVENMO\b': 'Venmo',
        r'\bSQUARE\b': 'Square',
    }
    
    # Try to match patterns
    for pattern, merchant_name in merchant_patterns.items():
        if re.search(pattern, description_upper):
            return merchant_name
    
    # If no pattern matches, try to extract first meaningful word/phrase
    # Remove common prefixes like "POS ", "ACH ", "DEBIT ", "CREDIT "
    cleaned = re.sub(r'^(POS|ACH|DEBIT|CREDIT|PURCHASE|PAYMENT)\s+', '', description_upper, flags=re.IGNORECASE)
    
    # Extract first 2-3 words as merchant name
    words = cleaned.split()[:3]
    if words:
        merchant = ' '.join(words)
        # Limit length
        if len(merchant) > 50:
            merchant = merchant[:50]
        return merchant
    
    # Fallback: return original description (truncated)
    return description[:100] if len(description) > 100 else description


def normalize_transaction(raw_tx: Dict, schema: Dict) -> Dict:
    """
    Normalize transaction format and validate data.
    
    Args:
        raw_tx: Raw transaction dict from parser
        schema: Parsing schema (for validation)
    
    Returns:
        Normalized transaction dict with validated fields
    """
    # Validate required fields
    if 'date' not in raw_tx or not raw_tx['date']:
        raise ValueError("Transaction missing date")
    if 'description' not in raw_tx or not raw_tx['description']:
        raise ValueError("Transaction missing description")
    if 'amount' not in raw_tx or raw_tx['amount'] is None:
        raise ValueError("Transaction missing amount")
    
    # Extract merchant
    merchant = extract_merchant(raw_tx['description'])
    
    # Build normalized transaction
    normalized = {
        'date': raw_tx['date'],
        'description': raw_tx['description'].strip(),
        'merchant': merchant,
        'amount': float(raw_tx['amount']),
        'currency': raw_tx.get('currency', schema.get('currency', 'USD')),
        'balance': raw_tx.get('balance'),
    }
    
    return normalized
