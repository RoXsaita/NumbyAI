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
from typing import Dict, List, Optional, Union, Iterator, AsyncIterator, Callable, Any, Tuple
from app.config import settings
from app.logger import create_logger
from app.tools.category_helpers import PREDEFINED_CATEGORIES, normalize_category
from app.prompts import load_prompt, render_prompt
from app.services.categorization_rules import CategorizationRule, format_rules_for_prompt

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
    prompt = render_prompt(
        load_prompt("analyze_statement_structure.txt"),
        csv_sample=csv_sample,
    )
    
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


def _build_categorization_prompt(
    transactions: List[Dict],
    rules: List[CategorizationRule],
    prompt_name: str,
    extra_instructions: str = "",
) -> str:
    categories_str = ", ".join(PREDEFINED_CATEGORIES)
    rules_str = format_rules_for_prompt(rules)
    transactions_json = json.dumps(transactions, indent=2, default=str)
    template = load_prompt(prompt_name)
    return render_prompt(
        template,
        categories=categories_str,
        rules=rules_str,
        transactions=transactions_json,
        extra_instructions=extra_instructions,
    )


def _validate_categorization_results(
    transactions: List[Dict],
    categorized: List[Dict],
) -> Tuple[List[Dict[str, Any]], List[int], List[str]]:
    expected_ids = {tx.get("id") for tx in transactions}
    expected_ids.discard(None)
    seen_ids = set()
    normalized: List[Dict[str, Any]] = []
    errors: List[str] = []

    for item in categorized:
        if not isinstance(item, dict):
            errors.append("Invalid item type")
            continue
        item_id = item.get("id")
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            errors.append(f"Invalid id: {item.get('id')}")
            continue
        if item_id not in expected_ids:
            errors.append(f"Unexpected id: {item_id}")
            continue
        if item_id in seen_ids:
            errors.append(f"Duplicate id: {item_id}")
            continue
        category = normalize_category(str(item.get("category") or ""))
        if not category:
            errors.append(f"Invalid category for id {item_id}: {item.get('category')}")
            continue
        seen_ids.add(item_id)
        normalized.append({"id": item_id, "category": category})

    missing_ids = sorted(expected_ids - seen_ids)
    return normalized, missing_ids, errors


