# Yale Radiology Policies RAG Application - Comprehensive Project Specification

## Project Overview

The Yale Radiology Policies RAG Application is a comprehensive system designed to make departmental policies accessible and interactive through large language models (LLMs). This document details the complete architecture, components, and implementation approach.

### Big Picture

This project implements a unified system with three distinct layers:

1. **Data Acquisition Layer**: Specialized components for crawling the Yale intranet, identifying policy pages, and extracting/processing policy content using LLMs.

2. **Backend Layer**: Unified backend with MCP-compliant retrieval tools, chat agent functionality, and policy management services.

3. **Frontend Layer**: User interface for interacting with policies through a chat interface, with admin features for policy management.

These three layers support three distinct access patterns:

- Complete UI Experience for end users
- Chat Agent API for external applications
- MCP Retrieval Service for external AI applications

### Key Components

1. **Data Acquisition**:

   - Web crawler to discover policy pages on the Yale intranet
   - AI-powered scraper to extract and structure policy content
   - Processing pipeline to convert raw content to markdown documents

2. **Unified Backend**:

   - Shared database schema and migrations
   - MCP-compliant retrieval tools implementation
   - Chat agent with conversation management
   - Common services for authentication, policy management, etc.
   - Standardized API endpoints for all access patterns

3. **Frontend Application**:
   - Next.js-based user interface
   - Chat interface with history management
   - Policy browsing and searching
   - Administrative features

## Technology Stack

### Data Acquisition

- **Python 3.10+**: Core programming language
- **Beautiful Soup/Selenium**: Web crawling and parsing
- **Anthropic API (Claude)**: LLM for content extraction and classification
- **Pandas**: Data management for crawled URLs and metadata

### Backend

- **Python 3.10+**: Core programming language
- **FastAPI**: Web framework for building APIs with automatic OpenAPI documentation
- **SQLAlchemy**: ORM for database interactions
- **Alembic**: Database migration tool
- **PostgreSQL**: Primary relational database
- **pgvector**: PostgreSQL extension for vector similarity search
- **Pydantic**: Data validation and settings management
- **OpenAI API**: For embeddings and completions (GPT-4o)
- **Google Gemini API**: Alternative LLM provider (Gemini 1.5 Pro)
- **Anthropic API**: For Claude models (optional alternative)
- **python-dotenv**: Environment variable management
- **pytest**: Testing framework
- **Redis**: For caching and rate limiting (optional)

### Frontend

- **Next.js 14+**: React framework with server-side rendering capabilities
- **TypeScript**: Typed JavaScript
- **React**: UI library
- **Tailwind CSS**: Utility-first CSS framework
- **Shadcn/UI**: Component library built on Tailwind
- **React Query**: Data fetching and caching
- **JWT**: Authentication mechanism
- **Jest/React Testing Library**: Testing framework

### DevOps

