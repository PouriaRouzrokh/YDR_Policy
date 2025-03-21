import logging
import os
import argparse
from dotenv import load_dotenv
import pandas as pd
import config

# Local imports
from logger import DataCollectionLogger
from scraper import scrape_policies

logger = DataCollectionLogger(
    name="scrape", 
    level=logging.INFO, 
    path=os.path.join(config.PROCESSED_DATA_DIR, "scrape.log")
)

def main():
    """Main function to run the policy extraction process."""       
    
    # Load environment variables
    load_dotenv()
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Yale Medicine Policy Scraper')
    parser.add_argument('--input-file', type=str, default="crawled_policies_data.csv",
                       help='Input CSV file name (default: crawled_policies_data.csv)')
    parser.add_argument('--input-dir', type=str, default=config.RAW_DATA_DIR,
                       help=f'Directory containing input file (default: {config.RAW_DATA_DIR})')
    parser.add_argument('--output-dir', type=str, default=config.SCRAPED_POLICIES_DIR,
                       help=f'Directory to save scraped policies (default: {config.SCRAPED_POLICIES_DIR})')
    parser.add_argument('--model', type=str, default=config.SCRAPER_LLM_MODEL,
                       help=f'LLM model to use for scraping (default: {config.SCRAPER_LLM_MODEL})')
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
    
    # Get config variables with command-line overrides
    RAW_DATA_DIR = args.input_dir
    SCRAPED_POLICIES_DIR = args.output_dir
    model = args.model
    OPENAI_API_KEY = config.OPENAI_API_KEY
    
    # Create output directory if it doesn't exist
    os.makedirs(SCRAPED_POLICIES_DIR, exist_ok=True)
    
    # Log configuration settings
    logger.info(f"Starting policy extraction with the following settings:")
    logger.info(f"  - Input directory: {RAW_DATA_DIR}")
    logger.info(f"  - Input file: {args.input_file}")
    logger.info(f"  - Output directory: {SCRAPED_POLICIES_DIR}")
    logger.info(f"  - Scraping LLM model: {model}")

    # Read the original data
    input_path = os.path.join(RAW_DATA_DIR, args.input_file)
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
    print("Use --help for more options.")
    print()
    
    logger.info("\n" + "="*80 + "\n" + "STARTING POLICY EXTRACTION PROCESS" + "\n" + "="*80)
    main()