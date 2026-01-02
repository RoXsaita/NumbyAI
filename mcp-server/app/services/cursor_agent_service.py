"""
Cursor Agent Service - Unified service for all Cursor Agent interactions

This service handles all communication with Cursor Agent headless CLI for:
- Statement structure analysis
- Transaction categorization
- Chat interface with streaming
- Other AI-powered tasks
"""
import subprocess
import json
import os
import asyncio
from typing import Dict, List, Optional, Union, Iterator, AsyncIterator
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
    existing_rules: List[Dict],
    batch_size: int = 20,
    parallel: bool = True
) -> List[Dict]:
    """
    Categorize a batch of transactions using Cursor Agent.
    Processes transactions in parallel batches for better performance.
    
    Args:
        transactions: List of transaction dicts with id, date, description, merchant, amount
        user_id: User ID for context
        existing_rules: List of existing categorization rules
        batch_size: Number of transactions per batch (default: 20)
        parallel: Whether to process batches in parallel (default: True)
    
    Returns:
        List of dicts with {id, category} for each transaction
    """
    if not transactions:
        return []
    
    # Split into batches
    batches = []
    for i in range(0, len(transactions), batch_size):
        batches.append(transactions[i:i + batch_size])
    
    logger.info("Categorizing transactions", {
        "total": len(transactions),
        "batches": len(batches),
        "batch_size": batch_size,
        "parallel": parallel
    })
    
    if parallel and len(batches) > 1:
        # Process batches in parallel using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def categorize_single_batch(batch: List[Dict]) -> List[Dict]:
            """Categorize a single batch of transactions"""
            return _categorize_batch_internal(batch, user_id, existing_rules)
        
        all_results = []
        with ThreadPoolExecutor(max_workers=min(len(batches), 5)) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(categorize_single_batch, batch): idx
                for idx, batch in enumerate(batches)
            }
            
            # Collect results as they complete
            batch_results = [None] * len(batches)
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    result = future.result()
                    batch_results[batch_idx] = result
                    logger.info(f"Completed batch {batch_idx + 1}/{len(batches)}", {
                        "batch_size": len(batches[batch_idx]),
                        "categorized": len(result) if result else 0
                    })
                except Exception as e:
                    logger.error(f"Batch {batch_idx + 1} failed", {"error": str(e)})
                    # Return empty categories for failed batch
                    batch_results[batch_idx] = []
            
            # Combine results in order
            for result in batch_results:
                if result:
                    all_results.extend(result)
    else:
        # Process sequentially
        all_results = []
        for idx, batch in enumerate(batches):
            try:
                result = _categorize_batch_internal(batch, user_id, existing_rules)
                all_results.extend(result)
                logger.info(f"Completed batch {idx + 1}/{len(batches)}", {
                    "batch_size": len(batch),
                    "categorized": len(result) if result else 0
                })
            except Exception as e:
                logger.error(f"Batch {idx + 1} failed", {"error": str(e)})
                # Continue with other batches
    
    logger.info("Categorization complete", {
        "total_transactions": len(transactions),
        "categorized": len(all_results)
    })
    
    return all_results


def _categorize_batch_internal(
    transactions: List[Dict],
    user_id: str,
    existing_rules: List[Dict]
) -> List[Dict]:
    """
    Internal function to categorize a single batch of transactions.
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
        # Return empty list instead of raising to allow other batches to continue
        return []


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


def build_mcp_tool_context(user_id: Optional[str] = None) -> str:
    """
    Build context string about available MCP tools for the Cursor agent.
    
    Args:
        user_id: Current user ID for context
    
    Returns:
        Formatted string with MCP tool information
    """
    mcp_base_url = os.getenv("BASE_URL", "http://localhost:8000")
    
    context = f"""
You are a financial assistant for NumbyAI, a personal finance budgeting application.

AVAILABLE MCP TOOLS:
You have access to the following tools through the MCP server at {mcp_base_url}/mcp:

1. **fetch_preferences** - Get user settings, categorization rules, or parsing instructions
   - Use this FIRST when starting any finance conversation
   - Parameters: preference_type (single or array), bank_name (optional), user_id (optional)
   - Returns: User settings, categorization rules, or parsing instructions

2. **save_preferences** - Save user settings, categorization rules, or parsing instructions
   - Use when persisting user data
   - Parameters: preferences (list), preference_type ("settings" | "categorization" | "parsing"), user_id (optional)

3. **get_financial_data** - Get dashboard data and financial summaries
   - Use when answering questions about spending, income, budgets, or showing dashboard
   - Parameters: user_id, bank_name, month_year, categories, profile, tab (all optional)

4. **save_statement_summary** - Save monthly statement summary
   - Use when user provides a bank statement CSV/Excel file
   - Parameters: category_summaries, bank_name, statement_net_flow, coverage_from, coverage_to, statement_insights, confirmation_text (optional), profile (optional), user_id (optional)

5. **mutate_categories** - Adjust category totals after data is saved
   - Use when reclassifying transactions or adjusting category amounts
   - Parameters: operations (list), bank_name (optional), month_year (optional), user_id (optional)

6. **save_budget** - Set or update budget targets
   - Use when user wants to set budget limits
   - Parameters: budgets (list), user_id (optional)

CURRENT USER CONTEXT:
- User ID: {user_id or "default"}

