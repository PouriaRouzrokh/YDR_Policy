"""
Configuration settings for the Yale Medicine crawler.
"""
import os
from types import SimpleNamespace
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Create config dictionary first
_config_dict = {
    # Data directory settings
    "DATA_DIR": os.path.join(_BASE_DIR, "data2"),
    "RAW_DATA_DIR": os.path.join(_BASE_DIR, "data2", "raw"),
    "DOCUMENT_DIR": os.path.join(_BASE_DIR, "data2", "raw", "documents"),
    "MARKDOWN_DIR": os.path.join(_BASE_DIR, "data2", "raw", "markdown_files"),
    "PROCESSED_DATA_DIR": os.path.join(_BASE_DIR, "data2", "processed"),
    "SCRAPED_POLICIES_DIR": os.path.join(_BASE_DIR, "data2", "processed", "scraped_policies"),
    
    # LLM settings
    "MISTRAL_API_KEY": os.environ.get("MISTRAL_API_KEY"),
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
    "CRAWLER_LLM_MODEL": "o3-mini",  # Should be a reasoning model from OpenAI
    "SCRAPER_LLM_MODEL": "o3-mini",  # Should be a reasoning model from OpenAI
    "OCR_MODEL": "mistral-ocr-latest",
    
    # Crawler-specific settings
    "MAIN_URL": "https://medicine.yale.edu/diagnosticradiology/facintranet/policies",
    "ALLOWED_DOMAINS": ["yale.edu", "medicine.yale.edu"],
    "DOCUMENT_EXTENSIONS": ['.pdf', '.doc', '.docx'],
    "ALLOWED_EXTENSIONS": ['.pdf', '.doc', '.docx', '.html', '.htm', '.php', '.aspx'],
    "PRIORITY_KEYWORDS": [
        'policy', 'policies', 'guideline', 'guidelines', 'procedure', 'procedures',
        'protocol', 'protocols', 'radiology', 'diagnostic', 'imaging', 'safety',
        'radiation', 'contrast', 'mri', 'ct', 'ultrasound', 'xray', 'x-ray',
        'regulation', 'requirement', 'compliance', 'standard', 'documentation'
    ],
    "FOLLOW_DEFINITE_LINKS_ONLY": False,  # If False, follow both "definite" and "probable" links
    "DEFAULT_MAX_DEPTH": 6,
    "REQUEST_TIMEOUT": 30,
    "WAIT_TIME": 60,
    "RESUME_CRAWL": False,
    "RESET_CRAWL": False,
    "SAVE_INTERVAL": 10,
}

# Convert dictionary to an object with attributes
config = SimpleNamespace(**_config_dict)