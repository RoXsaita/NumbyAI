"""Main MCP server entry point"""
import html
import json
import os
import textwrap
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from urllib.parse import urlparse


import mcp.types as types
from mcp.types import TextContent
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse, HTMLResponse, StreamingResponse
from starlette.requests import Request
from fastapi import UploadFile, File, Form
from dotenv import load_dotenv
import shutil
from datetime import datetime
import uuid

from app.config import settings
from app.logger import create_logger
from app.tools.save_statement_summary import save_statement_summary_handler
from app.tools.financial_data import get_financial_data_handler
from app.tools.category_helpers import PREDEFINED_CATEGORIES
from app.tools.fetch_preferences import fetch_preferences_handler
from app.tools.save_preferences import save_preferences_handler
from app.tools.mutate_categories import mutate_categories_handler
from app.tools.save_budget import save_budget_handler
# Tool descriptions are maintained in app/tools/tool_descriptions.py
# ALL tool descriptions MUST be defined there - do NOT hardcode descriptions in @mcp.tool decorators
from app.tools.tool_descriptions import (
    SAVE_STATEMENT_SUMMARY_DESCRIPTION,
    GET_FINANCIAL_DATA_DESCRIPTION,
    FETCH_PREFERENCES_DESCRIPTION,
    SAVE_PREFERENCES_DESCRIPTION,
    MUTATE_CATEGORIES_DESCRIPTION,
    SAVE_BUDGET_DESCRIPTION,
)
from app.services.cursor_agent_service import (
    call_cursor_agent,
    call_cursor_agent_chat,
    call_cursor_agent_chat_stream,
    categorize_transactions_batch,
    learn_merchant_rules
)
from app.services.statement_analyzer import (
    check_existing_parsing_preferences,
    analyze_statement_structure_from_file,
    build_parsing_schema,
    save_parsing_schema
)
from app.tools.statement_parser import (
    parse_csv_statement,
    extract_merchant,
    normalize_transaction
)
from app.database import (
    SessionLocal,
    Transaction,
    CategorizationRule,
    User,
    resolve_user_id,
    get_or_create_test_user
)
from app.auth import oauth2_auth
from jose import jwt
from datetime import datetime, timedelta

load_dotenv()

# Create logger for main module
logger = create_logger("main")

# Check if running in debug/development mode
IS_DEBUG = os.getenv("ENVIRONMENT", "").lower() != "production"

# Validate production settings on startup
settings.validate_production_settings()

MCP_SERVER_DESCRIPTION = """
Finance Budgeting App - parse, analyze, categorize, and save category summaries from bank statements.
"""

IS_SQLITE = settings.database_url.startswith("sqlite")

# Initialize FastMCP server
mcp = FastMCP(
    "finance-budgeting-app",
    stateless_http=True,
    streamable_http_path="/mcp"
)

mcp._mcp_server.description = textwrap.dedent(MCP_SERVER_DESCRIPTION).strip()


@mcp.custom_route("/", methods=["GET"])
async def root(request):
    """Serve the React frontend app"""
    index_path = WEB_DIST_PATH / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    # Fallback if frontend not built yet
    return JSONResponse(
        {
            "status": "ok",
            "message": "Finance Budgeting App MCP server",
            "endpoints": {
                "mcp": "/mcp",
                "health": "/health",
                "widgets": "/widgets",
                "app": "/ (React frontend)",
            },
            "note": "Run 'cd web && npm run build:app' to build the frontend app",
        }
    )


@mcp.custom_route("/mcp", methods=["GET"])
async def mcp_info(request):
    """Surface basic MCP info for scanners performing GET checks."""
    return JSONResponse(
        {
            "status": "ok",
            "message": "MCP endpoint (POST for tool calls, GET for health)",
            "name": mcp._mcp_server.name,
            "description": mcp._mcp_server.description,
        }
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    """Health check endpoint"""
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/debug/list-tools", methods=["GET"])
async def debug_list_tools(request):
    """Debug endpoint to list all registered tools and their schemas"""
    try:
        tools = []
        for tool in mcp._mcp_server._tool_manager._tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description[:200] + "..." if len(tool.description) > 200 else tool.description,
                "inputSchema": tool.inputSchema
            })
        return JSONResponse({"tools": tools})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/widgets", methods=["GET"])
