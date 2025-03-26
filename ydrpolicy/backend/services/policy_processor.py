# ydrpolicy/backend/services/policy_processor.py
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ydrpolicy.backend.database.models import Policy, PolicyChunk
from ydrpolicy.backend.database.repository.policies import PolicyRepository
from ydrpolicy.backend.services.chunking import chunk_text
from ydrpolicy.backend.services.embeddings import embed_text
from ydrpolicy.backend.config import config
from ydrpolicy.backend.logger import logger

# Import your existing crawling and scraping modules
from ydrpolicy.data_collection.crawl.crawler import YaleCrawler
from ydrpolicy.data_collection.scrape.scraper import PolicyScraper


class PolicyProcessorService:
    def __init__(self, policy_repository: PolicyRepository, session: AsyncSession):
        self.policy_repository = policy_repository
        self.session = session
        
    async def process_url(self, url: str, admin_id: Optional[int] = None, follow_links: bool = False, depth: int = 1) -> Policy:
        """
        Process a single policy URL.
        
        Args:
            url: The URL of the policy to process
            admin_id: Optional ID of admin performing the operation
            follow_links: Whether to follow links from the provided URL
            depth: How many levels deep to follow links
            
        Returns:
            The created or updated Policy object
        """
        # 1. Check if policy already exists
        existing = await self.policy_repository.get_by_url(url)
        if existing:
            logger.info(f"Policy with URL {url} already exists, updating...")
            return await self.update_policy(existing.id, url, admin_id)
            
        # 2. Crawl the URL (call your crawling script)
        crawl_result = await self._crawl_url(url, follow_links, depth)
        
        # 3. Scrape content (call your scraping script)
        policy_data = await self._scrape_content(crawl_result)
        
        # 4. Create policy record
        policy = Policy(
            title=policy_data['title'],
            description=policy_data.get('description', ''),
            url=url,
            content=policy_data['content'],
            metadata=policy_data.get('metadata', {})
        )
        created_policy = await self.policy_repository.create(policy)
        
        # 5. Process chunks and embeddings
        await self._process_chunks(created_policy)
        
        # 6. Log the addition
        await self.policy_repository.log_policy_update(
            policy_id=created_policy.id,
            admin_id=admin_id,
            action="create",
            details={"source": url}
        )
        
        return created_policy
        
    async def update_policy(self, policy_id: int, url: str, admin_id: Optional[int] = None) -> Policy:
        """
        Update an existing policy.
        
        Args:
            policy_id: ID of the policy to update
            url: URL to fetch updated content from
            admin_id: Optional ID of admin performing the update
            
        Returns:
            The updated Policy object
        """
        # 1. Get existing policy
        existing_policy = await self.policy_repository.get_by_id(policy_id)
        if not existing_policy:
            raise ValueError(f"Policy with ID {policy_id} not found")
            
        # 2. Crawl and scrape updated content
        crawl_result = await self._crawl_url(url, follow_links=False, depth=0)
        policy_data = await self._scrape_content(crawl_result)
        
        # 3. Check if content has actually changed
        if existing_policy.content == policy_data['content']:
            logger.info(f"Policy content unchanged for {url}")
            return existing_policy
            
        # 4. Track changes
        changes = {
            "content_changed": existing_policy.content != policy_data['content'],
            "title_changed": existing_policy.title != policy_data['title'],
            "old_title": existing_policy.title,
            "new_title": policy_data['title']
        }
        
        # 5. Update policy
        updated_policy = await self.policy_repository.update(
            policy_id,
            {
                "title": policy_data['title'],
                "description": policy_data.get('description', ''),
                "content": policy_data['content'],
                "metadata": {**existing_policy.metadata, **policy_data.get('metadata', {})},
                "updated_at": datetime.utcnow()
            }
        )
        
        # 6. Delete old chunks
        old_chunks = await self.policy_repository.get_chunks_by_policy_id(policy_id)
        for chunk in old_chunks:
            await self.session.delete(chunk)
        await self.session.flush()
        
        # 7. Create new chunks and embeddings
        await self._process_chunks(updated_policy)
        
        # 8. Log the update
        await self.policy_repository.log_policy_update(
            policy_id=policy_id,
            admin_id=admin_id,
            action="update",
            details=changes
        )
        
        return updated_policy
    
    async def process_multiple_urls(self, urls: List[str], admin_id: Optional[int] = None, follow_links: bool = False, depth: int = 1) -> List[Policy]:
        """
        Process multiple policy URLs.
        
        Args:
            urls: List of URLs to process
            admin_id: Optional ID of admin performing the operation
            follow_links: Whether to follow links from provided URLs
            depth: How many levels deep to follow links
            
        Returns:
            List of created or updated Policy objects
        """
        results = []
        for url in urls:
            try:
                policy = await self.process_url(url, admin_id, follow_links, depth)
                results.append(policy)
            except Exception as e:
                logger.error(f"Error processing URL {url}: {str(e)}")
                # Continue with other URLs even if one fails
                continue
        return results
    
    # Helper methods to integrate with your existing crawling and scraping code
    async def _crawl_url(self, url: str, follow_links: bool, depth: int) -> Dict[str, Any]:
        """
        Crawl a URL using the existing crawler.
        
        This method would integrate with your YaleCrawler from the data_collection module.
        The implementation depends on how your crawler is structured.
        """
        # Example integration - adjust based on your actual crawler implementation
        crawler = YaleCrawler(
            start_url=url,
            follow_links=follow_links,
            max_depth=depth
        )
        
        # Run the crawler (might need to be adapted based on your implementation)
        result = await crawler.crawl()
        return result
        
    async def _scrape_content(self, crawl_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract policy content from crawl results.
        
        This method would integrate with your PolicyScraper from the data_collection module.
        The implementation depends on how your scraper is structured.
        """
        # Example integration - adjust based on your actual scraper implementation
        scraper = PolicyScraper(crawl_result)
        
        # Run the scraper (might need to be adapted based on your implementation)
        policy_data = await scraper.extract_policy()
        return {
            'title': policy_data.get('title', 'Untitled Policy'),
            'description': policy_data.get('description', ''),
            'content': policy_data.get('content', ''),
            'metadata': {
                'department': policy_data.get('department', 'Radiology'),
                'category': policy_data.get('category', 'General'),
                'extracted_date': datetime.utcnow().isoformat(),
            }
        }
        
    async def _process_chunks(self, policy: Policy) -> None:
        """
        Process a policy into chunks with embeddings.
        
        Args:
            policy: The Policy object to chunk and embed
        """
        logger.info(f"Processing policy '{policy.title}' into chunks")
        
        # Chunk the content
        chunks = chunk_text(
            policy.content, 
            chunk_size=config.RAG.CHUNK_SIZE,
            chunk_overlap=config.RAG.CHUNK_OVERLAP
        )
        
        logger.info(f"Created {len(chunks)} chunks for policy {policy.id}")
        
        # Create embeddings and store chunks with rate limiting
        for i, chunk_content in enumerate(chunks):
            # Simple rate limiting to avoid OpenAI API rate limits
            if i > 0 and i % 20 == 0:
                logger.debug(f"Rate limiting: pausing for 1 second after {i} chunks")
                await asyncio.sleep(1)
                
            try:
                embedding = await embed_text(chunk_content)
                chunk = PolicyChunk(
                    policy_id=policy.id,
                    chunk_index=i,
                    content=chunk_content,
                    embedding=embedding
                )
                await self.policy_repository.create_chunk(chunk)
            except Exception as e:
                logger.error(f"Error processing chunk {i} for policy {policy.id}: {str(e)}")
                # Continue with other chunks even if one fails
                continue
                
        logger.info(f"Finished processing all chunks for policy {policy.id}")

# At the end of policy_processor.py
async def process_policies_cli(url=None, urls_file=None, admin_id=None, follow_links=False, depth=1, db_url=None):
    """CLI wrapper for policy processing."""
    if not url and not urls_file:
        logger.error("Either --url or --urls-file must be provided")
        return
        
    # Get database connection
    from ydrpolicy.backend.database.engine import get_async_engine, get_async_session
    from ydrpolicy.backend.database.repository.policies import PolicyRepository
    
    # Use provided DB URL or default from config
    if db_url:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        engine = create_async_engine(db_url)
        async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    else:
        from ydrpolicy.backend.database.engine import get_async_session, get_async_engine
        engine = get_async_engine()
        async_session_factory = get_async_session
    
    urls = []
    if url:
        urls.append(url)
        
    if urls_file:
        with open(urls_file, 'r') as f:
            file_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            urls.extend(file_urls)
    
    logger.info(f"Processing {len(urls)} URLs with follow_links={follow_links}, depth={depth}")
    
    async with async_session_factory() as session:
        policy_repo = PolicyRepository(session)
        processor = PolicyProcessorService(policy_repo, session)
        
        try:
            results = await processor.process_multiple_urls(urls, admin_id, follow_links, depth)
            logger.info(f"Successfully processed {len(results)} policies")
            
            # Print summary
            for policy in results:
                logger.info(f"Policy: {policy.title} (ID: {policy.id}) - URL: {policy.url}")
        except Exception as e:
            logger.error(f"Error processing policies: {str(e)}")
            raise