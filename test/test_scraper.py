import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ydrpolicy.data_collection.scrape.scrape import main as scrape_main

def test_scraper():
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
    RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
    DOCUMENT_DIR = os.path.join(RAW_DATA_DIR, "documents")
    MARKDOWN_DIR = os.path.join(RAW_DATA_DIR, "markdown_files")
    PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
    SCRAPED_POLICIES_DIR = os.path.join(PROCESSED_DATA_DIR, "scraped_policies")

    config_dict = {
        "DATA_DIR": DATA_DIR,
        "RAW_DATA_DIR": RAW_DATA_DIR,
        "DOCUMENT_DIR": DOCUMENT_DIR,
        "MARKDOWN_DIR": MARKDOWN_DIR,
        "PROCESSED_DATA_DIR": PROCESSED_DATA_DIR,
        "SCRAPED_POLICIES_DIR": SCRAPED_POLICIES_DIR,
    }
    scrape_main(config_override=config_dict)

if __name__ == "__main__":
    test_scraper()