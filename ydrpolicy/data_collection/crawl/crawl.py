"""
Main entry point for the Yale Medicine crawler application.
"""
import logging
import os
from types import SimpleNamespace

from dotenv import load_dotenv

from ydrpolicy.data_collection.crawl.crawler import YaleCrawler
from ydrpolicy.data_collection.logger import DataCollectionLogger


def main(config: SimpleNamespace = None, logger: logging.Logger = None):
    """Main function to run the crawler."""
    # Load environment variables
    load_dotenv()

    # If no logger is provided, create a new one
    if logger is None:
        logger = DataCollectionLogger(
            name="crawl",
            level=logging.INFO,
            path=os.path.join(config.RAW_DATA_DIR, "crawl.log")
        )
    
    # Validate environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment variables. Policy detection will not work.")
    
    if not os.environ.get("MISTRAL_API_KEY"):
        logger.warning("MISTRAL_API_KEY not found in environment variables. PDF OCR processing will not work.")
    
    # Handle reset option (overrides resume)
    if config.RESET_CRAWL:
        from crawler_state import CrawlerState
        state_manager = CrawlerState(os.path.join(config.RAW_DATA_DIR, "state"), logger)
        state_manager.clear_state()
        logger.info("Crawler state has been reset. Starting fresh crawl.")
    
    
    # Display configuration settings
    logger.info(f"Starting crawler with the following settings:")
    logger.info(f"  - Starting URL: {config.MAIN_URL}")
    logger.info(f"  - Maximum depth: {config.DEFAULT_MAX_DEPTH}")
    logger.info(f"  - Follow definite links only: {config.FOLLOW_DEFINITE_LINKS_ONLY}")
    logger.info(f"  - Resume from previous state: {config.RESUME_CRAWL}")
    
    # Initialize and start the crawler
    try:
        crawler = YaleCrawler(
            config=config,
            logger=logger
        )
        crawler.start()
        
        logger.info(f"Crawling completed. Results saved to {config.RAW_DATA_DIR}")
        
    except KeyboardInterrupt:
        logger.info("Crawling stopped by user")
    except Exception as e:
        logger.error(f"Error during crawling: {str(e)}")

if __name__ == "__main__":
    from ydrpolicy.data_collection.config import config

    print("Yale Medicine Policy Crawler")
    print("============================")
    print("This script will crawl Yale Medicine pages for policies and guidelines.")
    print(f"All results will be saved in the '{config.RAW_DATA_DIR}' directory.")
    print(f"Logs will be saved to '{os.path.join(config.RAW_DATA_DIR, 'crawler.log')}'")
    print("Press Ctrl+C to stop the crawler at any time - state will be saved automatically.")
    print()

    logger = DataCollectionLogger(
        name="crawl",
        level=logging.INFO,
        path=os.path.join(config.RAW_DATA_DIR, "crawl.log")
    )

    # Create output directories before setting up logging
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    os.makedirs(config.MARKDOWN_DIR, exist_ok=True)
    os.makedirs(config.DOCUMENT_DIR, exist_ok=True)
    
    main(config=config, logger=logger)