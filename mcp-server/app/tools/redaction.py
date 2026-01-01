"""
Redaction Utilities for Sensitive Data

Implements server-side redaction of PII and sensitive financial data
from insights before storage. Provides defense-in-depth even if
AI-generated content contains sensitive information.
"""

import re
from typing import Tuple, List

from app.logger import create_logger

logger = create_logger("redaction")

# Regex patterns for sensitive data detection
# Order matters - more specific patterns should be checked first
PATTERNS = {
    # IBAN: 2 letters + 2 digits + 10-30 alphanumeric (with optional spaces)
    # Must match before credit card to avoid partial matches
    "iban": re.compile(r'\b([A-Z]{2})\s?([0-9]{2})\s?([A-Z0-9\s]{10,30})\b', re.IGNORECASE),
    # Credit card: Starts with 3/4/5/6, exactly 13-19 digits, optionally separated by spaces or dashes
    # Luhn-valid card prefixes: 3(Amex), 4(Visa), 5(MC), 6(Discover)
    "credit_card": re.compile(r'\b[3-6]\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{1,7}\b'),
    # SWIFT/BIC: 8 or 11 characters (6 letters + 2 alphanumeric + optional 3 alphanumeric)
    "swift": re.compile(r'\b([A-Z]{4})([A-Z]{2})([A-Z0-9]{2})([A-Z0-9]{3})?\b'),
    # Email addresses
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b'),
    # Account numbers: 8+ digits not preceded/followed by decimal separators
    # Excludes amounts like $1,234.56 or 1234.56
    "account_number": re.compile(r'(?<![0-9,.])\b\d{8,}\b(?![0-9,.])'),
}


def redact_credit_card(text: str) -> str:
    """
    Completely redact credit card numbers.
    
    Example: "4532 1234 5678 9012" -> "****CARD****"
    """
    return PATTERNS["credit_card"].sub("****CARD****", text)


def redact_email(text: str) -> str:
    """
    Redact email local part, keep domain.
    
    Example: "john.doe@example.com" -> "****@example.com"
    """
    def replace_email(match):
        domain = match.group(1)
        return f"****@{domain}"
    
    return PATTERNS["email"].sub(replace_email, text)


def redact_iban(text: str) -> str:
    """
    Redact IBAN, keep country code and last 4 digits.
    
    Example: "GB82 WEST 1234 5698 7654 32" -> "GB82 ****7654"
    """
    def replace_iban(match):
        country_code = match.group(1).upper()
        check_digits = match.group(2)
        account_part = match.group(3)
        # Find all digit groups in the account part
        digit_groups = re.findall(r'\d+', account_part)
        # Find the last group with 4+ digits and take its last 4
        last_four = ""
        for group in reversed(digit_groups):
            if len(group) >= 4:
                last_four = group[-4:]
                break
        # Fallback: concatenate all digits and take last 4
        if not last_four:
            all_digits = ''.join(digit_groups)
            last_four = all_digits[-4:] if len(all_digits) >= 4 else all_digits
        return f"{country_code}{check_digits} ****{last_four}"
    
    return PATTERNS["iban"].sub(replace_iban, text)


def redact_swift(text: str) -> str:
    """
    Redact SWIFT/BIC codes, keep first 4 and last 3 characters.
    
    Example: "DEUTDEFF500" -> "DEUT****500"
    """
    def replace_swift(match):
        bank_code = match.group(1)  # First 4 letters (bank code)
        branch_code = match.group(4) if match.group(4) else ""  # Last 3 (optional branch)
        if branch_code:
            return f"{bank_code}****{branch_code}"
        else:
            # 8-character SWIFT without branch code
            country_loc = match.group(2) + match.group(3)  # Last 4 chars
            return f"{bank_code}****{country_loc[-3:]}"
    
    return PATTERNS["swift"].sub(replace_swift, text)


def redact_account_number(text: str) -> str:
    """
    Redact account numbers, keep last 4 digits.
    
    Example: "Account 12345678901234" -> "Account ****1234"
    """
    def replace_account(match):
        number = match.group(0)
        last_four = number[-4:]
        return f"****{last_four}"
    
    return PATTERNS["account_number"].sub(replace_account, text)


def redact_insights(insights: str) -> str:
    """
    Apply all redaction rules to insights text.
    
    Applies redactions in order of specificity to avoid
    partial matches causing issues.
    
    Args:
        insights: Raw insights text potentially containing PII
        
    Returns:
        Redacted insights text safe for storage
    """
    if not insights:
        return insights
    
    original = insights
    
    # Apply redactions in order of specificity (most specific first)
    # IBAN must be processed before credit card to avoid partial matches
    redacted = insights
    redacted = redact_iban(redacted)
    redacted = redact_swift(redacted)
    redacted = redact_credit_card(redacted)
    redacted = redact_email(redacted)
    redacted = redact_account_number(redacted)
    
    if redacted != original:
        # Calculate approximate number of redactions (simple heuristic)
        original_len = len(original)
        redacted_len = len(redacted)
        logger.info("Redaction applied", {
            "chars_changed": abs(original_len - redacted_len),
            "original_len": original_len,
            "redacted_len": redacted_len,
        })
    
    return redacted


def validate_no_sensitive_data(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text contains potentially sensitive data after redaction.
    
    This is a post-redaction validation to catch any patterns that
    may have slipped through the redaction process.
    
    Args:
        text: Text to validate
        
    Returns:
        Tuple of (is_safe, list of detected pattern types)
    """
    detected: List[str] = []
    
    # Check for credit card patterns
    if PATTERNS["credit_card"].search(text):
        detected.append("credit_card")
    
    # Check for email addresses (might be intentionally preserved in some cases)
    if PATTERNS["email"].search(text):
        detected.append("email")
    
    # Check for very long numbers (likely account numbers)
    if re.search(r'\b\d{12,}\b', text):
        detected.append("long_account_number")
    
    # Check for potential SSN patterns (XXX-XX-XXXX)
    if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
        detected.append("ssn_pattern")
    
    return (len(detected) == 0, detected)