- **Docker & Docker Compose**: Containerization
- **Nginx**: Reverse proxy for routing to different services
- **Supervisor**: Process management for multiple services on single server
- **Logging**: Structured logging with Python's logging module

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
│  Backend (FastAPI)                  │
│  [Port: 8000]                       │
│                                     │
│  - Database Models & Migrations     │
│  - Chat Agent API (/api/chat)       │
│  - MCP Server API (/api/mcp)        │
│  - Policy Management                │
│  - Authentication                   │
│                                     │
└──────────────────┬──────────────────┘
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
├── main.py                   # Entry point for different modes
│
├── data_collection/          # Data collection & processing components
│   ├── __init__.py           # Package initialization
│   ├── config.py             # Configuration for crawlers and LLMs
│   ├── crawl/                # Web crawler functionality
│   │   ├── __init__.py       # Package initialization
│   │   ├── crawler.py        # Main crawler for Yale intranet
│   │   ├── url_validator.py  # URL validation and filtering
│   │   └── intranet_auth.py  # Authentication for Yale intranet
│   │
│   ├── scrape/               # Policy extraction functionality
│   │   ├── __init__.py       # Package initialization
│   │   ├── scraper.py        # Main scraper for policy content
│   │   ├── llm_extractor.py  # LLM-based content extraction
│   │   └── policy_formatter.py # Format extracted policies
│   │
│   ├── processors/           # Content processing utilities
│   │   ├── __init__.py       # Package initialization
│   │   ├── html_to_text.py   # Convert HTML to text
│   │   ├── text_to_markdown.py # Convert text to markdown
│   │   └── document_cleaner.py # Clean up document formatting
│   │
│   └── tests/                # Tests for data collection
│       ├── __init__.py       # Test package initialization
│       ├── test_crawler.py   # Tests for crawler
│       └── test_scraper.py   # Tests for scraper
│
├── data/                     # Data storage (gitignored)
│   ├── raw/                  # Raw HTML/PDF files from crawler
│   ├── processed/            # Processed markdown policy files
│   ├── uploads/              # User uploaded documents
│   ├── backups/              # Database backups
│   └── auth/                 # Authentication data
│       └── authorized_users.json  # Pre-authorized users with passcodes
│
├── backend/                  # Unified backend code
│   ├── __init__.py           # Package initialization
│   ├── app.py                # FastAPI application entry point
│   ├── config.py             # Configuration settings using Pydantic
│   ├── constants.py          # Constant values and enumerations
│   ├── logger.py             # Logging configuration
│   ├── exceptions.py         # Custom exception definitions
│   │
│   ├── database/             # Database models & operations
│   │   ├── __init__.py       # Package initialization
│   │   ├── engine.py         # SQLAlchemy engine and session setup
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── repository/       # Repository pattern implementations
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── base.py       # Base repository class
│   │   │   ├── users.py      # User repository
│   │   │   ├── policies.py   # Policy repository
│   │   │   ├── chat.py       # Chat history repository
│   │   │   ├── api_usage.py  # API usage tracking repository
│   │   │   └── feedback.py   # User feedback repository
│   │   └── migrations/       # Alembic migrations
│   │       ├── versions/     # Migration scripts
│   │       ├── env.py        # Alembic environment
│   │       ├── script.py.mako # Migration template
│   │       └── alembic.ini   # Alembic configuration
│   │
│   ├── services/             # Shared business logic services
│   │   ├── __init__.py       # Package initialization
│   │   ├── auth_service.py   # Authentication logic
│   │   ├── vector_store.py   # Vector DB operations
│   │   ├── search_service.py # Search service (full-text + vector)
│   │   ├── embeddings.py     # Text embedding logic with OpenAI
│   │   ├── chunking.py       # Text chunking strategies
│   │   ├── policy_service.py # Policy processing service
│   │   └── usage_tracking.py # API usage tracking service
│   │
│   ├── mcp/                  # MCP Server implementation
│   │   ├── __init__.py       # Package initialization
│   │   ├── tools/            # MCP-compliant tools
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── base_tool.py  # Abstract MCP tool interface
│   │   │   ├── naive_rag.py  # Simple RAG implementation
│   │   │   ├── graph_rag.py  # Graph-based RAG implementation
│   │   │   ├── keyword_search.py # Full-text search implementation
│   │   │   └── hybrid_search.py # Hybrid search implementation
│   │   ├── schemas.py        # MCP-specific Pydantic schemas
│   │   ├── router.py         # FastAPI router for MCP endpoints
│   │   └── service.py        # MCP service implementation
│   │
│   ├── chat/                 # Chat Agent implementation
│   │   ├── __init__.py       # Package initialization
│   │   ├── agents/           # LLM agents
│   │   │   ├── __init__.py   # Package initialization
│   │   │   ├── base_agent.py # Abstract base agent
│   │   │   ├── chat_agent.py # Main chat agent implementation
│   │   │   ├── prompt_templates.py # Prompt engineering templates
│   │   │   ├── openai_provider.py # OpenAI API handler
│   │   │   └── gemini_provider.py # Google Gemini API handler
│   │   ├── schemas.py        # Chat-specific Pydantic schemas
│   │   ├── router.py         # FastAPI router for chat endpoints
│   │   └── service.py        # Chat service implementation
│   │
│   ├── api/                  # API endpoints
│   │   ├── __init__.py       # Package initialization
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── chat.py           # Chat endpoints
│   │   ├── mcp.py            # MCP endpoints
│   │   ├── policies.py       # Policy management endpoints
│   │   ├── about.py          # About page content endpoint
│   │   └── feedback.py       # User feedback endpoints
│   │
│   ├── schemas/              # Shared Pydantic schemas
│   │   ├── __init__.py       # Package initialization
│   │   ├── auth.py           # Auth-related schemas
│   │   ├── policy.py         # Policy-related schemas
│   │   ├── about.py          # About page schemas
│   │   ├── api_usage.py      # API usage tracking schemas
│   │   └── feedback.py       # Feedback-related schemas
│   │
│   ├── middleware/           # Middleware components
│   │   ├── __init__.py       # Package initialization
│   │   ├── auth_middleware.py # JWT validation middleware
│   │   ├── error_handler.py  # Error handling middleware
│   │   ├── usage_tracker.py  # API usage tracking middleware
│   │   └── logging_middleware.py # Request logging middleware
│   │
│   └── tests/                # Backend tests
│       ├── __init__.py       # Test package initialization
│       ├── conftest.py       # Test fixtures
│       ├── test_api/         # API endpoint tests
│       ├── test_services/    # Service-level tests
│       ├── test_mcp/         # MCP tool tests
│       └── test_chat/        # Chat agent tests
│
├── frontend/                 # Next.js Frontend
    ├── .eslintrc.json       # ESLint configuration
    ├── next.config.js       # Next.js configuration
    ├── package.json         # NPM dependencies
    ├── tsconfig.json        # TypeScript configuration
    ├── tailwind.config.js   # Tailwind CSS configuration
    │
    ├── public/              # Static files
    │   ├── favicon.ico      # Site favicon
    │   ├── yale-logo.svg    # Yale logo
    │   └── images/          # Image assets
    │
    └── src/                 # Source code
        ├── app/             # Next.js app router
        │   ├── layout.tsx   # Root layout
        │   ├── page.tsx     # Landing page
        │   ├── login/       # Login route
        │   ├── dashboard/   # Main dashboard route
        │   ├── chat/        # Chat interface
        │   │   ├── page.tsx # Main chat page
        │   │   └── history/ # Chat history management
        │   ├── policies/    # Policy management
        │   ├── about/       # About page
        │   └── profile/     # User profile
        │
        ├── components/      # Reusable components
        │   ├── ui/          # Base UI components
        │   ├── auth/        # Login components
        │   ├── chat/        # Chat interface components
        │   │   ├── ChatInterface.tsx # Main chat UI component
        │   │   ├── ChatMessage.tsx   # Individual message component
        │   │   ├── ChatSelector.tsx  # Chat history selector
        │   │   ├── NewChatButton.tsx # Start new chat button
        │   │   ├── DeleteChatButton.tsx # Delete chat button
        │   │   ├── SearchMethodSelector.tsx # Search method selector
        │   │   ├── ModelSelector.tsx # OpenAI/Gemini selector
        │   │   └── FeedbackButtons.tsx # Feedback UI component
        │   ├── policies/    # Policy viewing components
        │   ├── about/       # About page components
        │   └── layout/      # Layout components
        │
        ├── hooks/           # Custom React hooks
        ├── services/        # API client services
        ├── types/           # TypeScript types
        ├── utils/           # Utility functions
        ├── styles/          # Global styles
        └── tests/           # Frontend tests