HOW TO USE TOOLS:
When you need to use a tool, describe what you want to do in your response. The system will interpret your intent and call the appropriate MCP tool on your behalf.

For example:
- "Let me check your current preferences" → will call fetch_preferences
- "I'll save this categorization rule" → will call save_preferences
- "Let me show you your spending breakdown" → will call get_financial_data

IMPORTANT:
- Always be helpful and conversational
- When user asks about their finances, use get_financial_data to get real data
- When user provides a statement file, guide them through the save_statement_summary workflow
- Never make up financial data - always use tools to get real information
"""
    return context.strip()


def call_cursor_agent_chat(
    message: str,
    user_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    model: str = "auto",
    timeout: int = 300
) -> Dict:
    """
    Call Cursor Agent for chat interface with MCP tool context.
    
    Args:
        message: User's chat message
        user_id: Current user ID
        conversation_history: Previous messages in format [{"role": "user|assistant", "content": "..."}]
        model: Model to use (default: "auto")
        timeout: Timeout in seconds (default: 300)
    
    Returns:
        Dict with response text and metadata
    """
    # Build MCP tool context
    mcp_context = build_mcp_tool_context(user_id)
    
    # Build conversation history
    history_text = ""
    if conversation_history:
        history_text = "\n\nPrevious conversation:\n"
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"{role.capitalize()}: {content}\n"
    
    # Build full prompt
    prompt = f"""{mcp_context}

{history_text}

Current user message: {message}

Please respond helpfully to the user's message. If you need to use any MCP tools, describe what you want to do and the system will execute the tool calls for you.
"""
    
    try:
        response = call_cursor_agent(prompt, model=model, stream=False, timeout=timeout)
        
        # Extract text response
        if isinstance(response, dict):
            if "text" in response:
                return {
                    "response": response["text"],
                    "raw": response
                }
            else:
                # Try to find text in response
                text = json.dumps(response, indent=2)
                return {
                    "response": text,
                    "raw": response
                }
        else:
            return {
                "response": str(response),
                "raw": response
            }
    except Exception as e:
        logger.error("Failed to call Cursor Agent for chat", {"error": str(e)})
        raise


async def call_cursor_agent_chat_stream(
    message: str,
    user_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    model: str = "auto",
    timeout: int = 300
) -> AsyncIterator[str]:
    """
    Call Cursor Agent for chat with streaming responses.
    
    Args:
        message: User's chat message
        user_id: Current user ID
        conversation_history: Previous messages
        model: Model to use (default: "auto")
        timeout: Timeout in seconds (default: 300)
    
    Yields:
        Text chunks as they arrive
    """
    cursor_path = settings.cursor_agent_path
    cmd = [cursor_path, "-p", "--model", model, "--output-format", "stream-json", "--stream-partial-output"]
    
    # Build MCP tool context
    mcp_context = build_mcp_tool_context(user_id)
    
    # Build conversation history
    history_text = ""
    if conversation_history:
        history_text = "\n\nPrevious conversation:\n"
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"{role.capitalize()}: {content}\n"
    
    # Build full prompt
    prompt = f"""{mcp_context}

{history_text}

Current user message: {message}

Please respond helpfully to the user's message. If you need to use any MCP tools, describe what you want to do and the system will execute the tool calls for you.
"""
    
    # Add API key if provided
    env = os.environ.copy()
    if settings.cursor_api_key:
        env["CURSOR_API_KEY"] = settings.cursor_api_key
    
    logger.info("Calling Cursor Agent for streaming chat", {
        "model": model,
        "message_length": len(message)
    })
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Send prompt
        if process.stdin:
            process.stdin.write(prompt.encode('utf-8'))
            await process.stdin.drain()
            process.stdin.close()
            await process.stdin.wait_closed()
        
        # Read output line by line
        accumulated_text = ""
        while True:
            line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=timeout
            )
            
            if not line:
                break
            
            line_str = line.decode('utf-8').strip()
            if not line_str:
                continue
            
            try:
                # Parse JSON line from stream-json format
                data = json.loads(line_str)
                
                # Extract text content from different message types
                if data.get("type") == "assistant":
                    content = data.get("message", {}).get("content", [])
                    if isinstance(content, list) and len(content) > 0:
                        text_content = content[0].get("text", "")
                        if text_content:
                            # Yield only new text (delta)
                            new_text = text_content[len(accumulated_text):]
                            if new_text:
                                accumulated_text = text_content
                                yield new_text
                elif data.get("type") == "result":
                    # Final result
                    result_text = data.get("result", "")
                    if result_text and result_text != accumulated_text:
                        new_text = result_text[len(accumulated_text):]
                        if new_text:
                            yield new_text
                    break
            except json.JSONDecodeError:
                # Not JSON, might be plain text
                if line_str:
                    yield line_str
        
        # Wait for process to complete
        await process.wait()
        
        if process.returncode != 0:
            stderr = await process.stderr.read()
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            logger.error("Cursor Agent stream failed", {
                "returncode": process.returncode,
                "stderr": error_msg
            })
            yield f"\n\n[Error: {error_msg}]"
            
    except asyncio.TimeoutError:
        logger.error("Cursor Agent stream timed out", {"timeout": timeout})
        yield "\n\n[Error: Request timed out]"
    except Exception as e:
        logger.error("Unexpected error in Cursor Agent stream", {"error": str(e)})
        yield f"\n\n[Error: {str(e)}]"


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
