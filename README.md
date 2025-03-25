# Yale Radiology Policies RAG Application

## Project Overview

The Yale Radiology Policies RAG Application is a comprehensive system designed to make departmental policies accessible and interactive through large language models (LLMs). This document details the complete architecture, components, and implementation approach.

### Architectural Components

This project implements a unified system with four distinct components:

1. **Data Acquisition System**: Specialized components for crawling the Yale intranet, identifying policy pages, and extracting/processing policy content using LLMs.

2. **MCP Server**: An MCP-compliant server that exposes policy retrieval tools to be used by LLMs.

3. **Backend API Server**: FastAPI application that provides a Chat Agent, interfaces with the MCP server, and handles user management.

4. **Frontend Application**: Next.js user interface for interacting with policies through a chat interface, with admin features for policy management.

These components support three distinct access patterns:

- Complete UI Experience for end users (via Frontend + Backend API)
- Chat Agent API for external applications (via Backend API)
- MCP Retrieval Service for external AI applications (via MCP Server)

## System Architecture

```
┌─────────────────────────────────────┐
│                                     │
│  Frontend Service (Next.js)         │
│  [Port: 3000]                       │
│                                     │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│                                     │
│  Backend API (FastAPI)              │
│  [Port: 8000]                       │
│                                     │
│  - Database Models & Migrations     │
│  - Chat Agent API (/api/chat)       │
│  - Policy Management                │
│  - Authentication                   │
│                                     │
└──────────────────┬──────────────────┘
          │                 │
          │                 ▼
          │        ┌─────────────────────┐
          │        │                     │
          │        │  MCP Server         │
          │        │  [Port: 8001]       │
          │        │                     │
          │        │  - RAG Tools        │
          │        │  - Keyword Search   │
          │        │  - Hybrid Search    │
          │        │                     │
          │        └─────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│                                     │
│  PostgreSQL + pgvector               │
│  [Port: 5432]                       │
│                                     │
└─────────────────────────────────────┘

     ↑
     │ (Data Pipeline)
     │
┌─────────────────────────────────────┐
│                                     │
│  Data Collection                    │
│  - Yale Intranet Crawler            │
│  - Policy Content Scraper           │
│  - LLM-powered Extractor            │
│                                     │
└─────────────────────────────────────┘
```

## Detailed Project Structure