```

## Data Collection Components

### 1. Crawler Implementation

The crawler is responsible for discovering policy pages on the Yale Radiology intranet:

#### `data_collection/crawl/crawler.py`

```python
import requests
import pandas as pd
import os
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from .intranet_auth import authenticate_yale_intranet
from .url_validator import is_policy_url, normalize_url

class YaleRadiologyCrawler:
    """Crawler for Yale Radiology intranet to discover policy pages"""

    def __init__(self, base_url, output_dir, credentials=None, max_pages=None):
        """
        Initialize the crawler

        Args:
            base_url: Starting URL for crawling
            output_dir: Directory to store results
            credentials: Dict with username and password for intranet
            max_pages: Maximum number of pages to crawl (None for unlimited)
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.credentials = credentials
        self.max_pages = max_pages

        # Initialize tracking structures
        self.visited_urls = set()
        self.to_visit = [base_url]
        self.found_policies = []

        # Setup logging
        self.logger = logging.getLogger("yale_crawler")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Setup session
        self.session = requests.Session()
        if credentials:
            authenticate_yale_intranet(self.session, credentials)

    def extract_links(self, url, html_content):
        """Extract links from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(url, href)

            # Only include URLs from the same domain
            if urlparse(full_url).netloc == urlparse(self.base_url).netloc:
                normalized_url = normalize_url(full_url)
                if normalized_url not in self.visited_urls:
                    links.append(normalized_url)

        return links

    def save_html(self, url, content):
        """Save HTML content to file"""
        url_path = urlparse(url).path
        if url_path.endswith('/'):
            url_path = url_path[:-1]

        # Create a filename based on the URL path
        filename = url_path.replace('/', '_')
        if not filename:
            filename = 'index'

        filepath = os.path.join(self.output_dir, 'raw', f"{filename}.html")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def is_policy_page(self, url, html_content):
        """
        Determine if a page contains policies

        This is a simple heuristic approach - could be enhanced with
        more sophisticated NLP/ML techniques
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Check URL pattern
        if is_policy_url(url):
            return True

        # Check page content for policy indicators
        text = soup.get_text().lower()
        policy_keywords = ['policy', 'procedure', 'guideline', 'protocol', 'standard']

        # Check if the page has policy keywords
        if any(keyword in text for keyword in policy_keywords):
            # Additional checks for policy content...
            h_tags = soup.find_all(['h1', 'h2', 'h3'])
            for tag in h_tags:
                if any(keyword in tag.get_text().lower() for keyword in policy_keywords):
                    return True

        return False

    def crawl(self):
        """Crawl the Yale Radiology intranet"""
        count = 0

        while self.to_visit and (self.max_pages is None or count < self.max_pages):
            # Get next URL to visit
            url = self.to_visit.pop(0)

            if url in self.visited_urls:
                continue

            self.visited_urls.add(url)
            count += 1

            self.logger.info(f"Crawling {url} ({count}/{self.max_pages if self.max_pages else 'unlimited'})")

            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                html_content = response.text

                # Check if this is a policy page
                if self.is_policy_page(url, html_content):
                    filepath = self.save_html(url, html_content)
                    self.found_policies.append({
                        'url': url,
                        'title': self.extract_title(html_content),
                        'discovered_at': datetime.now().isoformat(),
                        'file_path': filepath
                    })
                    self.logger.info(f"Found policy page: {url}")

                # Extract links from this page
                new_links = self.extract_links(url, html_content)
                for link in new_links:
                    if link not in self.visited_urls and link not in self.to_visit:
                        self.to_visit.append(link)

            except Exception as e:
                self.logger.error(f"Error crawling {url}: {str(e)}")

        # Save discovered policies to CSV
        self.save_results()

        return self.found_policies

    def extract_title(self, html_content):
        """Extract the title of a page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.find('title')

        if title_tag:
            return title_tag.get_text().strip()

        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()

        return "Unknown Title"

    def save_results(self):
        """Save crawling results to CSV"""
        if self.found_policies:
            df = pd.DataFrame(self.found_policies)
            output_path = os.path.join(self.output_dir, 'policy_pages.csv')
            df.to_csv(output_path, index=False)
            self.logger.info(f"Saved {len(self.found_policies)} policy pages to {output_path}")
