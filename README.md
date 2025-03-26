# Yale Radiology Policies RAG Application - Comprehensive Specification

## Project Overview

The Yale Radiology Policies RAG Application is a comprehensive system designed to make departmental policies accessible and interactive through large language models (LLMs). The system leverages modern retrieval-augmented generation techniques to provide accurate policy information to users through natural language interactions.

## Modes of Operation

The system supports four distinct modes of operation, catering to different user needs and integration scenarios:

### 1. Complete Frontend Application Mode

In this mode, all three core components are deployed and accessible to end users:

- **Frontend Service**: A Next.js application providing the user interface
- **Backend API**: A FastAPI application handling authentication, chat functionality, and policy management
- **MCP Server**: A specialized server providing retrieval tools to the LLM

**User Interaction Flow**:

1. Users access the web application and are presented with a login screen
2. After authentication with Yale credentials (stored in a JSON file), users see a chat interface similar to ChatGPT
3. Users can enter prompts related to policies and receive AI-generated responses
4. The chat history is maintained on a vertical menu on the left side
5. Users can start new conversations or continue existing ones
6. The interface displays when and which retrieval tools are being used by the agent (this can be configured to be visible or hidden)
7. Users can switch between conversations, and sessions persist across browser restarts

**Deployment Options**:

- Development: Three separate Tmux sessions, one for each component
- Production: Components can run on the same physical server or on separate physical servers

### 2. Backend API Mode (No Frontend)

In this mode, only the Backend API and MCP Server are operational, enabling integration with third-party frontends:

- **Backend API**: Provides the Chat Agent API and authentication
- **MCP Server**: Supplies the retrieval tools

**User Interaction Flow**:

1. External applications authenticate with the Backend API
2. The Chat Agent API exposes endpoints for initiating and continuing conversations
3. Authentication is still required, and conversations are logged to the database
4. Each conversation is a single instance (no conversation history management)

This mode is ideal for organizations that want to integrate the policy chat functionality into their existing applications.

### 3. MCP Server Mode Only

This minimal mode provides only the MCP Server component, exposing policy retrieval capabilities to any compatible client:

- **MCP Server**: Offers policy retrieval tools via the MCP protocol

**User Interaction Flow**:

1. External LLM-powered applications connect to the MCP Server
2. The server receives queries and executes the appropriate tools:
   - RAG tool for semantic retrieval
   - Keyword search tool for exact-match searches
   - Possible future internet search tools
3. Retrieved policy information is returned to the external application
4. All tool usage is logged in the database

This mode enables integration with any MCP-compatible client, allowing organizations to leverage their own LLMs and chat interfaces.

### 4. Admin Policy Processing Mode

This administrative mode is used for managing the policy database:

- **Policy Processing System**: Leverages the existing crawler and scraper components

**Admin Interaction Flow**:

1. Administrators specify a single policy URL or multiple URLs
2. Optional parameters control whether to follow links from the source page or process only the specified URLs
3. The system crawls and scrapes the content, extracts policies, and processes them
4. Processed policies are chunked, embedded, and added to the database
5. All operations are logged for auditing purposes

This mode is accessible only to administrators and is designed for maintaining and updating the policy database.

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

## Technology Stack

### Backend

- **FastAPI**: Modern, high-performance web framework for building APIs with Python
- **PostgreSQL + pgvector**: Relational database with vector storage capabilities
- **SQLAlchemy**: ORM for database interactions
- **Alembic**: Database migration management
- **OpenAI API**: For LLM capabilities (embedding and generation)
- **Google Gemini API**: Alternative LLM provider
- **MCP Protocol**: For tool integration with LLMs
- **Async Programming**: Leveraging Python's asyncio for high concurrency
- **Pydantic**: Data validation and settings management
- **JWT**: For authentication and session management

### Frontend

