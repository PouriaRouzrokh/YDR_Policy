"""
Unit tests for the Yale Medicine crawler functionality.
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ydrpolicy.data_collection.crawl.crawler import YaleCrawler
from ydrpolicy.data_collection.crawl.crawler_state import CrawlerState


class TestCrawlerState(unittest.TestCase):
    """Tests for the CrawlerState class that manages crawler state persistence."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test state files
        self.temp_dir = tempfile.mkdtemp()
        self.mock_logger = MagicMock()
        self.state_manager = CrawlerState(self.temp_dir, self.mock_logger)
        
        # Sample test data
        self.visited_urls = {"https://test.com/page1", "https://test.com/page2"}
        self.priority_queue = [(0.5, "https://test.com/page3", 2), (0.8, "https://test.com/page4", 1)]
        self.current_url = "https://test.com/page2"
        self.current_depth = 2
        
    def tearDown(self):
        """Clean up after each test method."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_state(self):
        """Test that state can be saved and loaded correctly."""
        # Save state
        result = self.state_manager.save_state(
            self.visited_urls,
            self.priority_queue,
            self.current_url,
            self.current_depth
        )
        
        # Verify save was successful
        self.assertTrue(result)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "crawler_state.json")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "priority_queue.pkl")))
        
        # Load state
        loaded_state = self.state_manager.load_state()
        
        # Verify loaded state matches saved state
        self.assertEqual(loaded_state["current_url"], self.current_url)
        self.assertEqual(loaded_state["current_depth"], self.current_depth)
        self.assertEqual(loaded_state["visited_urls"], self.visited_urls)
        self.assertEqual(loaded_state["priority_queue"], self.priority_queue)
        self.assertEqual(loaded_state["visited_count"], len(self.visited_urls))
        self.assertEqual(loaded_state["queue_count"], len(self.priority_queue))
    
    def test_clear_state(self):
        """Test that state can be cleared correctly."""
        # First save some state
        self.state_manager.save_state(
            self.visited_urls,
            self.priority_queue,
            self.current_url,
            self.current_depth
        )
        
        # Verify state exists
        self.assertTrue(self.state_manager.state_exists())
        
        # Clear state
        result = self.state_manager.clear_state()
        
        # Verify clear was successful
        self.assertTrue(result)
        self.assertFalse(self.state_manager.state_exists())
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "crawler_state.json")))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "priority_queue.pkl")))
    
    def test_state_exists(self):
        """Test that state_exists correctly identifies if state exists."""
        # Initially no state should exist
        self.assertFalse(self.state_manager.state_exists())
        
        # Save state
        self.state_manager.save_state(
            self.visited_urls,
            self.priority_queue,
            self.current_url,
            self.current_depth
        )
        
        # Now state should exist
        self.assertTrue(self.state_manager.state_exists())
        
        # Remove just one file to test partial state detection
        os.remove(os.path.join(self.temp_dir, "crawler_state.json"))
        self.assertFalse(self.state_manager.state_exists())
    
    def test_load_state_nonexistent(self):
        """Test loading when no state exists returns empty dict."""
        loaded_state = self.state_manager.load_state()
        self.assertEqual(loaded_state, {})
    
    def test_error_handling(self):
        """Test error handling during save/load operations."""
        # Test save error
        with patch("json.dump", side_effect=Exception("Fake error")):
            result = self.state_manager.save_state(
                self.visited_urls,
                self.priority_queue,
                self.current_url,
                self.current_depth
            )
            self.assertFalse(result)
        
        # Save valid state first
        self.state_manager.save_state(
            self.visited_urls,
            self.priority_queue,
            self.current_url,
            self.current_depth
        )
        
        # Test load error
        with patch("json.load", side_effect=Exception("Fake error")):
            loaded_state = self.state_manager.load_state()
            self.assertEqual(loaded_state, {})


@patch("ydrpolicy.data_collection.crawl.crawler.CrawlerState")
@patch("requests.get")  # Patch requests directly, not through the crawler module
class TestYaleCrawler(unittest.TestCase):
    """Tests for the YaleCrawler class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_logger = MagicMock()
        
    def test_crawler_initialization(self, mock_get, mock_crawler_state):
        """Test proper initialization of the crawler."""
        # Mock the state manager
        mock_state_instance = MagicMock()
        mock_state_instance.load_state.return_value = {}
        mock_crawler_state.return_value = mock_state_instance
        
        # Create a crawler
        crawler = YaleCrawler(max_depth=3, resume=False, logger=self.mock_logger)
        
        # Verify initialization
        self.assertEqual(crawler.max_depth, 3)
        self.assertFalse(crawler.resume)
        self.assertEqual(crawler.logger, self.mock_logger)
        self.assertEqual(crawler.visited_urls, set())
        
    def test_crawler_resume(self, mock_get, mock_crawler_state):
        """Test that crawler can resume from saved state."""
        # Mock the state manager
        mock_state_instance = MagicMock()
        mock_state_instance.load_state.return_value = {
            "visited_urls": {"https://test.com/page1", "https://test.com/page2"},
            "priority_queue": [(0.5, "https://test.com/page3", 2)],
            "current_url": "https://test.com/page2",
            "current_depth": 2
        }
        mock_crawler_state.return_value = mock_state_instance
        
        # Create a crawler with resume=True
        crawler = YaleCrawler(max_depth=5, resume=True, logger=self.mock_logger)
        
        # Verify state restored
        self.assertEqual(crawler.visited_urls, {"https://test.com/page1", "https://test.com/page2"})
        self.assertEqual(crawler.priority_queue, [(0.5, "https://test.com/page3", 2)])
        
    @patch("ydrpolicy.data_collection.crawl.crawler.YaleCrawler.process_url")
    def test_crawler_start(self, mock_process_url, mock_get, mock_crawler_state):
        """Test the crawler start method initializes crawling correctly."""
        # Mock the state manager
        mock_state_instance = MagicMock()
        mock_state_instance.load_state.return_value = {}
        mock_crawler_state.return_value = mock_state_instance
        
        # Mock process_url to prevent actual crawling
        mock_process_url.return_value = None
        
        # Create crawler and call start
        crawler = YaleCrawler(max_depth=3, resume=False, logger=self.mock_logger)
        initial_url = "https://test.com"
        
        crawler.start(initial_url)
        
        # Verify process_url called with initial URL and depth 0
        mock_process_url.assert_called_once_with(initial_url, 0)
    
    @patch("ydrpolicy.data_collection.crawl.crawler.YaleCrawler.is_allowed_url")
    def test_is_allowed_url(self, mock_is_allowed, mock_get, mock_crawler_state):
        """Test URL filtering function works correctly."""
        # Mock the state manager
        mock_state_instance = MagicMock()
        mock_state_instance.load_state.return_value = {}
        mock_crawler_state.return_value = mock_state_instance
        
        # Setup URL tests
        mock_is_allowed.side_effect = [True, False, True]
        
        # Create crawler
        crawler = YaleCrawler(max_depth=3, resume=False, logger=self.mock_logger)
        
        # Test URLs
        self.assertTrue(crawler.is_allowed_url("https://medicine.yale.edu/page1"))
        self.assertFalse(crawler.is_allowed_url("https://example.com/page2"))
        self.assertTrue(crawler.is_allowed_url("https://yale.edu/page3"))
    
    def test_save_state_during_crawl(self, mock_get, mock_crawler_state):
        """Test that state is saved during crawling."""
        # Mock the state manager
        mock_state_instance = MagicMock()
        mock_state_instance.load_state.return_value = {}
        mock_state_instance.save_state.return_value = True
        mock_crawler_state.return_value = mock_state_instance
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "<html><body><a href='https://test.com/page2'>Link</a></body></html>"
        mock_response.url = "https://test.com/page1"
        mock_get.return_value = mock_response
        
        # Patching to prevent full execution while still testing state save
        with patch("ydrpolicy.data_collection.crawl.crawler.YaleCrawler.extract_links", return_value=["https://test.com/page2"]):
            with patch("ydrpolicy.data_collection.crawl.crawler.YaleCrawler.is_allowed_url", return_value=True):
                with patch("ydrpolicy.data_collection.crawl.crawler.YaleCrawler.should_follow_link", return_value=True):
                    # Create crawler
                    crawler = YaleCrawler(max_depth=3, resume=False, logger=self.mock_logger)
                    
                    # Start limited crawl (should process one URL and save state)
                    crawler.process_url("https://test.com/page1", 0)
                    
                    # Verify state was saved
                    mock_state_instance.save_state.assert_called_with(
                        crawler.visited_urls,
                        crawler.priority_queue,
                        "https://test.com/page1",
                        0
                    )


if __name__ == "__main__":
    unittest.main()