```

### 2. Scraper Implementation

The scraper extracts structured policy content from discovered pages using LLMs:

#### `data_collection/scrape/scraper.py`

```python
import os
import pandas as pd
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .llm_extractor import extract_policy_with_llm
from .policy_formatter import format_policy_as_markdown
from ..processors.document_cleaner import clean_document

class PolicyScraper:
    """
    Extract policy content from HTML files using LLM assistance
    """

    def __init__(self, input_csv, raw_dir, output_dir, llm_config=None, max_workers=4):
        """
        Initialize the policy scraper

        Args:
            input_csv: Path to CSV with policy pages info
            raw_dir: Directory with raw HTML files
            output_dir: Directory to save extracted policies
            llm_config: Configuration for LLM (model, api_key, etc)
            max_workers: Maximum number of parallel workers
        """
        self.input_csv = input_csv
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        self.llm_config = llm_config or {}
        self.max_workers = max_workers

        # Setup logging
        self.logger = logging.getLogger("policy_scraper")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def load_policy_pages(self):
        """Load the list of policy pages from CSV"""
        try:
            df = pd.read_csv(self.input_csv)
            self.logger.info(f"Loaded {len(df)} policy pages from {self.input_csv}")
            return df
        except Exception as e:
            self.logger.error(f"Error loading policy pages: {str(e)}")
            return pd.DataFrame()

    def process_policy_page(self, row):
        """Process a single policy page"""
        url = row['url']
        file_path = row['file_path']

        try:
            # Read HTML content
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Clean the document
            cleaned_text = clean_document(html_content)

            # Extract policy with LLM
            policy_content = extract_policy_with_llm(
                cleaned_text,
                url=url,
                llm_config=self.llm_config
            )

            if not policy_content:
                self.logger.warning(f"No policy content extracted from {url}")
                return None

            # Format as markdown
            markdown_content = format_policy_as_markdown(policy_content)

            # Generate output filename
            policy_id = Path(file_path).stem
            output_file = os.path.join(self.output_dir, f"{policy_id}.md")

            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            self.logger.info(f"Processed policy from {url} -> {output_file}")

            return {
                'url': url,
                'title': policy_content.get('title', row.get('title', 'Unknown Title')),
                'output_file': output_file,
                'word_count': len(markdown_content.split()),
                'success': True
            }

        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")
            return {
                'url': url,
                'error': str(e),
                'success': False
            }

    def run(self):
        """Run the scraper on all policy pages"""
        # Load policy pages
        df = self.load_policy_pages()
        if df.empty:
            return []

        results = []

        # Process pages in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.process_policy_page, row): row['url']
                for _, row in df.iterrows()
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing {url}: {str(e)}")

        # Save processing results
        success_count = sum(1 for r in results if r.get('success', False))
        self.logger.info(f"Processed {len(results)} pages, {success_count} successful")

        # Save results to CSV
        results_df = pd.DataFrame(results)
        results_path = os.path.join(os.path.dirname(self.output_dir), 'scraping_results.csv')
        results_df.to_csv(results_path, index=False)

        return results