async def widget_selector(request):
    """Widget selector page - lists all available widgets"""
    widgets_html = ""
    for name, config in WIDGET_CONFIG.items():
        # Escape values to prevent XSS when rendering HTML
        safe_name = html.escape(name)
        safe_title = html.escape(config.get("title", name))
        safe_description = html.escape(config.get("description", ""))
        widgets_html += f"""
        <div class="widget-card">
            <h3>{safe_title}</h3>
            <p>{safe_description}</p>
            <div class="button-group">
                <a href="/test-widget?widget={safe_name}&inline=1" class="button primary">View Widget</a>
                <a href="/test-widget?widget={safe_name}" class="button secondary">External Assets</a>
            </div>
        </div>
        """

    html_content = f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Widget Selector - Finance App</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 48px;
        }}
        .header h1 {{
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 12px;
        }}
        .header p {{
            font-size: 18px;
            opacity: 0.9;
        }}
        .widgets-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 24px;
        }}
        .widget-card {{
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .widget-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
        }}
        .widget-card h3 {{
            font-size: 24px;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 12px;
        }}
        .widget-card p {{
            font-size: 14px;
            color: #4a5568;
            line-height: 1.6;
            margin-bottom: 24px;
            min-height: 60px;
        }}
        .button-group {{
            display: flex;
            gap: 12px;
        }}
        .button {{
            flex: 1;
            padding: 12px 20px;
            text-decoration: none;
            text-align: center;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s;
            display: inline-block;
        }}
        .button.primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .button.primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        .button.secondary {{
            background: #edf2f7;
            color: #4a5568;
        }}
        .button.secondary:hover {{
            background: #e2e8f0;
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 48px;
            opacity: 0.8;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 Widget Gallery</h1>
            <p>Select a widget to preview</p>
        </div>
        <div class="widgets-grid">
            {widgets_html}
        </div>
        <div class="footer">
            <p>Finance Budgeting App · MCP Server</p>
        </div>
    </div>
</body>
</html>"""

    return HTMLResponse(html_content)


@mcp.custom_route("/test-widget", methods=["GET"])
async def test_widget(request):
    """Test/preview widget in browser with real database data"""
    widget_name = request.query_params.get("widget", "dashboard")
    force_inline = "inline" in request.query_params
    statement_id = request.query_params.get("statement_id")
    
    config = WIDGET_CONFIG.get(widget_name)
    if not config:
        return JSONResponse(
            {"error": f"Widget '{widget_name}' not found", "available": list(WIDGET_CONFIG.keys())},
            status_code=404
        )
    
    try:
        html, _ = generate_widget_html(widget_name, config, force_inline=bool(force_inline))
        
        # Inject real database data for widgets
        if widget_name == "dashboard":
            from app.database import get_or_create_test_user

            user_id = get_or_create_test_user()
            result = get_financial_data_handler(user_id=user_id)

            # Get _meta (full payload for widget) and structuredContent (lighter for AI)
            meta_content = result.get("_meta", {})
            structured_content = result.get("structuredContent", {
                "kind": "dashboard",
                "message": "No data available. Upload a statement to get started.",
            })

            data_script = f"""
        <script>
          // Real database data - widget reads from toolResponseMetadata first, falls back to toolOutput
          window.openai = {{
            toolOutput: {json.dumps(structured_content, default=str)},
            toolResponseMetadata: {json.dumps(meta_content, default=str)}
          }};
        </script>
        """
            # Insert data script before closing </body>
            html = html.replace("</body>", data_script + "\n</body>")
        
        return HTMLResponse(html)
    except Exception as e:
        logger.error("Widget rendering failed", {"error": str(e)})
        error_response = {"error": str(e)}
        # Only include traceback in debug/development mode
        if IS_DEBUG:
            error_response["traceback"] = traceback.format_exc()
        return JSONResponse(error_response, status_code=500)


WEB_ROOT = Path(__file__).parent.parent.parent / "web"
WEB_DIST_PATH = WEB_ROOT / "dist"
WIDGETS_CONFIG_PATH = WEB_ROOT / "widgets.config.json"
WIDGET_MANIFEST_PATH = WEB_DIST_PATH / "widget-manifest.json"

if not WIDGETS_CONFIG_PATH.exists():
    raise FileNotFoundError(
        f"Missing widget config file at {WIDGETS_CONFIG_PATH}. "
        "Ensure web/widgets.config.json exists."
    )

with WIDGETS_CONFIG_PATH.open(encoding="utf-8") as cfg_file:
    _widget_definitions: List[Dict[str, Any]] = json.load(cfg_file)

WIDGET_CONFIG: Dict[str, Dict[str, Any]] = {
    widget["name"]: widget for widget in _widget_definitions
}

_WIDGET_MANIFEST_CACHE: Optional[Dict[str, str]] = None
_WIDGET_MANIFEST_MTIME: Optional[float] = None


def _load_widget_manifest() -> Dict[str, str]:
    """Load the widget manifest that maps entry names to hashed asset files."""
    global _WIDGET_MANIFEST_CACHE, _WIDGET_MANIFEST_MTIME
    
    try:
        stat = WIDGET_MANIFEST_PATH.stat()
    except FileNotFoundError:
        logger.warn("Widget manifest not found", {"path": str(WIDGET_MANIFEST_PATH), "hint": "Run 'cd web && npm run build'"})
        return {}
    
    if (
        _WIDGET_MANIFEST_CACHE is None
        or _WIDGET_MANIFEST_MTIME is None
        or stat.st_mtime != _WIDGET_MANIFEST_MTIME
    ):
        with WIDGET_MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
            _WIDGET_MANIFEST_CACHE = json.load(manifest_file)
            _WIDGET_MANIFEST_MTIME = stat.st_mtime
            logger.info("Loaded widget manifest", {"path": str(WIDGET_MANIFEST_PATH)})
    
    return _WIDGET_MANIFEST_CACHE or {}


def get_widget_base_url() -> str:
    """Return the absolute base URL for static widget assets."""
    base_url = (
        settings.widget_base_url
        or os.getenv("WIDGET_BASE_URL")
        or os.getenv("BASE_URL")
    )
    if base_url:
        base_url = base_url.rstrip("/")
        logger.info("Using widget base URL", {"base_url": base_url})
        return base_url
    default_url = "http://localhost:8000/static"
    logger.warn("No BASE_URL set, using default", {"default_url": default_url})
    return default_url


def resolve_widget_asset(config: Dict[str, Any]) -> str:
    """Resolve the hashed asset filename for a widget entry."""
    asset_override = config.get("asset_file")
    if asset_override:
        return asset_override
    
    manifest = _load_widget_manifest()
    entry_name = config.get("entry")
    asset = manifest.get(entry_name)
    if not asset:
        raise FileNotFoundError(
            f"Asset for widget entry '{entry_name}' not found. "
            "Ensure 'npm run build' has been executed in the web/ directory."
        )
    return asset.lstrip("/")


def build_widget_csp() -> Dict[str, List[str]]:
    """Build CSP metadata that allows ChatGPT to load widget assets."""
    base_url = get_widget_base_url()
    resource_domains: List[str] = []
    
    if base_url.startswith("http"):
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        resource_domains.append(origin)
    
    return {
        "connect_domains": [],
        "resource_domains": resource_domains,
    }


def read_widget_asset(asset_filename: str) -> str:
    """Read the built widget asset contents."""
    asset_path = WEB_DIST_PATH / asset_filename
    if not asset_path.exists():
        raise FileNotFoundError(
            f"Widget asset '{asset_filename}' not found in {asset_path.parent}. "
            "Re-run 'cd web && npm run build'."
        )
    return asset_path.read_text(encoding="utf-8")


def _sanitize_inline_js(js_code: str) -> str:
    """Ensure inline JS doesn't prematurely close the script tag."""
    return js_code.replace("</script>", "<\\/script>")


WIDGETS_BY_URI: dict[str, dict[str, Any]] = {}
RESOURCE_ALIAS_MAP: Dict[str, str] = {}
WIDGET_TEMPLATE_URIS: Dict[str, str] = {}
LEGACY_WIDGET_URIS: Dict[str, str] = {}


def generate_widget_html(widget_name: str, config: Dict[str, Any], force_inline: bool = False) -> tuple[str, bool]:
    """Generate HTML for a widget."""
    root_id = config["root_id"]
    title = config.get("title", widget_name)
    asset_file = resolve_widget_asset(config)
    base_url = get_widget_base_url()
    script_url = None
    use_external_asset = False
    
    if base_url and not force_inline:
        base_url = base_url.rstrip("/")
        script_candidate = f"{base_url}/{asset_file.lstrip('/')}"
        try:
            parsed = urlparse(script_candidate)
            if parsed.scheme in {"http", "https"} and parsed.hostname not in {"localhost", "127.0.0.1"}:
                # Check if the external URL is accessible before using it
                try:
                    import urllib.request
                    req = urllib.request.Request(script_candidate, method='HEAD')
                    req.add_header('User-Agent', 'Mozilla/5.0')
                    with urllib.request.urlopen(req, timeout=2) as response:
                        if response.status == 200:
                            script_url = script_candidate
                            use_external_asset = True
                            logger.info("External asset accessible", {"url": script_candidate})
                        else:
                            logger.warn("External asset returned non-200 status", {"url": script_candidate, "status": response.status})
                except Exception as e:
                    logger.warn("External asset not accessible", {"url": script_candidate, "error": str(e)})
                    script_url = None
            else:
                # Localhost URLs - use them directly without checking
                script_url = script_candidate
                use_external_asset = True
        except Exception:
            script_url = None
    
    # Add Vega libraries for dashboard widget in head (load before React)
    # Load without defer to ensure they're available before React executes
    vega_scripts = ""
    if widget_name == "dashboard":
        vega_scripts = """
  <script src="https://cdn.jsdelivr.net/npm/vega@5.28.0/build/vega.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5.18.0/build/vega-lite.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6.24.0/build/vega-embed.min.js"></script>"""
    
    if script_url:
        script_block = f'<script defer type="module" src="{script_url}"></script>'
    else:
        inline_js = _sanitize_inline_js(read_widget_asset(asset_file))
        script_block = f"<script defer type=\"module\">\n{textwrap.indent(inline_js, '    ')}\n  </script>"
    
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>{vega_scripts}
</head>
<body>
  <div id="{root_id}"></div>
  {script_block}
</body>
</html>"""
    
    return textwrap.dedent(html).strip(), use_external_asset and not force_inline


def register_widget(widget_name: str):
    """Register a widget by storing it in WIDGETS_BY_URI dictionary"""
    config = WIDGET_CONFIG.get(widget_name)
    if not config:
        logger.error("Widget not configured", {"widget_name": widget_name})
        return
    
    asset_file = resolve_widget_asset(config)
    version_tag = config.get("template_version")
    if not version_tag:
        version_tag = asset_file.replace(".js", "").split("-", 1)[-1]
        config["template_version"] = version_tag
    template_uri = f"ui://widget/{widget_name}-{version_tag}.html"
    config["template_uri"] = template_uri
    config["asset_file"] = asset_file
    
    WIDGETS_BY_URI[template_uri] = {
        "config": config,
        "name": widget_name,
        "title": config["description"].split(".")[0] if config.get("description") else widget_name,
    }
    WIDGET_TEMPLATE_URIS[widget_name] = template_uri
    RESOURCE_ALIAS_MAP[widget_name] = template_uri
    RESOURCE_ALIAS_MAP[widget_name.replace("_", "-")] = template_uri
    
    legacy_uri = f"ui://widget/{widget_name}.html"
    LEGACY_WIDGET_URIS[legacy_uri] = template_uri


def widget_template(name: str) -> str:
    return WIDGET_TEMPLATE_URIS.get(name, f"ui://widget/{name}.html")


def build_structured_call_result(result: Dict[str, Any]) -> types.CallToolResult:
    structured = result.get("structuredContent")
    if structured is None:
        raise ValueError("structuredContent missing from tool handler result")
    
    raw_content = result.get("content") or []
    content_items: List[TextContent] = []
    for item in raw_content:
        if isinstance(item, TextContent):
            content_items.append(item)
        elif isinstance(item, dict):
            content_items.append(TextContent(type=item.get("type", "text"), text=item.get("text", "")))
            
    meta = result.get("_meta")
    return types.CallToolResult(content=content_items, structuredContent=structured, _meta=meta)


# Register all widgets
for widget_def in _widget_definitions:
    register_widget(widget_def["name"])


@mcp._mcp_server.list_resources()
async def _list_resources() -> List[types.Resource]:
    """List all available resources"""
    resources = []
    
    for uri, widget_data in WIDGETS_BY_URI.items():
        resources.append(
            types.Resource(
                name=widget_data["name"],
                title=widget_data["title"],
                uri=uri,
                description=widget_data["config"]["description"],
                mimeType="text/html+skybridge",
                _meta={
                    "openai/widgetDescription": widget_data["config"]["description"]
                }
            )
        )
    
    return resources


@mcp._mcp_server.list_resource_templates()
async def _list_resource_templates() -> List[types.ResourceTemplate]:
    """List all available resource templates"""
    templates = []
    
    for uri, widget_data in WIDGETS_BY_URI.items():
        templates.append(
            types.ResourceTemplate(
                name=widget_data["name"],
                title=widget_data["title"],
                uriTemplate=uri,
                description=widget_data["config"]["description"],
                mimeType="text/html+skybridge",
                _meta={
                    "openai/widgetDescription": widget_data["config"]["description"]
                }
            )
        )
    
    return templates


async def _handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    """Handle resource read requests - returns widget HTML"""
    raw_uri = str(req.params.uri)
    uri = raw_uri
    
    if uri.startswith("Finance-App/"):
        parts = uri.split("/")
        if len(parts) >= 3 and parts[1].startswith("link_"):
            uri = "/".join(parts[2:])
        else:
            uri = "/".join(parts[1:])
    
    if uri in LEGACY_WIDGET_URIS:
        uri = LEGACY_WIDGET_URIS[uri]
    
    if not uri.startswith("ui://widget"):
        alias = uri.split("/")[-1]
        normalized = alias.replace("-", "_")
        mapped_template = RESOURCE_ALIAS_MAP.get(normalized)
        if mapped_template:
            uri = mapped_template
    
    widget_data = WIDGETS_BY_URI.get(uri)
    if widget_data:
        try:
            # Force inline JS to avoid CSP/loading issues with ChatGPT
            html, uses_external = generate_widget_html(widget_data["name"], widget_data["config"], force_inline=True)
        except FileNotFoundError as exc:
            logger.error("Widget asset not found", {"error": str(exc)})
            html = textwrap.dedent(
                f"""<!doctype html>
<html>
<body>
  <p>{exc}</p>
</body>
</html>"""
            ).strip()
            uses_external = False
        
        widget_meta = {
            "openai/widgetDescription": widget_data["config"]["description"],
            "openai/widgetPrefersBorder": True,
        }
        # Configure CSP to allow necessary functionality
        widget_meta["openai/widgetCSP"] = {
            "connect_domains": [],
            "resource_domains": [],
            "script_src": ["'unsafe-eval'"],  # Allow eval for React and dynamic functionality
        }
        
        contents = [
            types.TextResourceContents(
                uri=uri,
                mimeType="text/html+skybridge",
                text=html,
                _meta=widget_meta
            )
        ]
        return types.ServerResult(types.ReadResourceResult(contents=contents))
    
    return types.ServerResult(
        types.ReadResourceResult(
            contents=[],
            _meta={"error": f"Unknown resource: {uri}"}
        )
    )


mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _handle_read_resource


# Register MCP tools

@mcp.tool(
    name="save_statement_summary",
    description=SAVE_STATEMENT_SUMMARY_DESCRIPTION,
    meta={
        "openai/toolInvocation/invoking": "Saving statement summary...",
        "openai/toolInvocation/invoked": "Statement summary saved",
        "readOnlyHint": False
    }
)
async def save_statement_summary(
    category_summaries: list[dict],
    bank_name: str,
    statement_net_flow: float,
    confirmation_text: Optional[str] = None,
    statement_insights: Optional[str] = None,
    coverage_from: str = "",
    coverage_to: str = "",
    profile: Optional[str] = None,
    user_id: Optional[str] = None
) -> types.CallToolResult:
    result = await save_statement_summary_handler(
        category_summaries=category_summaries,
        bank_name=bank_name,
        statement_net_flow=statement_net_flow,
        confirmation_text=confirmation_text,
        statement_insights=statement_insights,
        coverage_from=coverage_from,
        coverage_to=coverage_to,
        profile=profile,
        user_id=user_id
    )
    if "structuredContent" not in result:
        raise ValueError("save_statement_summary_handler missing structuredContent")
    return build_structured_call_result(result)


@mcp.tool(
    name="get_financial_data",
    description=GET_FINANCIAL_DATA_DESCRIPTION,
    meta={
        "openai/outputTemplate": widget_template("dashboard"),
        "openai/toolInvocation/invoking": "Retrieving financial data...",
        "openai/toolInvocation/invoked": "Financial data ready",
        "readOnlyHint": True
    },
)
async def get_financial_data(
    user_id: Optional[str] = None,
    bank_name: Optional[str] = None,
    month_year: Optional[str] = None,
    categories: Optional[List[str]] = None,
    profile: Optional[str] = None,
    tab: Optional[str] = None,
) -> types.CallToolResult:
    """Retrieve financial data and render dashboard"""
    result = get_financial_data_handler(
        user_id=user_id,
        bank_name=bank_name,
        month_year=month_year,
        categories=categories,
        profile=profile,
        tab=tab,
    )
    if "structuredContent" not in result:
        raise ValueError("get_financial_data_handler missing structuredContent")
    return build_structured_call_result(result)


@mcp.tool(
    name="fetch_preferences",
    description=FETCH_PREFERENCES_DESCRIPTION,
    meta={
        "openai/toolInvocation/invoking": "Fetching preferences...",
        "openai/toolInvocation/invoked": "Preferences loaded",
        "readOnlyHint": True
    }
)
async def fetch_preferences(
    preference_type: Union[str, List[str]] = "categorization",
    bank_name: Optional[str] = None,
    user_id: Optional[str] = None
) -> types.CallToolResult:
    """Fetch preferences (categorization rules, parsing instructions, or list summary). Can fetch multiple types at once."""
    result = await fetch_preferences_handler(
        preference_type=preference_type,
        bank_name=bank_name,
        user_id=user_id
    )
    if "structuredContent" not in result:
        raise ValueError("fetch_preferences_handler missing structuredContent")
    return build_structured_call_result(result)


@mcp.tool(
    name="save_preferences",
    description=SAVE_PREFERENCES_DESCRIPTION,
    meta={
        "openai/toolInvocation/invoking": "Saving preferences...",
        "openai/toolInvocation/invoked": "Preferences saved",
        "readOnlyHint": False
    }
)
async def save_preferences(
    preferences: list,
    preference_type: str = "categorization",
    user_id: Optional[str] = None
) -> types.CallToolResult:
    """Save preferences (categorization rules or parsing instructions)"""
    result = await save_preferences_handler(
        preferences=preferences,
        preference_type=preference_type,
        user_id=user_id
    )
    if "structuredContent" not in result:
        raise ValueError("save_preferences_handler missing structuredContent")
    return build_structured_call_result(result)


@mcp.tool(
    name="mutate_categories",
    description=MUTATE_CATEGORIES_DESCRIPTION,
    meta={
        "openai/toolInvocation/invoking": "Mutating categories...",
        "openai/toolInvocation/invoked": "Categories updated",
        "readOnlyHint": False
    }
)
async def mutate_categories(
    operations: list[dict],
    user_id: Optional[str] = None,
    bank_name: Optional[str] = None,
    month_year: Optional[str] = None,
) -> types.CallToolResult:
    """Mutate category totals through edit operations only."""
    result = mutate_categories_handler(
        operations=operations,
        user_id=user_id,
        bank_name=bank_name,
        month_year=month_year,
    )
    
    # Build lean text response with just the changes
    updated_categories = result.get("updated_categories", {})
    change_summary = result.get("change_summary", [])
    status = result.get("status", "unknown")
    
    # Format response text
    lines = []
    if status == "success" and updated_categories:
        lines.append("✓ Categories updated:")
        for cat, amount in updated_categories.items():
            lines.append(f"  • {cat}: {amount:,.2f}")
    elif status == "error":
        lines.append("✗ Mutation failed:")
        for change in change_summary:
            if change.get("status") == "error":
                lines.append(f"  • {change.get('message', 'Unknown error')}")
    else:
        lines.append("No changes applied.")
    
    return types.CallToolResult(
        content=[TextContent(type="text", text="\n".join(lines))],
        _meta={"change_summary": change_summary, "updated_categories": updated_categories},
    )


@mcp.tool(
    name="save_budget",
    description=SAVE_BUDGET_DESCRIPTION,
    meta={
        "openai/toolInvocation/invoking": "Saving budgets...",
        "openai/toolInvocation/invoked": "Budgets saved",
        "readOnlyHint": False
    }
)
async def save_budget(
    budgets: list[dict],
    user_id: Optional[str] = None,
) -> types.CallToolResult:
    """Save or update budget targets"""
    result = await save_budget_handler(
        budgets=budgets,
        user_id=user_id,
    )
    if "structuredContent" not in result:
        raise ValueError("save_budget_handler missing structuredContent")
    return build_structured_call_result(result)


# ============================================================================
# REST API ENDPOINTS FOR STANDALONE WEB APP
# ============================================================================

# Create uploads directory if it doesn't exist
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


# Store conversation history per user (in production, use Redis or database)
_conversation_history: Dict[str, List[Dict[str, str]]] = {}


@mcp.custom_route("/api/chat/messages", methods=["POST"])
async def send_chat_message(request: Request):
    """Send message to AI chat, handle file uploads, trigger flows"""
    try:
        # Handle FormData (frontend sends FormData)
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            form = await request.form()
            message = form.get("message", "")
            file = form.get("file")  # File object
            net_flow = form.get("net_flow")
            user_id = form.get("user_id")
        else:
            # Fallback to JSON
            data = await request.json()
            message = data.get("message", "")
            file = data.get("file")
            net_flow = data.get("net_flow")
            user_id = data.get("user_id")
        
        # Get or create user
        if not user_id:
            user_id = get_or_create_test_user()
        
        # Get conversation history for this user
        history = _conversation_history.get(user_id, [])
        
        # Handle file uploads (for now, just mention it in the message)
        if file:
            if isinstance(file, UploadFile):
                message = f"User uploaded file: {file.filename}. {message}"
            else:
                message = f"User uploaded file. {message}"
        
        # Add user message to history
        history.append({"role": "user", "content": message})
        
        # Call Cursor Agent
        try:
            response = call_cursor_agent_chat(
                message=message,
                user_id=user_id,
                conversation_history=history
            )
            
            assistant_response = response.get("response", "I'm sorry, I couldn't generate a response.")
            
            # Add assistant response to history
            history.append({"role": "assistant", "content": assistant_response})
            _conversation_history[user_id] = history[-10:]  # Keep last 10 messages
            
            # Generate message ID for potential streaming
            message_id = str(uuid.uuid4())
            
            return JSONResponse({
                "message_id": message_id,
                "response": assistant_response
            })
        except Exception as e:
            logger.error("Cursor Agent call failed", {"error": str(e), "traceback": traceback.format_exc()})
            return JSONResponse({
                "error": f"Failed to process message: {str(e)}"
            }, status_code=500)
            
    except Exception as e:
        logger.error("Chat message error", {"error": str(e), "traceback": traceback.format_exc()})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/chat/stream", methods=["GET"])
async def stream_chat_response(request: Request):
    """Server-Sent Events endpoint for streaming AI responses"""
    message_id = request.query_params.get("message_id")
    user_message = request.query_params.get("message", "")
    user_id = request.query_params.get("user_id")
    
    if not user_id:
        user_id = get_or_create_test_user()
    
    # Get conversation history
    history = _conversation_history.get(user_id, [])
    
    async def generate():
        try:
            # Add user message to history
            if user_message:
                history.append({"role": "user", "content": user_message})
            
            # Stream response from Cursor Agent
            accumulated_text = ""
            async for chunk in call_cursor_agent_chat_stream(
                message=user_message,
                user_id=user_id,
                conversation_history=history
            ):
                accumulated_text += chunk
                # Send chunk as SSE event
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            
            # Add complete response to history
            if accumulated_text:
                history.append({"role": "assistant", "content": accumulated_text})
                _conversation_history[user_id] = history[-10:]  # Keep last 10 messages
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error("Streaming error", {"error": str(e), "traceback": traceback.format_exc()})
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@mcp.custom_route("/api/statements/upload", methods=["POST"])
async def upload_statement(request: Request):
    """Upload and parse bank statement (CSV/Excel) - Enhanced with validation info"""
    try:
        user_id = get_or_create_test_user()  # TODO: Get from auth
        
        # Handle multipart form data
        form = await request.form()
        file = form.get("file")
        bank_name = form.get("bank_name")  # Extract bank_name from form
        
        if not file:
            return JSONResponse({"error": "No file provided"}, status_code=400)
        
        # Get filename - handle both UploadFile and regular file objects
        filename = getattr(file, 'filename', None) or 'statement.csv'
        if hasattr(file, 'file'):
            file_obj = file.file
        else:
            file_obj = file
        
        # Save file temporarily
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_upload_dir = UPLOADS_DIR / user_id
        user_upload_dir.mkdir(exist_ok=True)
        
        file_path = user_upload_dir / f"{timestamp}_{filename}"
        
        with open(file_path, "wb") as buffer:
            if hasattr(file_obj, 'read'):
                shutil.copyfileobj(file_obj, buffer)
            else:
                # Handle case where file is already bytes
                buffer.write(file_obj.read() if hasattr(file_obj, 'read') else file_obj)
        
        logger.info("File uploaded", {
            "filename": filename,
            "path": str(file_path),
            "user_id": user_id
        })
        
        # Check user settings for currency
        from app.database import CategorizationPreference
        db = SessionLocal()
        try:
            settings_pref = db.query(CategorizationPreference).filter(
                CategorizationPreference.user_id == user_id,
                CategorizationPreference.preference_type == "settings",
                CategorizationPreference.name == "user_settings",
                CategorizationPreference.enabled.is_(True)
            ).first()
            user_currency = None
            if settings_pref and settings_pref.rule:
                user_currency = settings_pref.rule.get("functional_currency")
        finally:
            db.close()
        
        # Check for existing parsing preferences
        parsing_preferences_exist = False
        saved_mappings = None
        if bank_name:
            existing_schema = check_existing_parsing_preferences(bank_name, user_id)
            if existing_schema:
                parsing_preferences_exist = True
                saved_mappings = existing_schema
                # Parse directly using existing schema
                transactions = parse_csv_statement(str(file_path), existing_schema)
                
                # Also return preview data for consistency
                preview_data = []
                total_rows = 0
                total_columns = 0
                try:
                    import pandas as pd
                    # Read without headers to show raw file content
                    df_preview = pd.read_csv(str(file_path), nrows=30, dtype=str, keep_default_na=False, header=None)
                    preview_data = df_preview.values.tolist()
                    total_rows = len(pd.read_csv(str(file_path), dtype=str, header=None))
                    total_columns = len(df_preview.columns) if len(df_preview) > 0 else 0
                except Exception as e:
                    logger.warn("Failed to read preview data for existing bank", {"error": str(e)})
                
                return JSONResponse({
                    "job_id": str(uuid.uuid4()),
                    "status": "ready_to_process",
                    "transactions_count": len(transactions),
                    "transactions": transactions[:10],  # Return first 10 for preview
                    "currency_detected": existing_schema.get("currency"),
                    "currency_required": not bool(user_currency),
                    "parsing_preferences_exist": True,
                    "detected_headers": list(existing_schema.get("column_mappings", {}).keys()) if existing_schema else [],
                    "preview_data": preview_data,
                    "total_rows": total_rows,
                    "total_columns": total_columns,
                    "saved_mappings": saved_mappings  # Include saved mappings for auto-population
                })
        
        # Analyze statement structure
        analysis = analyze_statement_structure_from_file(str(file_path), user_id)
        
        # Extract detected headers and preview data from CSV
        detected_headers = []
        preview_data = []
        total_rows = 0
        total_columns = 0
        try:
            import pandas as pd
            # Read without headers to show raw file content exactly as-is
            # This allows users to see the actual first row (whether it's headers or data)
            df_preview = pd.read_csv(str(file_path), nrows=30, dtype=str, keep_default_na=False, header=None)
            total_rows = len(df_preview)
            
            # Convert to 2D array (list of lists)
            preview_data = df_preview.values.tolist()
            
            # Get total row count and column count from file
            df_full = pd.read_csv(str(file_path), dtype=str, header=None)
            total_rows = len(df_full)
            total_columns = len(df_preview.columns) if len(df_preview) > 0 else 0
            
            # For backward compatibility, still provide detected_headers as first row if it looks like headers
            # But this is optional - users will work with numeric column indices
            detected_headers = preview_data[0] if preview_data else []
        except Exception as e:
            logger.warn("Failed to read CSV headers/preview", {"error": str(e)})
        
        # Extract currency from analysis
        currency_detected = analysis.get("currency")
        
        # Check if bank has saved preferences (even if not provided in upload)
        saved_mappings = None
        if bank_name:
            existing_schema = check_existing_parsing_preferences(bank_name, user_id)
            if existing_schema:
                saved_mappings = existing_schema
        
        return JSONResponse({
            "job_id": str(uuid.uuid4()),
            "status": "validation_required",
            "analysis": analysis,
            "file_path": str(file_path),
            "currency_detected": currency_detected,
            "currency_required": not bool(user_currency),
            "parsing_preferences_exist": bool(saved_mappings),
            "detected_headers": detected_headers,
            "preview_data": preview_data,
            "total_rows": total_rows,
            "total_columns": total_columns,
            "saved_mappings": saved_mappings  # Include saved mappings for auto-population
        })
        
    except Exception as e:
        logger.error("File upload error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/statements/process", methods=["POST"])
async def process_statement_automatically(request: Request):
    """
    AUTOMATIC statement processing: upload → parse → categorize → save → dashboard
    
    This endpoint handles the entire workflow automatically:
    1. Uploads and parses the statement
    2. Categorizes all transactions (in parallel)
    3. Saves the statement summary
    4. Returns dashboard data
    
    Accepts optional header_mapping JSON string from frontend.
    """
    try:
        user_id = get_or_create_test_user()
        
        # Handle multipart form data
        form = await request.form()
        file = form.get("file")
        bank_name = form.get("bank_name")
        net_flow_str = form.get("net_flow")
        header_mapping = form.get("header_mapping")
        
        if not file:
            return JSONResponse({"error": "No file provided"}, status_code=400)
        
        # Get filename - handle both UploadFile and regular file objects
        filename = getattr(file, 'filename', None) or 'statement.csv'
        if hasattr(file, 'file'):
            file_obj = file.file
        else:
            file_obj = file
        
        net_flow = None
        if net_flow_str:
            try:
                net_flow = float(net_flow_str)
            except (ValueError, TypeError):
                pass
        
        # Step 1: Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_upload_dir = UPLOADS_DIR / user_id
        user_upload_dir.mkdir(exist_ok=True)
        file_path = user_upload_dir / f"{timestamp}_{filename}"
        
        with open(file_path, "wb") as buffer:
            if hasattr(file_obj, 'read'):
                shutil.copyfileobj(file_obj, buffer)
            else:
                # Handle case where file is already bytes
                buffer.write(file_obj.read() if hasattr(file_obj, 'read') else file_obj)
        
        logger.info("Auto-processing statement", {
            "filename": filename,
            "bank_name": bank_name,
            "user_id": user_id,
            "has_header_mapping": bool(header_mapping)
        })
        
        # Step 2: Get or create parsing schema
        schema = None
        if bank_name:
            schema = check_existing_parsing_preferences(bank_name, user_id)
        
        if not schema:
            # Check if header mapping was provided from frontend
            if header_mapping:
                try:
                    mapping_data = json.loads(header_mapping)
                    # Get user currency
                    from app.database import CategorizationPreference
                    db = SessionLocal()
                    try:
                        settings_pref = db.query(CategorizationPreference).filter(
                            CategorizationPreference.user_id == user_id,
                            CategorizationPreference.preference_type == "settings",
                            CategorizationPreference.name == "user_settings",
                            CategorizationPreference.enabled.is_(True)
                        ).first()
                        currency = "USD"
                        if settings_pref and settings_pref.rule:
                            currency = settings_pref.rule.get("functional_currency", "USD")
                    finally:
                        db.close()
                    
                    # Build schema from user mapping (new structure with column_mappings dict)
                    column_mappings = mapping_data.get("column_mappings", {})
                    if not column_mappings:
                        # Fallback: try to build from old format
                        description_col = mapping_data.get("description_column", "")
                        if isinstance(description_col, str):
                            description_col = [description_col] if description_col else []
                        elif not isinstance(description_col, list):
                            description_col = []
                        column_mappings = {
                            "date": mapping_data.get("date_column", ""),
                            "description": description_col,
                            "amount": mapping_data.get("amount_column", ""),
                        }
                        if mapping_data.get("balance_column"):
                            column_mappings["balance"] = mapping_data["balance_column"]
                    
                    schema = {
                        "column_mappings": column_mappings,
                        "date_format": mapping_data.get("date_format", "DD/MM/YYYY"),
                        "currency": currency,
                        "has_headers": False,  # Always false - we use first_transaction_row instead
                        "skip_rows": 0,  # Will be calculated from first_transaction_row in parser
                        "first_transaction_row": mapping_data.get("first_transaction_row", 1),
                        "amount_positive_is": "debit",
                    }
                    
                    logger.info("Built parsing schema from header mapping", {
                        "bank_name": bank_name,
                        "column_mappings": column_mappings,
                        "column_mappings_types": {k: type(v).__name__ for k, v in column_mappings.items()},
                        "first_transaction_row": schema["first_transaction_row"]
                    })
                    
                    # Save schema for future use
                    if bank_name:
                        save_parsing_schema(schema, bank_name, user_id)
                except json.JSONDecodeError:
                    logger.warn("Failed to parse header_mapping, falling back to analysis")
                    schema = None
            
            if not schema:
                # Auto-analyze structure (use AI to detect format)
                logger.info("No existing schema, analyzing statement structure")
                analysis = analyze_statement_structure_from_file(str(file_path), user_id)
                
                # Auto-build schema from analysis (use defaults for missing info)
                schema = build_parsing_schema(analysis, {})
                
                # Save schema for future use
                if bank_name:
                    save_parsing_schema(schema, bank_name, user_id)
        
        # Step 3: Parse transactions
        transactions = parse_csv_statement(str(file_path), schema)
        logger.info(f"Parsed {len(transactions)} transactions")
        
        if not transactions:
            return JSONResponse({
                "error": "No transactions found in statement",
                "status": "error"
            }, status_code=400)
        
        # Step 4: Normalize transactions (extract merchant, etc.)
        normalized_txs = []
        for tx in transactions:
            normalized = normalize_transaction(tx, schema)
            normalized_txs.append(normalized)
        
        # Step 5: Get existing categorization rules
        from app.database import CategorizationRule
        db = SessionLocal()
        try:
            rules = db.query(CategorizationRule).filter(
                CategorizationRule.user_id == user_id,
                CategorizationRule.enabled.is_(True)
            ).all()
            existing_rules = [{
                "merchant_pattern": r.merchant_pattern,
                "category": r.category
            } for r in rules]
        finally:
            db.close()
        
        # Step 6: Categorize transactions using AI (in parallel batches)
        # Add IDs to transactions for categorization
        tx_with_ids = [
            {**tx, "id": idx + 1}
            for idx, tx in enumerate(normalized_txs)
        ]
        
        logger.info("Starting parallel categorization", {
            "transaction_count": len(tx_with_ids),
            "batch_size": 20
        })
        
        categorized = categorize_transactions_batch(
            tx_with_ids,
            user_id,
            existing_rules,
            batch_size=20,
            parallel=True
        )
        
        # Create mapping of ID to category
        category_map = {item["id"]: item["category"] for item in categorized}
        
        # Step 6.5: Save individual transactions to database
        logger.info("Saving individual transactions to database", {
            "transaction_count": len(normalized_txs),
            "bank_name": bank_name
        })
        
        db_save = SessionLocal()
        try:
            for idx, tx in enumerate(normalized_txs):
                tx_id = idx + 1
                category = category_map.get(tx_id, "Other")
                
                # Convert date to date object if it's a string
                tx_date = tx["date"]
                if isinstance(tx_date, str):
                    from datetime import datetime as dt
                    tx_date = dt.fromisoformat(tx_date).date()
                
                transaction = Transaction(
                    user_id=user_id,
                    date=tx_date,
                    description=tx["description"],
                    merchant=tx.get("merchant"),
                    amount=float(tx["amount"]),
                    currency=tx.get("currency", schema.get("currency", "USD")),
                    category=category,
                    bank_name=bank_name,
                    profile=None,  # Can be added later if needed
                )
                db_save.add(transaction)
            
            db_save.commit()
            logger.info(f"Saved {len(normalized_txs)} transactions to database", {
                "bank_name": bank_name,
                "user_id": user_id
            })
        except Exception as e:
            db_save.rollback()
            logger.error("Failed to save transactions to database", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            raise
        finally:
            db_save.close()
        
        # Step 7: Aggregate by category
        from collections import defaultdict
        from datetime import datetime as dt
        category_totals = defaultdict(float)
        category_counts = defaultdict(int)
        dates = []
        
        for idx, tx in enumerate(normalized_txs):
            tx_id = idx + 1
            category = category_map.get(tx_id, "Other")
            category_totals[category] += tx["amount"]
            category_counts[category] += 1
            if isinstance(tx["date"], str):
                dates.append(dt.fromisoformat(tx["date"]).date())
            else:
                dates.append(tx["date"])
        
        # Step 8: Build category summaries
        coverage_from = min(dates).isoformat() if dates else ""
        coverage_to = max(dates).isoformat() if dates else ""
        month_year = coverage_to[:7] if coverage_to else ""  # YYYY-MM format
        
        category_summaries = []
        for cat, amount in category_totals.items():
            category_summaries.append({
                "category": cat,
                "amount": float(amount),
                "currency": schema.get("currency", "USD"),
                "month_year": month_year,
                "transaction_count": category_counts[cat]
            })
        
        # Step 9: Calculate net flow if not provided
        if net_flow is None:
            # Calculate from transaction amounts
            net_flow = sum(tx["amount"] for tx in normalized_txs)
        
        # Step 10: Save statement summary
        result = await save_statement_summary_handler(
            category_summaries=category_summaries,
            bank_name=bank_name or "Unknown",
            statement_net_flow=float(net_flow),
            coverage_from=coverage_from,
            coverage_to=coverage_to,
            user_id=user_id
        )
        
        # Step 11: Get dashboard data
        dashboard_data = get_financial_data_handler(user_id=user_id)
        
        return JSONResponse({
            "status": "success",
            "transactions_processed": len(normalized_txs),
            "categories": len(category_summaries),
            "dashboard": dashboard_data.get("_meta", dashboard_data.get("structuredContent", {})),
            "message": f"Successfully processed {len(normalized_txs)} transactions across {len(category_summaries)} categories"
        })
        
    except Exception as e:
        logger.error("Auto-processing error", {
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


@mcp.custom_route("/api/transactions", methods=["GET"])
async def get_transactions(request: Request):
    """List transactions with filters"""
    try:
        user_id = get_or_create_test_user()  # TODO: Get from auth
        db = SessionLocal()
        
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        
        # Apply filters
        bank_name = request.query_params.get("bank_name")
        category = request.query_params.get("category")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        
        if bank_name:
            query = query.filter(Transaction.bank_name == bank_name)
        if category:
            query = query.filter(Transaction.category == category)
        if date_from:
            query = query.filter(Transaction.date >= datetime.fromisoformat(date_from).date())
        if date_to:
            query = query.filter(Transaction.date <= datetime.fromisoformat(date_to).date())
        
        transactions = query.order_by(Transaction.date.desc()).limit(1000).all()
        
        result = [{
            "id": str(tx.id),
            "date": tx.date.isoformat(),
            "description": tx.description,
            "merchant": tx.merchant,
            "amount": float(tx.amount),
            "currency": tx.currency,
            "category": tx.category,
            "bank_name": tx.bank_name,
            "profile": tx.profile
        } for tx in transactions]
        
        db.close()
        return JSONResponse({"transactions": result, "count": len(result)})
        
    except Exception as e:
        logger.error("Get transactions error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/transactions", methods=["PATCH"])
async def update_transaction(request: Request):
    """Update transaction (especially category)"""
    try:
        user_id = get_or_create_test_user()  # TODO: Get from auth
        data = await request.json()
        transaction_id = data.get("id")
        updates = data.get("updates", {})
        
        db = SessionLocal()
        tx = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        ).first()
        
        if not tx:
            db.close()
            return JSONResponse({"error": "Transaction not found"}, status_code=404)
        
        # Update fields
        if "category" in updates:
            tx.category = updates["category"]
        if "merchant" in updates:
            tx.merchant = updates["merchant"]
        if "description" in updates:
            tx.description = updates["description"]
        
        tx.updated_at = datetime.now()
        db.commit()
        db.close()
        
        return JSONResponse({
            "id": str(tx.id),
            "category": tx.category,
            "updated": True
        })
        
    except Exception as e:
        logger.error("Update transaction error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/financial-data", methods=["GET"])
async def get_financial_data_api(request: Request):
    """REST version of get_financial_data MCP tool"""
    try:
        user_id = get_or_create_test_user()  # TODO: Get from auth
        
        # Get filters from query params
        bank_name = request.query_params.get("bank_name")
        month_year = request.query_params.get("month_year")
        categories = request.query_params.getlist("categories")
        profile = request.query_params.get("profile")
        
        # Call existing handler
        result = get_financial_data_handler(
            user_id=user_id,
            bank_name=bank_name,
            month_year=month_year,
            categories=categories if categories else None,
            profile=profile
        )
        
        # Return the _meta payload (full dashboard data)
        return JSONResponse(result.get("_meta", result.get("structuredContent", {})))
        
    except Exception as e:
        logger.error("Get financial data error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/budgets", methods=["GET", "POST"])
async def manage_budgets(request: Request):
    """Get or save budgets"""
    try:
        user_id = get_or_create_test_user()  # TODO: Get from auth
        
        if request.method == "GET":
            # Return existing budgets
            from app.database import Budget
            db = SessionLocal()
            budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
            result = [{
                "category": b.category,
                "month_year": b.month_year,
                "amount": float(b.amount),
                "currency": b.currency
            } for b in budgets]
            db.close()
            return JSONResponse({"budgets": result})
        
        elif request.method == "POST":
            # Save budgets
            data = await request.json()
            budgets = data.get("budgets", [])
            result = await save_budget_handler(budgets=budgets, user_id=user_id)
            return JSONResponse(result.get("structuredContent", {"status": "saved"}))
            
    except Exception as e:
        logger.error("Manage budgets error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/preferences", methods=["GET", "POST"])
async def manage_preferences_api(request: Request):
    """Get or save preferences (categorization or parsing)"""
    try:
        user_id = get_or_create_test_user()  # TODO: Get from auth
        
        if request.method == "GET":
            preference_type = request.query_params.get("preference_type", "categorization")
            bank_name = request.query_params.get("bank_name")
            
            result = await fetch_preferences_handler(
                preference_type=preference_type,
                bank_name=bank_name,
                user_id=user_id
            )
            
            return JSONResponse(result.get("structuredContent", {}))
        
        elif request.method == "POST":
            data = await request.json()
            preferences = data.get("preferences", [])
            preference_type = data.get("preference_type", "categorization")
            
            result = await save_preferences_handler(
                preferences=preferences,
                preference_type=preference_type,
                user_id=user_id
            )
            
            return JSONResponse(result.get("structuredContent", {"status": "saved"}))
        
    except Exception as e:
        logger.error("Preferences API error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/banks", methods=["GET", "POST"])
async def manage_banks_api(request: Request):
    """Get or add banks for user"""
    try:
        user_id = get_or_create_test_user()  # TODO: Get from auth
        
        if request.method == "GET":
            # Get registered banks from user settings
            from app.database import CategorizationPreference
            db = SessionLocal()
            try:
                settings_pref = db.query(CategorizationPreference).filter(
                    CategorizationPreference.user_id == user_id,
                    CategorizationPreference.preference_type == "settings",
                    CategorizationPreference.name == "user_settings",
                    CategorizationPreference.enabled.is_(True)
                ).first()
                
                banks = []
                if settings_pref and settings_pref.rule:
                    banks = settings_pref.rule.get("registered_banks", [])
                
                return JSONResponse({"banks": banks})
            finally:
                db.close()
        
        elif request.method == "POST":
            # Add new bank to registered_banks
            data = await request.json()
            bank_name = data.get("bank_name")
            
            if not bank_name:
                return JSONResponse({"error": "bank_name is required"}, status_code=400)
            
            # Get current banks
            from app.database import CategorizationPreference
            db = SessionLocal()
            try:
                settings_pref = db.query(CategorizationPreference).filter(
                    CategorizationPreference.user_id == user_id,
                    CategorizationPreference.preference_type == "settings",
                    CategorizationPreference.name == "user_settings",
                    CategorizationPreference.enabled.is_(True)
                ).first()
                
                current_banks = []
                settings_data = {}
                if settings_pref and settings_pref.rule:
                    settings_data = settings_pref.rule.copy()
                    current_banks = settings_data.get("registered_banks", [])
                
                # Add new bank if not already present (case-insensitive)
                bank_lower = bank_name.strip().lower()
                if not any(b.lower() == bank_lower for b in current_banks):
                    current_banks.append(bank_name.strip())
                    settings_data["registered_banks"] = current_banks
                    
                    # Save via save_preferences_handler
                    result = await save_preferences_handler(
                        preferences=[settings_data],
                        preference_type="settings",
                        user_id=user_id
                    )
                    
                    return JSONResponse({"banks": current_banks, "status": "added"})
                else:
                    return JSONResponse({"banks": current_banks, "status": "already_exists"})
            finally:
                db.close()
        
    except Exception as e:
        logger.error("Banks API error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/auth/register", methods=["POST"])
async def register(request: Request):
    """Register a new user"""
    try:
        data = await request.json()
        email = data.get("email")
        name = data.get("name")
        password = data.get("password")  # TODO: Hash password properly
        
        if not email:
            return JSONResponse({"error": "Email is required"}, status_code=400)
        
        db = SessionLocal()
        try:
            # Check if user exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return JSONResponse({"error": "User already exists"}, status_code=400)
            
            # Create new user
            user = User(email=email, name=name or email.split("@")[0])
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Generate JWT token
            token = jwt.encode(
                {"sub": str(user.id), "email": user.email, "exp": datetime.utcnow() + timedelta(days=30)},
                settings.secret_key,
                algorithm="HS256"
            )
            
            return JSONResponse({
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name
                },
                "token": token
            })
        finally:
            db.close()
            
    except Exception as e:
        logger.error("Registration error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/auth/login", methods=["POST"])
async def login(request: Request):
    """Login user (for local auth, OAuth2 handled separately)"""
    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")  # TODO: Verify password properly
        
        if not email:
            return JSONResponse({"error": "Email is required"}, status_code=400)
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return JSONResponse({"error": "Invalid credentials"}, status_code=401)
            
            # TODO: Verify password hash
            # For now, allow login without password verification (development only)
            
            # Generate JWT token
            token = jwt.encode(
                {"sub": str(user.id), "email": user.email, "exp": datetime.utcnow() + timedelta(days=30)},
                settings.secret_key,
                algorithm="HS256"
            )
            
            return JSONResponse({
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name
                },
                "token": token
            })
        finally:
            db.close()
            
    except Exception as e:
        logger.error("Login error", {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/api/auth/me", methods=["GET"])
async def get_current_user(request: Request):
    """Get current user from token"""
    try:
        # Try OAuth2 first
        authorization = request.headers.get("Authorization")
        token_payload = await oauth2_auth.validate_token(authorization)
        
        if token_payload:
            # OAuth2 token
            user_id = token_payload.get("sub")
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return JSONResponse({
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name
                    })
            finally:
                db.close()
        
        # Try JWT token
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            try:
                payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
                user_id = payload.get("sub")
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user:
                        return JSONResponse({
                            "id": str(user.id),
                            "email": user.email,
                            "name": user.name
                        })
                finally:
                    db.close()
            except jwt.JWTError:
                pass
        
        # Fallback to test user for development
        user_id = get_or_create_test_user()
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return JSONResponse({
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name
                })
        finally:
            db.close()
        
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
        
    except Exception as e:
        logger.error("Get current user error", {"error": str(e)})
        # Fallback to test user for development
        user_id = get_or_create_test_user()
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return JSONResponse({
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name
                })
        finally:
            db.close()
        return JSONResponse({"error": str(e)}, status_code=500)


# Get the ASGI app from FastMCP
app = mcp.streamable_http_app()

# Mount static files directory
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

if WEB_DIST_PATH.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIST_PATH)), name="static")
    logger.info("Static files mounted", {"path": "/static", "source": str(WEB_DIST_PATH)})
else:
    logger.warn("Widget dist directory not found", {
        "path": str(WEB_DIST_PATH),
        "hint": "Run 'cd web && npm run build' to create widget bundles"
    })

# Add CORS middleware with configurable origins
_allowed_origins = [
    origin.strip()
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
]
# Fallback to ChatGPT origin if no origins configured
if not _allowed_origins:
    _allowed_origins = ["https://chatgpt.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)

# Export the ASGI app for uvicorn
asgi_app = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(asgi_app, host="0.0.0.0", port=8000)