- **Next.js**: React framework for production-grade applications
- **TypeScript**: Typed JavaScript for improved developer experience
- **React**: UI library for building component-based interfaces
- **TailwindCSS**: Utility-first CSS framework
- **SWR/React Query**: For data fetching and caching

### Data Collection and Processing

- **Selenium**: Web automation for crawling complex sites
- **Requests**: HTTP library for simpler web requests
- **PDF Processing**: Libraries for extracting text from PDFs
- **Markdown Processing**: Tools for converting and standardizing content

### Testing

- **PyTest**: For comprehensive unit and integration testing
- **Jest/Testing Library**: For frontend testing

## Database Schema

The application uses PostgreSQL with pgvector extension for vector storage. The database schema consists of the following tables:

### 1. Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,  -- Yale email address
    password_hash VARCHAR(255) NOT NULL,  -- Hashed password
    full_name VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);
```

### 2. Policies Table

```sql
CREATE TABLE policies (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(255) UNIQUE NOT NULL,  -- Source URL
    content TEXT NOT NULL,  -- Full policy content
    metadata JSONB,  -- Additional metadata about the policy
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3. Policy Chunks Table

```sql
CREATE TABLE policy_chunks (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER REFERENCES policies(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,  -- Position within the policy
    content TEXT NOT NULL,  -- Chunk text content
    embedding VECTOR(1536),  -- Vector embedding for semantic search
    metadata JSONB,  -- Additional metadata about the chunk
    UNIQUE(policy_id, chunk_index)
);
```

### 4. Chats Table

```sql
CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),  -- Auto-generated or user-provided title
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5. Messages Table

```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user', 'assistant', or 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 6. Tool Usage Table

```sql
CREATE TABLE tool_usage (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,  -- 'rag', 'keyword_search', etc.
    input JSONB NOT NULL,  -- Tool input parameters
    output JSONB,  -- Tool output
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    execution_time FLOAT  -- Time taken to execute the tool in seconds
);
```

### 7. Policy Updates Table

```sql
CREATE TABLE policy_updates (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES users(id),
    policy_id INTEGER REFERENCES policies(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,  -- 'create', 'update', 'delete'
    details JSONB,  -- Details of what was changed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
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
│   └── logs/                 # Project logs
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
├── tests/
│    ├── __init__.py
│    ├── conftest.py                   # Shared fixtures for all tests
│    ├── data_collection/              # Tests for data collection components
│    │   ├── __init__.py
│    │   ├── test_crawler.py
│    │   └── test_scraper.py
│    │
│    ├── backend/
│    │   ├── __init__.py
│    │   ├── test_app.py
│    │   ├── database/                 # Organized database tests
│    │   │   ├── __init__.py
│    │   │   ├── conftest.py           # Database-specific fixtures
│    │   │   ├── test_connection.py    # Basic connection and setup tests
│    │   │   ├── test_models.py        # Tests for database models
│    │   │   ├── test_repositories.py  # Tests for base repository pattern
│    │   │   ├── test_policy_repo.py   # Tests for policy repository
│    │   │   ├── test_user_repo.py     # Tests for user repository
│    │   │   ├── test_chunking.py      # Tests for chunking functionality
│    │   │   ├── test_embeddings.py    # Tests for embedding functionality
|    |   |   ├── test_pgvector.py      # Tests for pgvector functionalities
│    │   │   └── test_search.py        # Tests for various search methods
│    │   │
│    │   ├── test_services/
│    │   │   ├── __init__.py
│    │   │   ├── test_policy_processor.py
│    │   │   ├── test_auth_service.py
│    │   │   └── test_search_service.py
│    │   │
│    │   ├── test_api/
│    │   │   ├── __init__.py
│    │   │   ├── test_auth.py
│    │   │   ├── test_chat.py
│    │   │   └── test_policies.py
│    │   │
│    │   └── test_chat/
│    │       ├── __init__.py
│    │       ├── test_chat_agent.py
│    │       └── test_prompt_templates.py
│    │
│    ├── mcp_server/
│    │   ├── __init__.py
│    │   ├── test_server.py
│    │   └── test_tools/
│    │       ├── __init__.py
│    │       ├── test_naive_rag.py
│    │       ├── test_graph_rag.py
│    │       ├── test_keyword_search.py
│    │       ├── test_hybrid_search.py
│    │       └── test_add_policy.py
│    │
│    └── frontend/
│        ├── __init__.py
│        ├── components/
│        ├── hooks/
│        └── services/       └── services/         # Tests for frontend services
│
├── ydrpolicy/                # Main package directory for all code
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Entry point for different modes (updated for policy processing)
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
│   │   │   ├── hybrid_search.py  # Hybrid search implementation
│   │   │   └── add_policy.py # Tool for adding new policies
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
│   │   ├── logger.py         # Backend-specific logger
│   │   │
│   │   ├── database/         # Database models & operations
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── engine.py     # SQLAlchemy engine and session setup
│   │   │   ├── models.py     # SQLAlchemy ORM models
│   │   │   ├── init_db.py    # Database initialization script
│   │   │   ├── repository/   # Repository pattern implementations
│   │   │   │   ├── __init__.py   # Package initialization
│   │   │   │   ├── base.py   # Base repository class
│   │   │   │   ├── users.py  # User repository
│   │   │   │   ├── policies.py # Policy repository
│   │   │   │   └── chat.py   # Chat history repository
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
│   │   │   ├── policy_processor.py # Policy processing service
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
│   │   │   ├── policy.py     # Policy-related schemas (updated for policy processing)
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
│   │   ├── scripts/          # Standalone backend scripts
│   │   │   ├── __init__.py   # Package initialization
│   │   │   └── initialize_database.py # Initialize the database
│   │   │
│   │   └── utils/            # Misc backend utils
│   │       ├── __init__.py   # Package initialization
│   │       └── paths.py      # Path management utilities
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
│           │   │   ├── page.tsx # Policies list page
│           │   │   ├── [id]/  # Single policy view
│           │   │   └── add/   # Add policy form
│           │   ├── about/    # About page
│           │   └── profile/  # User profile
│           │
│           ├── components/   # Reusable components
│           │   ├── ui/       # Base UI components
│           │   ├── auth/     # Login components
│           │   ├── chat/     # Chat interface components
│           │   ├── policies/ # Policy management components
│           │   │   ├── PolicyList.tsx # Policy listing component
│           │   │   ├── PolicyDetail.tsx # Policy detail view
│           │   │   ├── AddPolicyForm.tsx # Form for adding new policies
│           │   │   └── PolicySearchForm.tsx # Search form for policies
│           │   ├── about/    # About page components
│           │   └── layout/   # Layout components
│           │
│           ├── hooks/        # Custom React hooks
│           ├── services/     # API client services
│           │   ├── api.ts    # Base API client
│           │   ├── auth.ts   # Authentication service
│           │   ├── chat.ts   # Chat service
│           │   └── policies.ts # Policies service
│           ├── types/        # TypeScript types
│           ├── utils/        # Utility functions
│           └── styles/       # Global styles
```

## Main.py Implementation

```python
import argparse
import os
import sys
import logging
from pathlib import Path

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path("data/logs/application.log"))
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Main entry point for the application."""
    logger = setup_logging()

    parser = argparse.ArgumentParser(description="Yale Radiology Policies RAG Application")
    subparsers = parser.add_subparsers(dest="mode", help="Mode to run the application in")

    # Mode 1: MCP Server mode
    mcp_parser = subparsers.add_parser("mcp", help="Run the MCP server for policy retrieval tools")
    mcp_parser.add_argument("--port", type=int, default=8001, help="Port to run the MCP server on")
    mcp_parser.add_argument("--host", default="0.0.0.0", help="Host to bind the MCP server to")
    mcp_parser.add_argument("--transport", choices=["http", "stdio"], default="http",
                           help="Transport mechanism (http or stdio)")
    mcp_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    # Mode 2: Backend API mode
    api_parser = subparsers.add_parser("api", help="Run the Backend API server with Chat Agent")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind the API server to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to run the API server on")
    api_parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    api_parser.add_argument("--mcp-url", help="URL of the MCP server (default: http://localhost:8001)")
    api_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    # Mode 3: Frontend mode (for development)
    frontend_parser = subparsers.add_parser("frontend", help="Run the frontend development server")
    frontend_parser.add_argument("--port", type=int, default=3000, help="Port to run the frontend on")
    frontend_parser.add_argument("--api-url", help="URL of the Backend API (default: http://localhost:8000)")

    # Mode 4: Data Collection/Policy Processing mode
    data_parser = subparsers.add_parser("policy", help="Process policies for the database")
    data_parser.add_argument("--task", choices=["crawl", "scrape", "process", "add"],
                            required=True, help="Policy processing task to run")
    data_parser.add_argument("--url", help="URL of the policy or policy index page")
    data_parser.add_argument("--urls-file", help="File containing list of URLs to process")
    data_parser.add_argument("--follow-links", action="store_true",
                        help="Follow links from the provided URL(s)")
    data_parser.add_argument("--depth", type=int, default=1,
                        help="Link following depth when --follow-links is enabled")
    data_parser.add_argument("--admin-id", type=int, help="ID of admin performing the operation")
    data_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    # Full application mode (runs all components)
    full_parser = subparsers.add_parser("full", help="Run the complete application stack")
    full_parser.add_argument("--api-port", type=int, default=8000, help="Port for the Backend API")
    full_parser.add_argument("--mcp-port", type=int, default=8001, help="Port for the MCP server")
    full_parser.add_argument("--frontend-port", type=int, default=3000, help="Port for the frontend")
    full_parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    full_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    # Initialize database schema
    init_parser = subparsers.add_parser("init-db", help="Initialize the database schema")
    init_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    try:
        if args.mode == "policy":
            if args.task == "crawl" or args.task == "all":
                from ydrpolicy.data_collection.crawl.crawl import main as crawl_main
                crawl_main()

            elif args.task == "scrape" or args.task == "all":
                from ydrpolicy.data_collection.scrape.scrape import main as scrape_main
                scrape_main()

            elif args.task == "process" or args.task == "add":
                from ydrpolicy.backend.services.policy_processor import process_policies_cli
                asyncio.run(process_policies_cli(
                    url=args.url,
                    urls_file=args.urls_file,
                    admin_id=args.admin_id,
                    follow_links=args.follow_links,
                    depth=args.depth,
                    db_url=args.db_uri
                ))

        elif args.mode == "mcp":
            logger.info(f"Starting MCP Server on {args.host}:{args.port} with {args.transport} transport")
            from ydrpolicy.mcp_server.server import run_server
            run_server(host=args.host, port=args.port, transport=args.transport, db_uri=args.db_uri)

        elif args.mode == "api":
            logger.info(f"Starting Backend API Server on {args.host}:{args.port}, Debug={args.debug}")
            from ydrpolicy.backend.app import start_backend
            start_backend(host=args.host, port=args.port, debug=args.debug,
                         mcp_url=args.mcp_url, db_uri=args.db_uri)

        elif args.mode == "frontend":
            logger.info(f"Starting Frontend Server on port {args.port}")
            # Change directory to frontend and run npm command
            frontend_dir = Path(__file__).parent / "ydrpolicy" / "frontend"
            if not frontend_dir.exists():
                logger.error(f"Frontend directory not found: {frontend_dir}")
                sys.exit(1)

            os.chdir(frontend_dir)
            api_url = args.api_url or "http://localhost:8000"
            os.environ["NEXT_PUBLIC_API_URL"] = api_url
            os.system(f"npm run dev -- --port {args.port}")

        elif args.mode == "full":
            logger.info("Starting Full Application Stack")
            # This would start all components using multiprocessing
            import subprocess
            import threading

            # Function to run a component in a separate process
            def run_component(cmd, name):
                logger.info(f"Starting {name} with command: {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )

                # Handle stdout and stderr
                def log_output(stream, level):
                    for line in stream:
                        if level == "info":
                            logger.info(f"[{name}] {line.strip()}")
                        else:
                            logger.error(f"[{name}] {line.strip()}")

                # Start threads for logging
                threading.Thread(target=log_output, args=(process.stdout, "info"), daemon=True).start()
                threading.Thread(target=log_output, args=(process.stderr, "error"), daemon=True).start()

                return process

            # Start MCP Server
            mcp_cmd = [sys.executable, __file__, "mcp", "--port", str(args.mcp_port)]
            if args.db_uri:
                mcp_cmd.extend(["--db-uri", args.db_uri])
            mcp_process = run_component(mcp_cmd, "MCP Server")

            # Give MCP server time to start
            import time
            time.sleep(2)

            # Start Backend API
            api_cmd = [sys.executable, __file__, "api", "--port", str(args.api_port),
                      "--mcp-url", f"http://localhost:{args.mcp_port}"]
            if args.debug:
                api_cmd.append("--debug")
            if args.db_uri:
                api_cmd.extend(["--db-uri", args.db_uri])
            api_process = run_component(api_cmd, "Backend API")

            # Give API server time to start
            time.sleep(2)

            # Start Frontend
            frontend_cmd = [sys.executable, __file__, "frontend", "--port", str(args.frontend_port),
                           "--api-url", f"http://localhost:{args.api_port}"]
            frontend_process = run_component(frontend_cmd, "Frontend")

            # Wait for all processes to complete (or user interruption)
            try:
                frontend_process.wait()
            except KeyboardInterrupt:
                logger.info("Shutting down all components...")
                for process in [frontend_process, api_process, mcp_process]:
                    process.terminate()
                    process.wait()
                logger.info("All components shut down")

        elif args.mode == "init-db":
            logger.info("Initializing database schema")
            from ydrpolicy.backend.scripts.initialize_database import initialize_database
            initialize_database(db_uri=args.db_uri)

    except KeyboardInterrupt:
        logger.info("Application interrupted. Shutting down...")
    except Exception as e:
        logger.exception(f"Error running application in {args.mode} mode: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Detailed Component Descriptions

### MCP Server Component

The MCP (Model Context Protocol) Server exposes a set of specialized tools for policy retrieval and search. Based on the MCP protocol documentation, this server provides tools that can be used by LLMs like Claude:

1. **RAG Tool**: The primary tool for semantic policy retrieval

   - Accepts natural language queries
   - Uses OpenAI embeddings to find semantically relevant policy chunks
   - Returns relevant policy information with proper citations and context

2. **Keyword Search Tool**: For exact-match or pattern-based searches

   - Searches for specific terms, phrases, or patterns in policies
   - Uses PostgreSQL's full-text search capabilities
   - Returns matching policy segments with appropriate context

3. **Future Internet Search Tool**: Optional integration with external search capabilities
   - Could search publicly accessible policy repositories
   - Would provide supplementary information when local policies are insufficient

The MCP Server is designed to be stateless and highly responsive, making it suitable for high-throughput applications. All tool executions are logged in the database for auditing and improvement purposes.

### Backend API Component

The Backend API provides:

1. **Authentication Services**:

   - Simple JWT-based authentication using a defined list of Yale emails
   - Session management for maintaining user context
   - No complex user registration (uses predefined accounts)

2. **Chat Agent**:

   - Integration with OpenAI and Google Gemini models
   - Streaming responses for real-time interaction
   - Context management for multi-turn conversations
   - Intelligent tool selection based on query analysis
   - Memory of previous interactions within a conversation

3. **Policy Management**:

   - API endpoints for querying available policies
   - Not intended for direct policy CRUD (handled by the admin mode)

4. **Logging and Analytics**:
   - Comprehensive logging of all interactions
   - Usage analytics for understanding system utilization
   - Performance metrics for optimization

### Frontend Component

The frontend provides:

1. **Login Interface**:

   - Simple email/password authentication
   - No registration functionality (uses predefined accounts)

2. **Chat Interface**:

   - Design similar to ChatGPT's interface
   - Message streaming for real-time responses
   - Tool usage visibility (can be configured)
   - Markdown rendering for structured responses

3. **Conversation Management**:

   - Left sidebar for conversation history
   - Ability to create new conversations
   - Ability to continue existing conversations
   - Persistence across sessions

4. **Responsive Design**:
   - Works on desktop and mobile devices
   - Accessible design for all users

### Data Collection/Processing Component

The data collection and processing component consists of:

1. **Web Crawler**:

   - Uses Selenium for JavaScript-heavy sites
   - Configurable depth and scope
   - State maintenance for resumable crawling
   - Document discovery and download

2. **Content Scraper**:

   - Extracts relevant policy content from web pages
   - Processes downloaded documents (PDFs, DOCs, etc.)
   - Cleans and standardizes content formatting

3. **Policy Processor**:
   - Chunks policies into appropriate segments
   - Generates embeddings using OpenAI's API
   - Stores processed policies in the database
   - Updates existing policies when content changes

## Logging Strategy

Comprehensive logging is implemented at all levels:

1. **Application Logs**:

   - Standard logging for application events
   - Error tracking and debugging information
   - Component startup and shutdown events

2. **Database Logging**:

   - User actions (login, conversation creation)
   - Chat messages (both user and assistant)
   - Tool usage (inputs, outputs, timing)
   - Policy updates and additions

3. **Access Logs**:
   - HTTP request logging for security monitoring
   - API endpoint usage statistics
   - Performance metrics for optimization

All logs use structured formats where appropriate, making them suitable for analysis using standard tools.

## Testing Strategy

The project uses PyTest for comprehensive testing:

1. **Unit Tests**:

   - Test individual components in isolation
   - Mock dependencies for controlled testing
   - Test edge cases and error handling

2. **Integration Tests**:

   - Test component interactions
   - Ensure communication between services works
   - Test database operations

3. **End-to-End Tests**:
   - Test complete workflows
   - Simulate real-world usage patterns
   - Verify system behavior as a whole

The `tests/` directory structure mirrors the project structure, making it easy to locate tests for specific components.

## Development Workflow

Development can be conducted with different components running in separate Tmux sessions:

```bash
# Terminal 1: Run MCP Server
python main.py mcp --port 8001 --debug

# Terminal 2: Run Backend API
python main.py api --port 8000 --debug --mcp-url http://localhost:8001

# Terminal 3: Run Frontend
python main.py frontend --port 3000 --api-url http://localhost:8000
```

For production, the components can be managed using Supervisor or a similar process management tool, as defined in the provided `supervisord.conf` file.

## Deployment Considerations

The application is designed to be deployable in several configurations:

1. **Single-Server Deployment**:

   - All components on one physical server
   - Uses local network communication
   - Simplest deployment but limited scalability

2. **Multi-Server Deployment**:

   - Components distributed across multiple servers
   - Network communication between components
   - Better performance and scalability
   - Requires proper network configuration

3. **Container-Based Deployment**:
   - Each component in a separate container
   - Orchestration using Docker Compose or Kubernetes
   - Flexible deployment options
   - Simplified environment management

The provided `docker-compose.yml` file supports container-based deployment in development and production environments.

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

## Conclusion

This refined specification provides a comprehensive blueprint for the Yale Radiology Policies RAG Application. The system's modular design enables flexible deployment and usage patterns, while maintaining a consistent and reliable experience for users. The four distinct modes of operation ensure that the system can be integrated into various workflows and environments, maximizing its utility for Yale Radiology staff.
