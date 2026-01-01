"""
Cursor Agent Service - Unified service for all Cursor Agent interactions

This service handles all communication with Cursor Agent headless CLI for:
- Statement structure analysis
- Transaction categorization
- Other AI-powered tasks
"""
import subprocess
import json
import os
from typing import Dict, List, Optional, Union, Iterator
from app.config import settings
from app.logger import create_logger
from app.tools.category_helpers import PREDEFINED_CATEGORIES

logger = create_logger("cursor_agent_service")


def call_cursor_agent(
    prompt: str,
    model: str = "auto",
    stream: bool = False,
    timeout: int = 300
) -> Union[Dict, Iterator[str]]:
    """
    Base function to call Cursor Agent CLI.
    
    Args:
        prompt: The prompt to send to Cursor Agent
        model: Model to use (default: "auto")
        stream: Whether to stream responses (for chat interface)
        timeout: Timeout in seconds (default: 300)
    
    Returns:
        Dict with parsed JSON response, or Iterator[str] for streaming
    """
    cursor_path = settings.cursor_agent_path
    cmd = [cursor_path, "-p", "--model", model]
    
    # Add API key if provided
    env = os.environ.copy()
    if settings.cursor_api_key:
        env["CURSOR_API_KEY"] = settings.cursor_api_key
    
    logger.info("Calling Cursor Agent", {
        "model": model,
        "stream": stream,
        "prompt_length": len(prompt)
    })
    
    try:
        if stream:
            # For streaming, we'll use a different approach
            # For now, return non-streaming and handle streaming separately
            # TODO: Implement proper streaming with subprocess.Popen
            result = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                check=True,
                timeout=timeout,
                env=env
            )
            # Parse JSON response
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # If not JSON, return as text
                return {"text": result.stdout.strip()}
        else:
            result = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                check=True,
                timeout=timeout,
                env=env
            )
            
            # Parse JSON response
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # If not JSON, return as text
                return {"text": result.stdout.strip()}
                
    except subprocess.TimeoutExpired:
        logger.error("Cursor Agent call timed out", {"timeout": timeout})
        raise TimeoutError(f"Cursor Agent call timed out after {timeout} seconds")
    except subprocess.CalledProcessError as e:
        logger.error("Cursor Agent call failed", {
            "returncode": e.returncode,
            "stderr": e.stderr
        })
        raise RuntimeError(f"Cursor Agent call failed: {e.stderr}")
    except Exception as e:
        logger.error("Unexpected error calling Cursor Agent", {"error": str(e)})
        raise


def analyze_statement_structure(csv_sample: str, user_id: str) -> Dict:
    """
    Analyze CSV statement structure using Cursor Agent.
    
    Args:
        csv_sample: First 50 rows of CSV as string
        user_id: User ID for context
    
    Returns:
        Dict with analysis and questions for user
    """
    prompt = f"""Analyze this bank statement CSV and identify its structure.

CSV Sample (first 50 rows):
{csv_sample}

Please analyze:
1. What columns exist? (date, description, amount, balance, etc.)
2. Which column contains the transaction date?
3. Which column contains the transaction description?
4. Which column contains the transaction amount?
5. What date format is used? (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, etc.)
6. What currency is used?
7. Are there headers in the first row?
8. Are there any rows to skip at the beginning?

Return your analysis as JSON with this structure:
{{
    "columns_found": ["list of column names or indices"],
    "date_column": "Column A" or column name,
    "description_column": "Column B" or column name,
    "amount_column": "Column C" or column name,
    "balance_column": "Column D" or column name (if exists),
    "date_format": "MM/DD/YYYY" or detected format,
    "currency": "USD" or detected currency,
    "has_headers": true/false,
    "skip_rows": 0 or number of rows to skip,
    "amount_positive_is": "debit" or "credit",
    "questions": [
        "Question 1 for user",
        "Question 2 for user"
    ],
    "confidence": "high" or "medium" or "low"
}}

If you're uncertain about any field, include it in the questions array for the user to confirm.
"""
    
    try:
        response = call_cursor_agent(prompt, model="auto")
        
        # Extract JSON from response
        if isinstance(response, dict):
            if "text" in response:
                # Try to parse JSON from text
                text = response["text"]
                # Look for JSON block in markdown code fences
                json_match = None
                if "```json" in text:
                    json_match = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    json_match = text.split("```")[1].split("```")[0].strip()
                else:
                    json_match = text
                
                try:
                    return json.loads(json_match)
                except json.JSONDecodeError:
                    # Fallback: return structured response
                    return {
                        "columns_found": [],
                        "questions": [text],
                        "confidence": "low"
                    }
            else:
                return response
        else:
            return {"error": "Unexpected response format", "response": response}
            
    except Exception as e:
        logger.error("Failed to analyze statement structure", {"error": str(e)})
        raise


