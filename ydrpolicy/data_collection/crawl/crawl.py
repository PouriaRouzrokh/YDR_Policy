"""
Main entry point for the Yale Medicine crawler application.
"""
import argparse
import logging
import os

import config
from crawler import YaleCrawler
from dotenv import load_dotenv
from logger import DataCollectionLogger

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
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Yale Medicine Policy Crawler')
    parser.add_argument('--url', type=str, default=config.MAIN_URL,
                        help=f'URL to start crawling from (default: {config.MAIN_URL})')
    parser.add_argument('--depth', type=int, default=config.DEFAULT_MAX_DEPTH,
                        help=f'Maximum crawling depth (default: {config.DEFAULT_MAX_DEPTH})')
    parser.add_argument('--definite-only', action='store_true',
                        help='Follow only definite policy links (overrides config setting)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last crawl state if available')
    parser.add_argument('--reset', action='store_true',
                        help='Reset (delete) any existing crawl state and start fresh')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    # Validate environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment variables. Policy detection will not work.")
    
    if not os.environ.get("MISTRAL_API_KEY"):
        logger.warning("MISTRAL_API_KEY not found in environment variables. PDF OCR processing will not work.")
    
    # Check if definite-only flag is set
    if args.definite_only:
        config.FOLLOW_DEFINITE_LINKS_ONLY = True
        logger.info("Command-line flag set to follow only definite policy links")
    
    # Handle reset option (overrides resume)
    if args.reset:
        from crawler_state import CrawlerState
        state_manager = CrawlerState(os.path.join(config.RAW_DATA_DIR, "state"), logger)
        state_manager.clear_state()
        logger.info("Crawler state has been reset. Starting fresh crawl.")
        resume = False
    else:
        resume = args.resume
    
    # Display configuration settings
    logger.info(f"Starting crawler with the following settings:")
    logger.info(f"  - Starting URL: {args.url}")
    logger.info(f"  - Maximum depth: {args.depth}")
    logger.info(f"  - Follow definite links only: {config.FOLLOW_DEFINITE_LINKS_ONLY}")
    logger.info(f"  - Resume from previous state: {resume}")
    
    # Initialize and start the crawler
    try:
        crawler = YaleCrawler(max_depth=args.depth, resume=resume, logger=logger)
        crawler.start(initial_url=args.url)
        
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