```
yale-radiology-rag/
├── .env                      # Environment variables (gitignored)
├── .env.example              # Example environment variables template
├── .gitignore                # Git ignore file
├── README.md                 # Project documentation
├── docker-compose.yml        # Docker compose configuration
├── nginx.conf                # Nginx configuration for production
├── supervisord.conf          # Supervisor configuration for process management
├── pytest.ini                # PyTest configuration
│
├── data/                     # Data storage
│   ├── raw/                  # Raw data from crawler
│   │   ├── documents/        # Downloaded documents (PDFs, etc.)
│   │   ├── markdown_files/   # Markdown content from web pages
│   │   ├── state/            # Crawler state for resuming
│   │   └── crawled_policies_data.csv  # List of crawled policy URLs
│   │
│   ├── processed/            # Processed data
│   │   ├── scraped_policies/ # Extracted policy content
│   │   └── scraped_policies_data.csv # Data about scraped policies
│   │
│   ├── auth/                 # Authentication data
│   ├── uploads/              # User uploaded documents
|   └── logs/                 # Project logs
│       ├── crawler.log       # Crawler logs
│       ├── scraper.log       # Scraper logs
│       └── backend.log       # Backend logs
│
├── test_data/                # Test data files
│   ├── mock_policies/        # Mock policy files for testing
│   ├── mock_documents/       # Mock documents for testing
│   ├── fixtures/             # Test fixtures
│   └── snapshots/            # Test snapshots
│
├── tests/                    # Centralized test directory
│   ├── __init__.py           # Test package initialization
│   ├── data_collection/      # Tests for data collection components
│   │   ├── __init__.py       # Test package initialization
│   │   ├── test_crawler.py   # Tests for crawler
│   │   └── test_scraper.py   # Tests for scraper
│   │
│   ├── mcp_server/           # Tests for MCP server components
│   │   ├── __init__.py       # Test package initialization
│   │   ├── test_server.py    # Tests for MCP server
│   │   └── test_tools/       # Tests for MCP tools
│   │       ├── __init__.py   # Test package initialization
│   │       ├── test_naive_rag.py   # Tests for naive RAG
│   │       ├── test_graph_rag.py   # Tests for graph RAG
│   │       ├── test_keyword_search.py # Tests for keyword search
│   │       └── test_hybrid_search.py  # Tests for hybrid search
│   │
│   ├── backend/              # Tests for backend components
│   │   ├── __init__.py       # Test package initialization
│   │   ├── test_app.py       # Tests for main app
|   |   ├── test_database.py  # Tests the database functionalities
│   │   ├── test_api/         # Tests for API endpoints
│   │   │   ├── __init__.py   # Test package initialization
│   │   │   ├── test_auth.py  # Tests for auth endpoints
│   │   │   ├── test_chat.py  # Tests for chat endpoints
│   │   │   └── test_policies.py # Tests for policy endpoints
│   │   ├── test_services/    # Tests for backend services
│   │   │   ├── __init__.py   # Test package initialization
│   │   │   ├── test_auth_service.py  # Tests for auth service
│   │   │   └── test_search_service.py # Tests for search service
│   │   └── test_chat/        # Tests for chat components
│   │       ├── __init__.py   # Test package initialization
│   │       ├── test_chat_agent.py # Tests for chat agent
│   │       └── test_prompt_templates.py # Tests for prompt templates
│   │
│   └── frontend/             # Tests for frontend components
│       ├── __init__.py       # Test package initialization
│       ├── components/       # Tests for React components
│       ├── hooks/            # Tests for React hooks
│       └── services/         # Tests for frontend services
│
├── ydrpolicy/                # Main package directory for all code
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Entry point for different modes
│   ├── config.py             # Global configuration settings
│   ├── constants.py          # Global constants and enumerations
│   ├── logger.py             # Centralized logging configuration
│   │
│   ├── data_collection/      # Data collection components
│   │   ├── __init__.py       # Package initialization
│   │   ├── config.py         # Configuration for crawlers and LLMs
│   │   ├── prompts.py        # LLM prompts for analysis
│   │   │
│   │   ├── crawl/            # Web crawler functionality
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── crawl.py      # Main entry point for crawling
│   │   │   ├── crawler.py    # YaleCrawler implementation
│   │   │   ├── crawler_state.py  # State management for resuming
│   │   │   └── processors/   # Document processing utilities
│   │   │       ├── __init__.py   # Package initialization
│   │   │       ├── document_processor.py # Document download/conversion
│   │   │       ├── pdf_processor.py    # PDF processing with OCR
│   │   │       └── llm_processor.py    # LLM-based content analysis
│   │   │
│   │   └── scrape/           # Policy extraction functionality
│   │       ├── __init__.py   # Package initialization
│   │       ├── scrape.py     # Main entry point for scraping
│   │       └── scraper.py    # Policy extraction implementation
│   │
│   ├── mcp_server/           # MCP Server implementation
│   │   ├── __init__.py       # Package initialization
│   │   ├── config.py         # MCP server configuration
│   │   ├── server.py         # MCP server entry point
│   │   ├── tools/            # MCP-compliant tools
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── base_tool.py  # Abstract MCP tool interface
│   │   │   ├── naive_rag.py  # Simple RAG implementation
│   │   │   ├── graph_rag.py  # Graph-based RAG implementation
│   │   │   ├── keyword_search.py # Full-text search implementation
│   │   │   └── hybrid_search.py  # Hybrid search implementation
│   │   │
│   │   ├── schemas.py        # MCP-specific Pydantic schemas
│   │   └── services/         # Services for MCP
│   │       ├── __init__.py   # Package initialization
│   │       ├── vector_store.py # Vector DB operations for MCP
│   │       └── database.py   # Database access for MCP
│   │
│   ├── backend/              # Backend API components
│   │   ├── __init__.py       # Package initialization
│   │   ├── app.py            # FastAPI application entry point
│   │   ├── config.py         # Configuration settings using Pydantic
│   │   ├── exceptions.py     # Custom exception definitions
│   │   │
│   │   ├── database/         # Database models & operations
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── engine.py     # SQLAlchemy engine and session setup
│   │   │   ├── models.py     # SQLAlchemy ORM models
│   │   │   ├── repository/   # Repository pattern implementations
│   │   │   │   ├── __init__.py   # Package initialization
│   │   │   │   ├── base.py   # Base repository class
│   │   │   │   ├── users.py  # User repository
│   │   │   │   ├── policies.py # Policy repository
│   │   │   │   ├── chat.py   # Chat history repository
│   │   │   └── migrations/   # Alembic migrations
│   │   │       ├── versions/ # Migration scripts
│   │   │       ├── env.py    # Alembic environment
│   │   │       ├── script.py.mako # Migration template
│   │   │       └── alembic.ini # Alembic configuration
│   │   │
│   │   ├── services/         # Shared business logic services
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── auth_service.py # Authentication logic
│   │   │   ├── search_service.py # Search service (full-text + vector)
│   │   │   ├── embeddings.py # Text embedding logic with OpenAI
│   │   │   ├── chunking.py   # Text chunking strategies
│   │   │   ├── policy_service.py # Policy processing service
│   │   │   ├── mcp_client.py # Client for connecting to MCP server
│   │   │   └── usage_tracking.py # API usage tracking service
│   │   │
│   │   ├── chat/             # Chat Agent implementation
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── agents/       # LLM agents
│   │   │   │   ├── __init__.py # Package initialization
│   │   │   │   ├── base_agent.py # Abstract base agent
│   │   │   │   ├── chat_agent.py # Main chat agent implementation
│   │   │   │   ├── prompt_templates.py # Prompt engineering templates
│   │   │   │   ├── openai_provider.py # OpenAI API handler
│   │   │   │   └── gemini_provider.py # Google Gemini API handler
│   │   │   ├── schemas.py    # Chat-specific Pydantic schemas
│   │   │   └── service.py    # Chat service implementation
│   │   │
│   │   ├── routers/          # FastAPI routers
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── auth.py       # Authentication routes
│   │   │   ├── chat.py       # Chat routes
│   │   │   ├── policies.py   # Policy management routes
│   │   │   ├── about.py      # About page content routes
│   │   │   └── feedback.py   # User feedback routes
│   │   │
│   │   ├── schemas/          # Shared Pydantic schemas
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── auth.py       # Auth-related schemas
│   │   │   ├── policy.py     # Policy-related schemas
│   │   │   ├── about.py      # About page schemas
│   │   │   ├── api_usage.py  # API usage tracking schemas
│   │   │   └── feedback.py   # Feedback-related schemas
│   │   │
│   │   ├── middleware/       # Middleware components
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── auth_middleware.py # JWT validation middleware
│   │   │   ├── error_handler.py # Error handling middleware
│   │   │   ├── usage_tracker.py # API usage tracking middleware
│   │   │   └── logging_middleware.py # Request logging middleware
│   │   │
│   │   ├── scripts/       # Standalone backend scripts
│   │   │   ├── initalize_database.py # initialize the database
│   │   │
|   |   └── utils/       # Misc backend utils
│   │       ├── paths.py # Ensure the database paths exist
│   │
│   └── frontend/             # Next.js Frontend
│       ├── .eslintrc.json    # ESLint configuration
│       ├── next.config.js    # Next.js configuration
│       ├── package.json      # NPM dependencies
│       ├── tsconfig.json     # TypeScript configuration
│       ├── tailwind.config.js # Tailwind CSS configuration
│       │
│       ├── public/           # Static files
│       │   ├── favicon.ico   # Site favicon
│       │   ├── yale-logo.svg # Yale logo
│       │   └── images/       # Image assets
│       │
│       └── src/              # Source code
│           ├── app/          # Next.js app router
│           │   ├── layout.tsx # Root layout
│           │   ├── page.tsx  # Landing page
│           │   ├── login/    # Login route
│           │   ├── dashboard/ # Main dashboard route
│           │   ├── chat/     # Chat interface
│           │   │   ├── page.tsx # Main chat page
│           │   │   └── history/ # Chat history management
│           │   ├── policies/ # Policy management
│           │   ├── about/    # About page
│           │   └── profile/  # User profile
│           │
│           ├── components/   # Reusable components
│           │   ├── ui/       # Base UI components
│           │   ├── auth/     # Login components
│           │   ├── chat/     # Chat interface components
│           │   │   ├── ChatInterface.tsx # Main chat UI component
│           │   │   ├── ChatMessage.tsx  # Individual message component
│           │   │   ├── ChatSelector.tsx # Chat history selector
│           │   │   ├── NewChatButton.tsx # Start new chat button
│           │   │   ├── DeleteChatButton.tsx # Delete chat button
│           │   │   ├── SearchMethodSelector.tsx # Search method selector
│           │   │   ├── ModelSelector.tsx # OpenAI/Gemini selector
│           │   │   └── FeedbackButtons.tsx # Feedback UI component
│           │   ├── policies/ # Policy viewing components
│           │   ├── about/    # About page components
│           │   └── layout/   # Layout components
│           │
│           ├── hooks/        # Custom React hooks
│           ├── services/     # API client services
│           ├── types/        # TypeScript types
│           ├── utils/        # Utility functions
│           └── styles/       # Global styles
```