def categorize_transactions_batch(
    transactions: List[Dict],
    user_id: str,
    existing_rules: List[Dict]
) -> List[Dict]:
    """
    Categorize a batch of transactions using Cursor Agent.
    
    Args:
        transactions: List of transaction dicts with id, date, description, merchant, amount
        user_id: User ID for context
        existing_rules: List of existing categorization rules
    
    Returns:
        List of dicts with {id, category} for each transaction
    """
    categories_str = ", ".join(PREDEFINED_CATEGORIES)
    
    # Format existing rules
    rules_str = ""
    if existing_rules:
        rules_str = "\nExisting categorization rules (apply these first):\n"
        for rule in existing_rules:
            pattern = rule.get('merchant_pattern', '')
            category = rule.get('category', '')
            rules_str += f"- If merchant matches '{pattern}', assign category '{category}'\n"
    
    # Format transactions
    transactions_json = json.dumps(transactions, indent=2, default=str)
    
    prompt = f"""Categorize these bank transactions into the predefined categories.

Available categories:
{categories_str}
{rules_str}

Transactions to categorize:
{transactions_json}

For each transaction:
1. First check if the merchant matches any existing rule above
2. If no rule matches, analyze the description and merchant to determine the best category
3. Assign exactly one category per transaction

Return JSON array with this structure:
[
    {{"id": 1, "category": "Groceries"}},
    {{"id": 2, "category": "Transportation"}},
    ...
]

Each transaction must have an "id" field matching the transaction ID and a "category" field with one of the predefined categories.
"""
    
    try:
        response = call_cursor_agent(prompt, model="auto")
        
        # Extract JSON array from response
        if isinstance(response, dict):
            if "text" in response:
                text = response["text"]
                # Look for JSON array in markdown code fences
                json_match = None
                if "```json" in text:
                    json_match = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    json_match = text.split("```")[1].split("```")[0].strip()
                else:
                    json_match = text
                
                try:
                    categorized = json.loads(json_match)
                    if isinstance(categorized, list):
                        return categorized
                    else:
                        logger.warn("Expected list but got dict", {"response": categorized})
                        return []
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse categorization response", {
                        "error": str(e),
                        "text": text[:500]
                    })
                    return []
            else:
                # Direct dict response
                if isinstance(response, list):
                    return response
                else:
                    logger.warn("Unexpected response format", {"response": response})
                    return []
        else:
            logger.warn("Unexpected response type", {"type": type(response)})
            return []
            
    except Exception as e:
        logger.error("Failed to categorize transactions", {"error": str(e)})
        raise


def build_categorization_prompt(
    transactions: List[Dict],
    existing_rules: List[Dict],
    categories: List[str]
) -> str:
    """
    Build prompt for transaction categorization.
    
    Args:
        transactions: List of transaction dicts
        existing_rules: List of existing categorization rules
        categories: List of predefined categories
    
    Returns:
        Formatted prompt string
    """
    categories_str = ", ".join(categories)
    
    rules_str = ""
    if existing_rules:
        rules_str = "\nExisting categorization rules (apply these first):\n"
        for rule in existing_rules:
            pattern = rule.get('merchant_pattern', '')
            category = rule.get('category', '')
            rules_str += f"- If merchant matches '{pattern}', assign category '{category}'\n"
    
    transactions_json = json.dumps(transactions, indent=2, default=str)
    
    prompt = f"""Categorize these bank transactions.

Available categories: {categories_str}
{rules_str}

Transactions:
{transactions_json}

Return JSON array: [{{"id": 1, "category": "Groceries"}}, ...]
"""
    
    return prompt


def learn_merchant_rules(transactions: List, db) -> List:
    """
    Learn new merchant categorization rules from transactions.
    
    Groups transactions by merchant + category, and if a merchant is categorized
    the same way 3+ times, creates a CategorizationRule.
    
    Args:
        transactions: List of Transaction objects (already categorized)
        db: Database session
    
    Returns:
        List of newly created CategorizationRule objects
    """
    from app.database import CategorizationRule
    from collections import defaultdict
    
    # Group by merchant + category
    merchant_category_counts = defaultdict(int)
    merchant_category_map = {}
    
    for tx in transactions:
        if not tx.merchant or not tx.category:
            continue
        
        key = (tx.merchant.lower(), tx.category)
        merchant_category_counts[key] += 1
        merchant_category_map[key] = tx.category
    
    # Find merchants with 3+ consistent categorizations
    new_rules = []
    user_id = transactions[0].user_id if transactions else None
    
    if not user_id:
        return []
    
    for (merchant, category), count in merchant_category_counts.items():
        if count >= 3:
            # Check if rule already exists
            existing = db.query(CategorizationRule).filter(
                CategorizationRule.user_id == user_id,
                CategorizationRule.merchant_pattern == merchant,
                CategorizationRule.category == category
            ).first()
            
            if not existing:
                # Create new rule
                rule = CategorizationRule(
                    user_id=user_id,
                    merchant_pattern=merchant,
                    category=category,
                    confidence_score=count,
                    enabled=True
                )
                db.add(rule)
                new_rules.append(rule)
                logger.info("Learned new categorization rule", {
                    "merchant": merchant,
                    "category": category,
                    "confidence": count
                })
            else:
                # Update confidence score
                existing.confidence_score = max(existing.confidence_score, count)
                existing.updated_at = db.query(CategorizationRule).filter(
                    CategorizationRule.id == existing.id
                ).first().updated_at
                logger.info("Updated categorization rule confidence", {
                    "merchant": merchant,
                    "category": category,
                    "confidence": count
                })
    
    if new_rules:
        db.commit()
    
    return new_rules