def categorize_transactions_batch(
    transactions: List[Dict],
    user_id: str,
    rules: List[CategorizationRule],
    batch_size: int = 20,
    parallel: bool = True,
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    prompt_variant: str = "default",
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
    
    def emit_progress(payload: Dict[str, Any]) -> None:
        if not progress_callback:
            return
        try:
            progress_callback(payload)
        except Exception as e:
            logger.warn("Progress callback failed", {"error": str(e)})

    worker_limit = max_workers if max_workers is not None else settings.categorization_max_workers
    worker_limit = max(1, worker_limit)
    worker_count = min(len(batches), worker_limit)

    logger.info("Categorizing transactions", {
        "total": len(transactions),
        "batches": len(batches),
        "batch_size": batch_size,
        "parallel": parallel,
        "max_workers": worker_count
    })

    emit_progress({
        "type": "categorization_start",
        "total_transactions": len(transactions),
        "total_batches": len(batches),
        "batch_size": batch_size,
        "parallel": parallel and len(batches) > 1,
        "max_workers": worker_count,
    })
    
    def categorize_single_batch(batch: List[Dict]) -> List[Dict]:
        """Categorize a single batch of transactions with validation retries."""
        max_attempts = 2
        attempt = 0
        last_normalized: List[Dict[str, Any]] = []
        missing_ids: List[int] = []
        errors: List[str] = []
        extra_instructions = ""

        while attempt < max_attempts:
            result = _categorize_batch_internal(
                batch,
                user_id,
                rules,
                prompt_variant,
                extra_instructions=extra_instructions,
            )
            normalized, missing_ids, errors = _validate_categorization_results(batch, result)
            if not errors and not missing_ids:
                return normalized
            attempt += 1
            last_normalized = normalized
            missing_text = ", ".join(str(mid) for mid in missing_ids)
            error_text = "; ".join(errors[:5])
            extra_instructions = (
                f"\nPrevious output had issues: {error_text}."
                f" Return categories for ALL transaction ids. Missing ids: {missing_text}."
            )

        if missing_ids:
            logger.warn("Categorization output incomplete after retries", {
                "missing_ids": missing_ids,
                "errors": errors,
            })
            for missing_id in missing_ids:
                last_normalized.append({"id": missing_id, "category": "Other"})

        return last_normalized

    if parallel and len(batches) > 1:
        # Process batches in parallel using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed

        all_results = []
        completed_batches = 0
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
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
                    completed_batches += 1
                    logger.info(f"Completed batch {batch_idx + 1}/{len(batches)}", {
                        "batch_size": len(batches[batch_idx]),
                        "categorized": len(result) if result else 0
                    })
                    emit_progress({
                        "type": "categorization_progress",
                        "completed_batches": completed_batches,
                        "total_batches": len(batches),
                        "batch_index": batch_idx + 1,
                        "categorized": len(result) if result else 0,
                    })
                except Exception as e:
                    logger.error(f"Batch {batch_idx + 1} failed", {"error": str(e)})
                    batch_results[batch_idx] = []
                    completed_batches += 1
                    emit_progress({
                        "type": "categorization_progress",
                        "completed_batches": completed_batches,
                        "total_batches": len(batches),
                        "batch_index": batch_idx + 1,
                        "categorized": 0,
                        "error": str(e),
                    })

            # Combine results in order
            for result in batch_results:
                if result:
                    all_results.extend(result)
    else:
        # Process sequentially
        all_results = []
        for idx, batch in enumerate(batches):
            try:
                result = categorize_single_batch(batch)
                all_results.extend(result)
                logger.info(f"Completed batch {idx + 1}/{len(batches)}", {
                    "batch_size": len(batch),
                    "categorized": len(result) if result else 0
                })
                emit_progress({
                    "type": "categorization_progress",
                    "completed_batches": idx + 1,
                    "total_batches": len(batches),
                    "batch_index": idx + 1,
                    "categorized": len(result) if result else 0,
                })
            except Exception as e:
                logger.error(f"Batch {idx + 1} failed", {"error": str(e)})
                emit_progress({
                    "type": "categorization_progress",
                    "completed_batches": idx + 1,
                    "total_batches": len(batches),
                    "batch_index": idx + 1,
                    "categorized": 0,
                    "error": str(e),
                })
    
    logger.info("Categorization complete", {
        "total_transactions": len(transactions),
        "categorized": len(all_results)
    })

    emit_progress({
        "type": "categorization_complete",
        "categorized": len(all_results),
        "total_batches": len(batches),
    })
    
    return all_results


def _categorize_batch_internal(
    transactions: List[Dict],
    user_id: str,
    rules: List[CategorizationRule],
    prompt_variant: str,
    extra_instructions: str = "",
) -> List[Dict]:
    """Internal function to categorize a single batch of transactions."""
    prompt_name = "categorize_transactions.txt"
    if prompt_variant == "retry":
        prompt_name = "categorize_transactions_retry.txt"
    prompt = _build_categorization_prompt(
        transactions,
        rules,
        prompt_name,
        extra_instructions=extra_instructions,
    )
    
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
        if isinstance(existing_rules[0], CategorizationRule):
            rules_str = format_rules_for_prompt(existing_rules)  # type: ignore[arg-type]
        else:
            rules_str = "\nExisting categorization rules (apply these first):\n"
            for rule in existing_rules:
                pattern = rule.get('merchant_pattern', '') if isinstance(rule, dict) else ''
                category = rule.get('category', '') if isinstance(rule, dict) else ''
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
    return render_prompt(
        load_prompt("mcp_tool_context.txt"),
        mcp_base_url=mcp_base_url,
        user_id=user_id or "default",
    ).strip()


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


def learn_merchant_rules(transactions: List, db, bank_name: Optional[str] = None) -> List:
    """
    Learn new merchant categorization preferences from transactions.

    Groups transactions by merchant + category, and if a merchant is categorized
    the same way 3+ times, creates a CategorizationPreference rule.

    Args:
        transactions: List of Transaction objects (already categorized)
        db: Database session
        bank_name: Optional bank name for bank-specific rules

    Returns:
        List of newly created preference objects
    """
    from app.database import CategorizationPreference
    from collections import defaultdict

    merchant_category_counts = defaultdict(int)

    for tx in transactions:
        if not tx.merchant or not tx.category or tx.category == "Other":
            continue
        key = (tx.merchant.lower(), tx.category)
        merchant_category_counts[key] += 1

    user_id = transactions[0].user_id if transactions else None
    if not user_id:
        return []

    new_rules = []
    for (merchant, category), count in merchant_category_counts.items():
        if count < 3:
            continue

        existing_prefs = db.query(CategorizationPreference).filter(
            CategorizationPreference.user_id == user_id,
            CategorizationPreference.preference_type == "categorization",
            CategorizationPreference.enabled.is_(True),
            CategorizationPreference.bank_name == bank_name,
        ).all()
        if any(
            isinstance(pref.rule, dict)
            and pref.rule.get("merchant_pattern") == merchant
            and pref.rule.get("category") == category
            for pref in existing_prefs
        ):
            continue

        rule = CategorizationPreference(
            user_id=user_id,
            name=f"auto:{merchant}",
            rule={"merchant_pattern": merchant, "category": category},
            bank_name=bank_name,
            priority=0,
            enabled=True,
            preference_type="categorization",
        )
        db.add(rule)
        new_rules.append(rule)
        logger.info("Learned new categorization preference", {
            "merchant": merchant,
            "category": category,
            "count": count,
        })

    if new_rules:
        db.commit()

    return new_rules
