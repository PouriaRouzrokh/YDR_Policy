"""
Module for web crawling and link extraction using priority-based algorithm with resume capability.
"""
import heapq
import json
import logging
import os
import re
import signal
import time
import urllib.parse
from typing import List, Optional, Tuple
from types import SimpleNamespace
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ydrpolicy.data_collection.crawl.crawler_state import CrawlerState
from ydrpolicy.data_collection.crawl.processors.document_processor import (
    convert_to_markdown, download_document, html_to_markdown)
from ydrpolicy.data_collection.crawl.processors.llm_processor import \
    analyze_content_for_policies
from ydrpolicy.data_collection.crawl.processors.pdf_processor import \
    pdf_to_markdown


class YaleCrawler:
    """Class for crawling Yale Medicine webpages and documents using priority-based algorithm."""
    
    def __init__(
            self, 
            config: SimpleNamespace,
            logger: logging.Logger = None
        ):
        """
        Initialize the crawler.
        
        Args:
            max_depth: Maximum depth to crawl
            resume: Whether to try to resume from a previous crawl
            logger: Logger for logging messages
        """
        self.config = config
        self.max_depth = config.DEFAULT_MAX_DEPTH
        self.visited_urls = set()
        self.priority_queue = []  # Priority queue of (priority, url, depth)
        self.driver = None
        self.current_url = None
        self.current_depth = 0  
        self.resume = config.RESUME_CRAWL
        self.logger = logger        
        self.state_manager = CrawlerState(os.path.join(config.RAW_DATA_DIR, "state"), logger)
        
        # Flag to track if the crawler is stopping gracefully
        self.stopping = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Keywords for priority scoring
        self.priority_keywords = [
            'policy', 'policies', 'guideline', 'guidelines', 'procedure', 'procedures',
            'protocol', 'protocols', 'radiology', 'diagnostic', 'imaging', 'safety',
            'radiation', 'contrast', 'mri', 'ct', 'ultrasound', 'xray', 'x-ray',
            'regulation', 'requirement', 'compliance', 'standard', 'documentation'
        ]
        
        # Create output directories
        os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
        os.makedirs(config.MARKDOWN_DIR, exist_ok=True)
        os.makedirs(config.DOCUMENT_DIR, exist_ok=True)
        
        # Initialize the data tracking CSV
        self.policies_df_path = os.path.join(config.RAW_DATA_DIR, "crawled_policies_data.csv")
        if not os.path.exists(self.policies_df_path):
            policies_df = pd.DataFrame(columns=[
                'url', 'file_path', 'include', 'found_links_count', 
                'definite_links', 'probable_links'
            ])
            policies_df.to_csv(self.policies_df_path, index=False)
        
        # Initialize the driver
        self._init_driver()
    
    def _init_driver(self):
        """Initialize the Selenium WebDriver."""
        self.logger.info("Initializing Chrome WebDriver...")
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-notifications")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing WebDriver: {str(e)}")
            raise
    
    def signal_handler(self, sig, frame):
        """Handle termination signals to save state before exiting."""
        self.logger.info("Received termination signal. Saving state and shutting down gracefully...")
        self.stopping = True
        self.save_state()
        
        if self.driver:
            self.logger.info("Closing browser...")
            self.driver.quit()
        
        self.logger.info("Crawler stopped gracefully. Run again with --resume to continue from this point.")
        exit(0)
    
    def save_state(self):
        """Save the current crawler state."""
        if self.current_url:
            self.state_manager.save_state(
                self.visited_urls, 
                self.priority_queue, 
                self.current_url, 
                self.current_depth
            )
    
    def load_state(self):
        """Load previous crawler state if it exists."""
        if not self.resume:
            self.logger.info("Resume mode disabled, starting fresh crawl")
            self.state_manager.clear_state()
            return False
            
        state = self.state_manager.load_state()
        if not state:
            self.logger.info("No previous state to resume from")
            return False
            
        # Restore state
        self.visited_urls = state["visited_urls"]
        self.priority_queue = state["priority_queue"]
        self.current_url = state["current_url"]
        self.current_depth = state["current_depth"]
        
        self.logger.info(f"Resumed crawler state with {len(self.visited_urls)} visited URLs and {len(self.priority_queue)} URLs in queue")
        return True
    
    def start(self, initial_url: str = None):
        """
        Start the crawling process.
        
        Args:
            initial_url: URL to start crawling from
        """
        try:
            # If no initial URL is provided, use the main URL from the config
            if initial_url is None:
                initial_url = self.config.MAIN_URL

            # Navigate to the initial URL
            self.logger.info(f"Opening {initial_url}...")
            self.driver.get(initial_url)
            
            # Wait for manual login
            self.logger.info("Please log in manually. The browser will wait until you're done.")
            self.logger.info("Once you've logged in and can see the policies page, press Enter to continue...")
            input()
            
            # Check if we should resume or start fresh
            resumed = self.load_state()
            
            if not resumed:
                # Add initial URL to priority queue with high priority
                heapq.heappush(self.priority_queue, (-100, initial_url, 0))  # Negative priority so highest is first
                self.logger.info(f"Starting new crawl from {initial_url}")
            else:
                self.logger.info(f"Resuming crawl from {self.current_url}")
                
                # Make sure we're on the right page before continuing
                if self.current_url:
                    self.logger.info(f"Navigating to last processed URL: {self.current_url}")
                    self.driver.get(self.current_url)
                    time.sleep(2)  # Give the page a moment to load
            
            # Start automated crawling
            self.logger.info(f"Starting automated crawling with max depth {self.max_depth}...")
            self.crawl_automatically()
            
        except Exception as e:
            self.logger.error(f"Error during crawling: {str(e)}")
            # Save state on error
            self.save_state()
        
        finally:
            # Save final state
            if not self.stopping:
                self.save_state()
                
            # Close the browser
            if self.driver:
                self.logger.info("Closing the browser...")
                self.driver.quit()
    
    def crawl_automatically(self):
        """Run the automated crawling process using the priority queue."""
        pages_processed = 0
        save_interval = 10  # Save state every 10 pages
        
        # Continue until priority queue is empty
        while self.priority_queue and not self.stopping:
            try:
                # Get the highest priority URL
                neg_priority, url, depth = heapq.heappop(self.priority_queue)
                priority = -neg_priority  # Convert back to positive priority
                
                # Update current URL and depth for state saving
                self.current_url = url
                self.current_depth = depth
                
                # Skip if already visited or max depth reached
                if url in self.visited_urls:
                    self.logger.info(f"Skipping already visited URL: {url}")
                    continue
                    
                if depth > self.max_depth:
                    self.logger.info(f"Skipping {url} - max depth reached")
                    continue
                
                # Process the URL
                self.logger.info(f"\n{'='*80}\nProcessing [{pages_processed+1}] (Priority: {priority:.1f}, Depth: {depth}): {url}")
                self.process_url(url, depth)
                pages_processed += 1
                
                # Save state periodically
                if pages_processed % save_interval == 0:
                    self.save_state()
                    self.logger.info(f"Progress: {pages_processed} pages processed, {len(self.priority_queue)} URLs in queue")
                    
            except Exception as e:
                self.logger.error(f"Error processing URL {self.current_url}: {str(e)}")
                # Continue with next URL
                continue
                
        # Final state save
        self.save_state()
        
        if not self.stopping:
            if self.priority_queue:
                self.logger.info(f"Crawler stopped with {len(self.priority_queue)} URLs still in queue")
            else:
                self.logger.info("Crawler completed - all URLs processed")
                # Clear state as we're done
                self.state_manager.clear_state()
    
    def is_allowed_url(self, url: str) -> bool:
        """
        Check if a URL is allowed for crawling.
        
        Args:
            url: URL to check
            
        Returns:
            True if the URL is allowed, False otherwise
        """
        # Skip empty URLs and anchors
        if not url or url.startswith('#') or url.startswith('javascript:'):
            self.logger.debug(f"Skipping empty or javascript URL: {url}")
            return False
        
        # Skip already visited URLs
        if url in self.visited_urls:
            self.logger.debug(f"Skipping already visited URL: {url}")
            return False
        
        # Check domain restrictions
        parsed_url = urllib.parse.urlparse(url)
        allowed = any(domain in parsed_url.netloc for domain in self.config.ALLOWED_DOMAINS)
        if not allowed:
            self.logger.debug(f"Skipping URL from non-allowed domain: {url}")
        return allowed
    
    def is_document_url(self, url: str) -> bool:
        """
        Check if a URL points to a document.
        
        Args:
            url: URL to check
            
        Returns:
            True if the URL points to a document, False otherwise
        """
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path.lower()
        
        # Check for known document extensions
        extension = os.path.splitext(path)[1]
        if extension in self.config.DOCUMENT_EXTENSIONS:
            self.logger.info(f"Detected document URL by extension: {url}")
            return True
        
        # Check for document repository patterns
        doc_patterns = [
            '/documents/',     # Common document path
            'files-profile',   # Yale-specific document repository
            '/attachments/',   # Common attachment path
            '/download/',      # Download endpoints
            '/dl/',            # Shortened download endpoints
            '/docs/',          # Document directories
            '/files/',         # File directories
            '/content/dam/'    # Content DAM systems
        ]
        
        for pattern in doc_patterns:
            if pattern in url.lower():
                self.logger.info(f"Detected document URL by pattern '{pattern}': {url}")
                return True
        
        # Additional checks for Yale medicine document URLs
        if 'files-profile.medicine.yale.edu/documents/' in url:
            self.logger.info(f"Detected Yale Medicine document repository URL: {url}")
            return True
        
        # Add specific check for the URL pattern you mentioned
        if re.match(r'https://files-profile\.medicine\.yale\.edu/documents/[a-f0-9-]+', url):
            self.logger.info(f"Detected Yale Medicine document UUID URL: {url}")
            return True
            
        return False
    
    def calculate_priority(self, url: str, link_text: str = "") -> float:
        """
        Calculate priority score for a URL based on keywords and path structure.
        
        Args:
            url: URL to score
            link_text: Text of the link pointing to this URL
            
        Returns:
            Priority score (higher is more relevant)
        """
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path.lower()
        url_string = url.lower()
        
        # Start with base priority
        priority = 1.0
        
        # Check URL path for keywords
        for keyword in self.priority_keywords:
            if keyword in path:
                priority += 5.0
                
            # Give extra weight to keywords in filename
            if f"/{keyword}" in path or f"/{keyword}." in path:
                priority += 3.0
        
        # Check link text for keywords
        if link_text:
            link_text_lower = link_text.lower()
            for keyword in self.priority_keywords:
                if keyword in link_text_lower:
                    priority += 4.0
        
        # Prioritize shorter paths (closer to root)
        path_depth = path.count('/')
        priority -= path_depth * 0.5  # Reduce priority for deeper paths
        
        # Prioritize certain file types
        if path.endswith('.pdf'):
            priority += 10.0
        elif path.endswith('.doc') or path.endswith('.docx'):
            priority += 8.0
            
        # Prioritize paths with "policy" or "guideline" in them
        if 'policy' in path or 'policies' in path:
            priority += 15.0
        if 'guideline' in path or 'guidelines' in path:
            priority += 15.0
        if 'procedure' in path or 'procedures' in path:
            priority += 12.0
        if 'protocol' in path or 'protocols' in path:
            priority += 12.0
            
        # Deprioritize certain paths
        if 'search' in path or 'login' in path or 'contact' in path:
            priority -= 10.0
            
        self.logger.debug(f"Priority for {url} (link text: '{link_text}'): {priority:.1f}")
        return priority
    
    def extract_links(self, html_content: str, base_url: str) -> List[Tuple[str, str]]:
        """
        Extract links and their text from HTML content.
        
        Args:
            html_content: HTML content to extract links from
            base_url: Base URL for resolving relative links
            
        Returns:
            List of tuples (url, link_text)
        """
        # Find all <a href> links with their text
        href_links = re.findall(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>([^<]*)</a>', html_content)
        
        # Process and normalize links
        processed_links = []
        for link, text in href_links:
            # Skip empty links and anchors
            if not link or link.startswith('#'):
                continue
            
            # Convert relative URLs to absolute
            if not link.startswith('http'):
                link = urllib.parse.urljoin(base_url, link)
            
            # Check if the link is allowed
            if self.is_allowed_url(link):
                processed_links.append((link, text.strip()))
        
        self.logger.info(f"Extracted {len(processed_links)} valid links from {base_url}")
        return processed_links
    
    def process_url(self, url: str, depth: int):
        """
        Process a URL, extract its content and follow links based on LLM analysis.
        
        Args:
            url: URL to process
            depth: Current crawling depth
        """
        # Mark as visited
        self.visited_urls.add(url)
        self.logger.info(f"Processing URL: {url} at depth {depth}")
        
        # Special handling for root URL to ensure we don't get stuck
        is_root_url = (depth == 0)
        
        # Process based on URL type
        if self.is_document_url(url):
            # Process document
            self.logger.info(f"Processing as document: {url}")
            markdown_content = self.process_document(url)
            
            # No need to extract links from documents
            if not markdown_content:
                self.logger.warning(f"Failed to extract content from document {url}")
                return
            
            # Analyze and save policy content
            policy_result = analyze_content_for_policies(markdown_content, url)
            self.save_policy_content(url, markdown_content, depth, policy_result)
        else:
            # Process webpage
            self.logger.info(f"Processing as webpage: {url}")
            markdown_content, all_links = self.process_webpage(url)
            
            if not markdown_content:
                self.logger.warning(f"Failed to extract content from webpage {url}")
                return
            
            # Pass the links to the LLM for analysis
            policy_result = analyze_content_for_policies(markdown_content, url, all_links)
            
            # Save all content regardless of policy detection
            self.save_policy_content(url, markdown_content, depth, policy_result)
            
            # Process links if not at max depth
            if depth < self.max_depth:
                links_to_follow = []
                
                # For the root URL: If no policy links are found, follow all links up to a limit
                if is_root_url and not policy_result.get('definite_links') and not policy_result.get('probable_links'):
                    self.logger.warning("No policy links found on root page. Following all links as a fallback.")
                    # Follow all links from the root page (limited to first 20 to avoid overwhelming)
                    for link_url, link_text in all_links[:20]:
                        links_to_follow.append((link_url, link_text))
                        self.logger.info(f"Adding fallback link from root: {link_url}")
                else:
                    # Normal policy link following
                    # Add definite links
                    for link_url in policy_result.get('definite_links', []):
                        links_to_follow.append((link_url, "Definite policy link"))
                        self.logger.info(f"Adding definite policy link: {link_url}")
                    
                    # Add probable links if configured to do so
                    if not self.config.FOLLOW_DEFINITE_LINKS_ONLY:
                        for link_url in policy_result.get('probable_links', []):
                            links_to_follow.append((link_url, "Probable policy link"))
                            self.logger.info(f"Adding probable policy link: {link_url}")
                
                # Add the links to the queue
                self.add_links_to_queue(links_to_follow, depth + 1)
                
                # Log summary of links
                self.logger.info(f"Added {len(links_to_follow)} links to priority queue. Queue size: {len(self.priority_queue)}")
    
    def add_links_to_queue(self, links: List[Tuple[str, str]], depth: int):
        """
        Calculate priorities and add links to the priority queue.
        
        Args:
            links: List of (url, link_text) tuples
            depth: Depth for these links
        """
        added_count = 0
        for url, link_text in links:
            if url not in self.visited_urls:
                priority = self.calculate_priority(url, link_text)
                heapq.heappush(self.priority_queue, (-priority, url, depth))  # Negate for max heap
                added_count += 1
                self.logger.info(f"Added to queue: {url} (Priority: {priority:.1f}, Depth: {depth})")
        
        self.logger.info(f"Added {added_count} links to priority queue. Queue size: {len(self.priority_queue)}")
    
    def process_webpage(self, url: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Process a webpage, extract its content and links.
        
        Args:
            url: URL of the webpage
            
        Returns:
            Tuple of (markdown_content, extracted_links)
        """
        try:
            # Navigate to the URL
            self.logger.info(f"Navigating to webpage: {url}")
            self.driver.get(url)
            
            # Wait for the main content to load
            WebDriverWait(self.driver, self.config.REQUEST_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get the page HTML
            html_content = self.driver.page_source
            self.logger.info(f"Retrieved HTML content from {url} (length: {len(html_content)} characters)")
            
            # Convert HTML to markdown
            markdown_content = html_to_markdown(html_content)
            self.logger.info(f"Converted HTML to markdown (length: {len(markdown_content)} characters)")
            
            # Extract links
            links = self.extract_links(html_content, url)
            self.logger.info(f"Extracted {len(links)} links from {url}")
            
            return markdown_content, links
            
        except Exception as e:
            self.logger.error(f"Error processing webpage {url}: {str(e)}")
            return "", []
    
    def process_document(self, url: str) -> str:
        """
        Process a document URL, download and convert to markdown.
        
        Args:
            url: URL of the document
            
        Returns:
            Markdown content of the document
        """
        try:
            # Check if it might be a PDF file
            parsed_url = urllib.parse.urlparse(url)
            file_ext = os.path.splitext(parsed_url.path.lower())[1]
            
            # For URLs matching Yale document repository pattern
            if 'files-profile.medicine.yale.edu/documents/' in url:
                # Assume this is a PDF for Yale document repository URLs without extension
                self.logger.info(f"Processing Yale document repository URL as PDF: {url}")
                doc_output_dir = os.path.join(self.config.DOCUMENT_DIR, f"doc_{hash(url) % 10000}")
                os.makedirs(doc_output_dir, exist_ok=True)
                
                self.logger.info(f"Processing with Mistral OCR: {url}")
                markdown_path = pdf_to_markdown(url, doc_output_dir)
                
                if markdown_path and os.path.exists(markdown_path):
                    with open(markdown_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.logger.info(f"Successfully extracted content using OCR: {url} (length: {len(content)} characters)")
                        return content
                else:
                    self.logger.error(f"Failed to convert document from {url}")
                    return f"# Failed to Extract Content\n\nURL: {url}\n\nCould not extract content from this document."
            
            # Process based on file extension
            elif file_ext == '.pdf' or file_ext == '':  # Handle both PDF and extensionless URLs
                # Try Mistral OCR for PDFs and extensionless URLs that might be PDFs
                doc_output_dir = os.path.join(self.config.DOCUMENT_DIR, f"doc_{hash(url) % 10000}")
                os.makedirs(doc_output_dir, exist_ok=True)
                
                self.logger.info(f"Processing with Mistral OCR: {url}")
                markdown_path = pdf_to_markdown(url, doc_output_dir)
                
                if markdown_path and os.path.exists(markdown_path):
                    with open(markdown_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.logger.info(f"Successfully extracted content using OCR: {url} (length: {len(content)} characters)")
                        return content
                else:
                    self.logger.error(f"Failed to convert document from {url}")
                    return ""
            else:
                # For other document types, use the standard approach
                file_path = download_document(url, self.config.DOCUMENT_DIR)
                
                if not file_path:
                    self.logger.error(f"Failed to download document from {url}")
                    return ""
                
                # Convert document to markdown
                markdown_content = convert_to_markdown(file_path, url)
                self.logger.info(f"Converted document to markdown: {url} (length: {len(markdown_content)} characters)")
                return markdown_content
                
        except Exception as e:
            self.logger.error(f"Error processing document {url}: {str(e)}")
            return f"# Error Processing Document\n\nURL: {url}\n\nError: {str(e)}"
    
    def save_policy_content(self, url: str, content: str, depth: int, policy_result: dict = None) -> Optional[str]:
        """
        Analyze content for policies and save relevant content.
        
        Args:
            url: Source URL of the content
            content: Content to analyze
            depth: Current crawling depth
            policy_result: Optional pre-analyzed policy result from LLM
            
        Returns:
            Path to the saved policy file or None if no policy found
        """
        # If policy_result not provided, analyze content
        if policy_result is None:
            self.logger.info(f"No policy result provided, analyzing content for {url}")
            policy_result = analyze_content_for_policies(content, url)
        
        # Save all content as markdown regardless of policy detection
        parsed_url = urllib.parse.urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # Create a filename for the full content
        full_filename = f"full_depth_{depth}_{'_'.join(path_parts[-2:]) if len(path_parts) > 1 else path_parts[0]}.md"
        if len(full_filename) > 100:
            full_filename = f"full_depth_{depth}_{hash(url) % 10000}.md"
        if not full_filename.endswith('.md'):
            full_filename += '.md'
        
        # Save the full content
        full_file_path = os.path.join(self.config.MARKDOWN_DIR, full_filename)
        with open(full_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Content from {parsed_url.netloc}{parsed_url.path}\n\n")
            f.write(f"Source URL: {url}\n")
            f.write(f"Crawl Depth: {depth}\n\n")
            f.write("---\n\n")
            f.write(content)
        
        self.logger.info(f"Full content saved to {full_file_path}")
        
        # Extract policy details
        include_policy = policy_result.get('include', False)
        definite_links = policy_result.get('definite_links', [])
        probable_links = policy_result.get('probable_links', [])
        
        # If no policy content detected, record data and return None
        if not include_policy:
            self.logger.info(f"No policy content found in {url}")
            self.record_policy_data(url, full_file_path, include_policy, [], [], 0)
            return None
        
        # Create a filename for the policy content
        policy_filename = f"policy_depth_{depth}_{'_'.join(path_parts[-2:]) if len(path_parts) > 1 else path_parts[0]}.md"
        if len(policy_filename) > 100:
            policy_filename = f"policy_depth_{depth}_{hash(url) % 10000}.md"
        if not policy_filename.endswith('.md'):
            policy_filename += '.md'
        
        # Save the policy content
        policy_file_path = os.path.join(self.config.MARKDOWN_DIR, policy_filename)
        with open(policy_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Policy Content from {parsed_url.netloc}{parsed_url.path}\n\n")
            f.write(f"Source URL: {url}\n")
            f.write(f"Crawl Depth: {depth}\n\n")
            
            # Add information about links identified by LLM
            if definite_links or probable_links:
                f.write("## Links Identified by LLM\n\n")
                
                if definite_links:
                    f.write("### Definite Policy Links\n\n")
                    for link in definite_links:
                        f.write(f"- [{link}]({link})\n")
                    f.write("\n")
                
                if probable_links:
                    f.write("### Probable Policy Links\n\n")
                    for link in probable_links:
                        f.write(f"- [{link}]({link})\n")
                    f.write("\n")
                
                f.write("---\n\n")
            
            f.write(policy_result['content'])
        
        self.logger.info(f"Policy content saved to {policy_file_path}")
        
        # Record policy data
        self.record_policy_data(url, policy_file_path, include_policy, definite_links, probable_links, 
                              len(definite_links) + len(probable_links))
        
        return policy_file_path
    
    def record_policy_data(self, url: str, file_path: str, include: bool, definite_links: List[str], 
                        probable_links: List[str], found_links_count: int):
        """
        Record policy data in the tracking DataFrame.
        
        Args:
            url: Source URL of the policy
            file_path: Path to the saved policy file
            include: Whether the content is identified as policy
            definite_links: List of definite links
            probable_links: List of probable links
            found_links_count: Total count of links found
        """
        try:
            # Load existing DataFrame
            if os.path.exists(self.policies_df_path):
                df = pd.read_csv(self.policies_df_path)
            else:
                df = pd.DataFrame(columns=[
                    'url', 'file_path', 'include', 'found_links_count', 
                    'definite_links', 'probable_links'
                ])
            
            # Add new data
            new_row = {
                'url': url,
                'file_path': file_path,
                'include': include,
                'found_links_count': found_links_count,
                'definite_links': json.dumps(definite_links),
                'probable_links': json.dumps(probable_links)
            }
            
            # Check if the URL already exists in the dataframe
            if url in df['url'].values:
                # Update existing entry
                df.loc[df['url'] == url] = pd.Series(new_row)
                self.logger.info(f"Updated existing entry in policies data for {url}")
            else:
                # Add new entry
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                self.logger.info(f"Added new entry to policies data for {url}")
            
            # Save DataFrame
            df.to_csv(self.policies_df_path, index=False)
            self.logger.info(f"Policy data recorded in {self.policies_df_path}")
            
        except Exception as e:
            self.logger.error(f"Error recording policy data: {str(e)}")