"""
Configuration settings for the Yale Medicine crawler.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base URL to start crawling from
MAIN_URL = "https://medicine.yale.edu/diagnosticradiology/facintranet/policies"

# Domain restrictions
ALLOWED_DOMAINS = ["yale.edu", "medicine.yale.edu"]

# File types to process
DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS + ['.html', '.htm', '.php', '.aspx']

# Output directory settings
OUTPUT_DIR = "data2/crawled_data"
MARKDOWN_DIR = os.path.join(OUTPUT_DIR, "markdown_files")
DOCUMENT_DIR = os.path.join(OUTPUT_DIR, "documents")

# Maximum crawling depth
DEFAULT_MAX_DEPTH = 6

# Link filtering settings
FOLLOW_DEFINITE_LINKS_ONLY = False  # If True, only follow links the LLM considers "definite" policy content
                                    # If False, follow both "definite" and "probable" links

# Crawling behavior
REQUEST_TIMEOUT = 30
WAIT_TIME = 60

# LLM settings
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LLM_MODEL = "o3-mini"  # Use OpenAI's o3-mini model for all reasoning tasks
OCR_MODEL = "mistral-ocr-latest"