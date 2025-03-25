import logging
import os
from types import SimpleNamespace

import pandas as pd
from dotenv import load_dotenv

from ydrpolicy.data_collection.logger import DataCollectionLogger
from ydrpolicy.data_collection.scrape.scraper import scrape_policies


def main(config: SimpleNamespace = None, logger: logging.Logger = None):
    """Main function to run the policy extraction process."""       
    # Load environment variables
    load_dotenv()

    # If no logger is provided, create a new one
    if logger is None:
        logger = DataCollectionLogger(
            name="scrape", 
            level=logging.INFO, 
            path=os.path.join(config.PROCESSED_DATA_DIR, "scrape.log")
        )
    
    # Get the path to the crawled policies data
    crawled_policies_data_path = os.path.join(config.RAW_DATA_DIR, "crawled_policies_data.csv")
    
    # Validate environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment variables. Policy detection will not work.")
    
    # Create output directory if it doesn't exist
    os.makedirs(config.SCRAPED_POLICIES_DIR, exist_ok=True)
    
    # Log configuration settings
    logger.info(f"Starting policy extraction with the following settings:")
    logger.info(f"  - Input directory: {config.RAW_DATA_DIR}")
    logger.info(f"  - Crawled policies dataframe path: {crawled_policies_data_path}")
    logger.info(f"  - Output directory: {config.SCRAPED_POLICIES_DIR}")
    logger.info(f"  - Scraping LLM model: {config.SCRAPER_LLM_MODEL}")

    # Read the original data
    logger.info(f"Reading input data from: {crawled_policies_data_path}")
    original_df = pd.read_csv(crawled_policies_data_path)

    # Extract policies
    df_with_policies = scrape_policies(
        original_df, 
        base_path=config.RAW_DATA_DIR,
        config=config,
        logger=logger
    )
    
    # Save the scraped policies
    output_path = os.path.join(config.PROCESSED_DATA_DIR, "scraped_policies_data.csv")
    logger.info(f"Saving scraped policies to: {output_path}")
    df_with_policies.to_csv(output_path, index=False)
    logger.info("Policy extraction completed successfully")

if __name__ == "__main__":
    from ydrpolicy.config import config

    print("Yale Medicine Policy Scraper")
    print("============================")
    print("This script will extract policies from crawled Yale Medicine pages.")
    print(f"Results will be saved in the configured output directory.")
    print()

    logger = DataCollectionLogger(
        name="scrape", 
        level=logging.INFO, 
        path=os.path.join(config.PROCESSED_DATA_DIR, "scrape.log")
    )
    
    logger.info("\n" + "="*80 + "\n" + "STARTING POLICY EXTRACTION PROCESS" + "\n" + "="*80)
    main(config=config, logger=logger)