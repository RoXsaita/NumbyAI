"""
MCP Tool Helper - Helper functions to call MCP tools from agent context

This module provides functions that can be called by the Cursor agent
to interact with MCP tools via HTTP requests.
"""
import os
import json
import httpx
from typing import Dict, Any, Optional
from app.config import settings
from app.logger import create_logger

logger = create_logger("mcp_tool_helper")


def get_mcp_server_url() -> str:
    """Get the MCP server URL"""
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    return f"{base_url}/mcp"


async def call_mcp_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call an MCP tool via HTTP.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments
        user_id: Optional user ID to include in context
    
    Returns:
        Tool result as dict
    """
    mcp_url = get_mcp_server_url()
    
    # Build MCP protocol request
    request_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    # Add user_id to arguments if provided
    if user_id and "user_id" not in arguments:
        arguments["user_id"] = user_id
    
    logger.info("Calling MCP tool", {
        "tool_name": tool_name,
        "user_id": user_id
    })
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                mcp_url,
                json=request_payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract result from MCP response
            if "result" in result:
                return result["result"]
            elif "error" in result:
                logger.error("MCP tool error", {
                    "tool_name": tool_name,
                    "error": result["error"]
                })
                return {"error": result["error"]}
            else:
                return result
                
    except httpx.HTTPError as e:
        logger.error("HTTP error calling MCP tool", {
            "tool_name": tool_name,
            "error": str(e)
        })
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        logger.error("Unexpected error calling MCP tool", {
            "tool_name": tool_name,
            "error": str(e)
        })
        return {"error": f"Unexpected error: {str(e)}"}


async def list_available_tools() -> list:
    """
    List all available MCP tools.
    
    Returns:
        List of tool names and descriptions
    """
    mcp_url = get_mcp_server_url()
    
    request_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                mcp_url,
                json=request_payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                return result["result"]["tools"]
            return []
    except Exception as e:
        logger.error("Failed to list MCP tools", {"error": str(e)})
        return []