## Implementation of main.py

The main.py script will act as an entry point for the different modes of operation:

```python
import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Yale Radiology Policies RAG Application")
    subparsers = parser.add_subparsers(dest="mode", help="Mode to run the application in")

    # MCP Server mode
    mcp_parser = subparsers.add_parser("mcp", help="Run the MCP server")
    mcp_parser.add_argument("--port", type=int, default=8001, help="Port to run the MCP server on")
    mcp_parser.add_argument("--transport", choices=["http", "stdio"], default="http",
                           help="Transport mechanism (http or stdio)")

    # Backend API mode
    api_parser = subparsers.add_parser("api", help="Run the Backend API server")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind the API server to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to run the API server on")
    api_parser.add_argument("--debug", action="store_true", help="Run in debug mode")

    # Data Collection mode
    data_parser = subparsers.add_parser("data", help="Run data collection tasks")
    data_parser.add_argument("--task", choices=["crawl", "scrape", "all"],
                            required=True, help="Data collection task to run")

    # Frontend mode (for development)
    frontend_parser = subparsers.add_parser("frontend", help="Run the frontend development server")
    frontend_parser.add_argument("--port", type=int, default=3000, help="Port to run the frontend on")

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    if args.mode == "data":
        if args.task == "crawl" or args.task == "all":
            from data_collection.crawl.crawl import main as crawl_main
            crawl_main()

        if args.task == "scrape" or args.task == "all":
            from data_collection.scrape.scrape import main as scrape_main
            scrape_main()

    elif args.mode == "mcp":
        # from mcp_server.server import run_server
        # run_server(port=args.port, transport=args.transport)
        raise NotImplementedError("MCP server not implemented yet")

    elif args.mode == "api":
        # from backend.app import start_backend
        # start_backend(host=args.host, port=args.port, debug=args.debug)
        raise NotImplementedError("Backend API server not implemented yet")

    elif args.mode == "frontend":
        # Change directory to frontend and run npm command
        # os.chdir("frontend")
        # os.system(f"npm run dev -- --port {args.port}")
        raise NotImplementedError("Frontend development server not implemented yet")

if __name__ == "__main__":
    main()
```

