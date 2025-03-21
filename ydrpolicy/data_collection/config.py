"""
Configuration settings for the Yale Medicine crawler.
"""
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --------------------------- Data directory settings --------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data2")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
DOCUMENT_DIR = os.path.join(RAW_DATA_DIR, "documents")
MARKDOWN_DIR = os.path.join(RAW_DATA_DIR, "markdown_files")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
SCRAPED_POLICIES_DIR = os.path.join(PROCESSED_DATA_DIR, "scraped_policies")

# ------------------------------ LLM settings ------------------------------

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CRAWLER_LLM_MODEL = "o3-mini"  # Should be a reasoning model from OpenAI
SCRAPER_LLM_MODEL = "o3-mini" # Should be a reasoning model from OpenAI
OCR_MODEL = "mistral-ocr-latest"

# ------------------------------ Crawler-specific settings ------------------------------   

## URL settings
MAIN_URL = "https://medicine.yale.edu/diagnosticradiology/facintranet/policies"
ALLOWED_DOMAINS = ["yale.edu", "medicine.yale.edu"]
DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS + ['.html', '.htm', '.php', '.aspx']   

## Crawling behavior
FOLLOW_DEFINITE_LINKS_ONLY = False  # If True, only follow links the LLM considers "definite" policy content
                                    # If False, follow both "definite" and "probable" links
DEFAULT_MAX_DEPTH = 6
REQUEST_TIMEOUT = 30        
WAIT_TIME = 60

## Crawler state
RESUME_CRAWL = False
RESET_CRAWL = False