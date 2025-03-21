"""
Main entry point for the Yale Medicine crawler application.
"""
import logging
import os

from ydrpolicy.data_collection import config
from ydrpolicy.data_collection.crawl.crawler import YaleCrawler
from dotenv import load_dotenv
from ydrpolicy.data_collection.logger import DataCollectionLogger

logger = DataCollectionLogger(
    name="crawl",
    level=logging.INFO,
    path=os.path.join(config.RAW_DATA_DIR, "crawl.log")
)

# Create output directories before setting up logging
os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
os.makedirs(config.MARKDOWN_DIR, exist_ok=True)
os.makedirs(config.DOCUMENT_DIR, exist_ok=True)

def main():
    """Main function to run the crawler."""
    # Load environment variables
    load_dotenv()
    
    # Set up configuration using default values from config
    url = config.MAIN_URL
    depth = config.DEFAULT_MAX_DEPTH
    follow_definite_only = config.FOLLOW_DEFINITE_LINKS_ONLY
    resume = config.RESUME_CRAWL  # Default: don't resume from previous state
    reset = config.RESET_CRAWL   # Default: don't reset existing crawl state
    
    # Validate environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment variables. Policy detection will not work.")
    
    if not os.environ.get("MISTRAL_API_KEY"):
        logger.warning("MISTRAL_API_KEY not found in environment variables. PDF OCR processing will not work.")
    
    # Handle reset option (overrides resume)
    if reset:
        from crawler_state import CrawlerState
        state_manager = CrawlerState(os.path.join(config.RAW_DATA_DIR, "state"), logger)
        state_manager.clear_state()
        logger.info("Crawler state has been reset. Starting fresh crawl.")
        resume = False
    
    # Display configuration settings
    logger.info(f"Starting crawler with the following settings:")
    logger.info(f"  - Starting URL: {url}")
    logger.info(f"  - Maximum depth: {depth}")
    logger.info(f"  - Follow definite links only: {follow_definite_only}")
    logger.info(f"  - Resume from previous state: {resume}")
    
    # Initialize and start the crawler
    try:
        crawler = YaleCrawler(max_depth=depth, resume=resume, logger=logger)
        crawler.start(initial_url=url)
        
        logger.info(f"Crawling completed. Results saved to {config.RAW_DATA_DIR}")
        
    except KeyboardInterrupt:
        logger.info("Crawling stopped by user")
    except Exception as e:
        logger.error(f"Error during crawling: {str(e)}", exc_info=True)

if __name__ == "__main__":
    print("Yale Medicine Policy Crawler")
    print("============================")
    print("This script will crawl Yale Medicine pages for policies and guidelines.")
    print(f"All results will be saved in the '{config.RAW_DATA_DIR}' directory.")
    print(f"Logs will be saved to '{os.path.join(config.RAW_DATA_DIR, 'crawler.log')}'")
    print("Press Ctrl+C to stop the crawler at any time - state will be saved automatically.")
    print()
    
    main()