## Running the Application Components

### Development Environment (TMUX Sessions)

During development, you'll typically run three separate processes:

**Terminal 1 (MCP Server)**:

```bash
python main.py mcp --port 8001
```

**Terminal 2 (Backend API)**:

```bash
python main.py api --port 8000 --debug
```

**Terminal 3 (Frontend)**:

```bash
python main.py frontend --port 3000
# Or directly using npm in the frontend directory:
# cd frontend && npm run dev
```

### Production Environment (Supervisor)

In production, you can use Supervisor to manage these processes. Here's a sample supervisord.conf:

```ini
[program:mcp-server]
command=python /path/to/yale-radiology-rag/main.py mcp --port 8001
directory=/path/to/yale-radiology-rag
autostart=true
autorestart=true
user=www-data
stderr_logfile=/var/log/supervisor/mcp-server.err.log
stdout_logfile=/var/log/supervisor/mcp-server.out.log

[program:backend-api]
command=python /path/to/yale-radiology-rag/main.py api --port 8000
directory=/path/to/yale-radiology-rag
autostart=true
autorestart=true
user=www-data
stderr_logfile=/var/log/supervisor/backend-api.err.log
stdout_logfile=/var/log/supervisor/backend-api.out.log

[program:frontend]
command=cd /path/to/yale-radiology-rag/frontend && npm run start -- -p 3000
directory=/path/to/yale-radiology-rag/frontend
autostart=true
autorestart=true
user=www-data
stderr_logfile=/var/log/supervisor/frontend.err.log
stdout_logfile=/var/log/supervisor/frontend.out.log
```

## Communication between Components

### MCP Server and Backend API

The Backend API will connect to the MCP Server as a client using the MCP protocol. This communication happens through:

1. The `backend/services/mcp_client.py` module that implements an MCP client
2. The Chat Agent uses this client to access the policy retrieval tools

### Backend API and Frontend

The Frontend communicates with the Backend API using standard HTTP requests:

1. Authentication via JWT tokens
2. RESTful API endpoints for policy management
3. WebSocket connection for real-time chat functionality

### Database Access

Both the MCP Server and Backend API have access to the PostgreSQL database:

1. MCP Server uses it to retrieve policy vectors and content
2. Backend API uses it for user management, chat history, and policy management