```

### 3. LLM Extractor Implementation

#### `data_collection/scrape/llm_extractor.py`

```python
import anthropic
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("llm_extractor")

def extract_policy_with_llm(text: str, url: str = None, llm_config: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    Extract structured policy information from text using Claude

    Args:
        text: The policy document text
        url: Source URL (optional)
        llm_config: Configuration for LLM

    Returns:
        Dictionary with extracted policy information or None if extraction failed
    """
    # Get configuration
    config = llm_config or {}
    api_key = config.get('api_key')
    model = config.get('model', 'claude-3-opus-20240229')
    max_tokens = config.get('max_tokens', 4000)

    if not api_key:
        logger.error("No API key provided for LLM extraction")
        return None

    client = anthropic.Anthropic(api_key=api_key)

    # Truncate text if too long
    max_text_length = 100000  # Claude has a token limit, and we need room for the prompt
    if len(text) > max_text_length:
        text = text[:max_text_length] + "\n\n[Text truncated due to length...]"

    # Create prompt with extraction instructions
    prompt = f"""
You are an expert at extracting formal policies from web pages.
You will be given text from a Yale Radiology department page that may contain policies or procedures.

Your task is to:
1. Identify if this page contains a formal policy or procedure
2. Extract the full policy content, maintaining its structure and formatting
3. Provide the extracted information in a structured JSON format

Only extract content that appears to be an actual policy or procedure. Ignore navigation elements, headers, footers, and other non-policy content.

URL: {url or "Unknown"}

TEXT:
{text}

If the page contains a policy, respond with a JSON object with the following structure:
{{
  "is_policy": true,
  "title": "The policy title",
  "effective_date": "Date when policy is effective (if mentioned)",
  "policy_id": "Any policy ID or number mentioned",
  "content": "The full policy text, preserving sections and structure",
  "sections": [
    {{
      "title": "Section title (e.g., Scope, Purpose, Procedure)",
      "content": "Text content of this section"
    }}
  ]
}}

If the page does not contain a policy, respond with:
{{
  "is_policy": false,
  "reason": "Brief explanation of why this isn't a policy"
}}

Provide ONLY the JSON output, nothing else.
    """

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0.1,  # Low temperature for factual extraction
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract JSON from response
        result_text = response.content[0].text

        # Parse JSON
        try:
            result = json.loads(result_text)

            # Return None if not a policy
            if not result.get('is_policy', False):
                logger.info(f"Not a policy document: {result.get('reason', 'Unknown reason')}")
                return None

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from LLM response: {str(e)}")
            logger.debug(f"LLM response: {result_text}")
            return None

    except Exception as e:
        logger.error(f"Error in LLM extraction: {str(e)}")
        return None
```

### 4. Policy Formatter Implementation

#### `data_collection/scrape/policy_formatter.py`

```python
from typing import Dict, Any

def format_policy_as_markdown(policy_data: Dict[str, Any]) -> str:
    """
    Format extracted policy data as markdown
```
