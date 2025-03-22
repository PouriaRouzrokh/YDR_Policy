import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ydrpolicy.data_collection.crawl.crawl import main as crawl_main
from ydrpolicy.data_collection.config import config

def test_crawler():
    config.DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
    config.RAW_DATA_DIR = os.path.join(config.DATA_DIR, "raw")
    config.DOCUMENT_DIR = os.path.join(config.RAW_DATA_DIR, "documents")
    config.MARKDOWN_DIR = os.path.join(config.RAW_DATA_DIR, "markdown_files")
    config.PROCESSED_DATA_DIR = os.path.join(config.DATA_DIR, "processed")
    config.SCRAPED_POLICIES_DIR = os.path.join(config.PROCESSED_DATA_DIR, "scraped_policies")
    config.MAX_DEPTH = 1

    crawl_main(config=config)

if __name__ == "__main__":  
    test_crawler()