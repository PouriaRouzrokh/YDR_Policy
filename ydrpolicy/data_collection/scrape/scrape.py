import logging
import os

from ydrpolicy.data_collection import config
import pandas as pd
from dotenv import load_dotenv
from ydrpolicy.data_collection.logger import DataCollectionLogger
from ydrpolicy.data_collection.scrape.scraper import scrape_policies

logger = DataCollectionLogger(
    name="scrape", 
    level=logging.INFO, 
    path=os.path.join(config.PROCESSED_DATA_DIR, "scrape.log")
)

def main():
    """Main function to run the policy extraction process."""       
    
    # Load environment variables
    load_dotenv()
    
    # Set up configuration using default values from config
    RAW_DATA_DIR = config.RAW_DATA_DIR
    SCRAPED_POLICIES_DIR = config.SCRAPED_POLICIES_DIR
    input_file = os.path.join(RAW_DATA_DIR, "crawled_policies_data.csv")
    model = config.SCRAPER_LLM_MODEL
    OPENAI_API_KEY = config.OPENAI_API_KEY
    
    # Validate environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment variables. Policy detection will not work.")
    
    # Create output directory if it doesn't exist
    os.makedirs(SCRAPED_POLICIES_DIR, exist_ok=True)
    
    # Log configuration settings
    logger.info(f"Starting policy extraction with the following settings:")
    logger.info(f"  - Input directory: {RAW_DATA_DIR}")
    logger.info(f"  - Input file: {input_file}")
    logger.info(f"  - Output directory: {SCRAPED_POLICIES_DIR}")
    logger.info(f"  - Scraping LLM model: {model}")

    # Read the original data
    input_path = os.path.join(RAW_DATA_DIR, input_file)
    logger.info(f"Reading input data from: {input_path}")
    original_df = pd.read_csv(input_path)

    # Extract policies
    df_with_policies = scrape_policies(
        original_df, 
        model=model,    
        api_key=OPENAI_API_KEY, 
        base_path=RAW_DATA_DIR,
        scraped_policies_dir=SCRAPED_POLICIES_DIR,
        logger=logger
    )
    
    # Save the scraped policies
    output_path = os.path.join(SCRAPED_POLICIES_DIR, "scraped_policies_data.csv")
    logger.info(f"Saving scraped policies to: {output_path}")
    df_with_policies.to_csv(output_path, index=False)
    logger.info("Policy extraction completed successfully")

if __name__ == "__main__":
    print("Yale Medicine Policy Scraper")
    print("============================")
    print("This script will extract policies from crawled Yale Medicine pages.")
    print(f"Results will be saved in the configured output directory.")
    print()
    
    logger.info("\n" + "="*80 + "\n" + "STARTING POLICY EXTRACTION PROCESS" + "\n" + "="*80)
    main()