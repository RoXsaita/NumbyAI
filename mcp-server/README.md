# MCP Server

FastAPI-based Model Context Protocol (MCP) server for the Finance Budgeting App.

## Overview

This server provides MCP tools for AI assistants to interact with user financial data:
- Save and retrieve bank statement summaries
- Manage budgets
- Mutate category allocations
- Manage categorization preferences
- Query financial data with dashboard visualizations

## Structure

```
mcp-server/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── auth.py              # JWT authentication
│   ├── config.py            # Environment configuration
│   ├── database.py          # SQLAlchemy database setup
│   ├── logger.py            # Structured logging
│   ├── schemas/             # Pydantic schemas
│   │   └── dashboard.py     # Dashboard data models
│   └── tools/               # MCP tool implementations
│       ├── financial_data.py           # get_financial_data
│       ├── save_statement_summary.py   # save_statement_summary
│       ├── save_budget.py              # save_budget
│       ├── mutate_categories.py        # mutate_categories
│       ├── fetch_categorization_preferences.py
│       ├── save_categorization_preference.py
│       └── tool_descriptions.py        # Tool documentation
├── alembic/                 # Database migrations
├── requirements.txt         # Python dependencies
└── Dockerfile              # Container build
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | SQLite (dev) |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `SECRET_KEY` | JWT signing key | Dev-only default |
| `AUTH0_DOMAIN` | Auth0 domain (optional) | - |
| `AUTH0_AUDIENCE` | Auth0 audience (optional) | - |

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_financial_data` | Query financial summaries with optional filters |
| `save_statement_summary` | Save categorized bank statement data |
| `save_budget` | Set budget targets by category |
| `mutate_categories` | Edit, transfer, or split category amounts |
| `fetch_categorization_preferences` | Get user's auto-categorization rules |
| `save_categorization_preference` | Save a categorization rule |

## Testing

```bash
# Run tool tests
python -m pytest test_*.py -v

# Run QA script
python test_preferences_qa.py
```
