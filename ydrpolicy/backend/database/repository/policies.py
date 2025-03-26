from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select, func, text, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import or_, and_

from ydrpolicy.backend.database.models import Policy, PolicyChunk, PolicyUpdate
from ydrpolicy.backend.database.repository.base import BaseRepository
from ydrpolicy.backend.config import config
from ydrpolicy.backend.logger import logger


class PolicyRepository(BaseRepository[Policy]):
    """Repository for working with Policy models and related operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Policy)
    
    async def get_by_url(self, url: str) -> Optional[Policy]:
        """
        Get a policy by its URL.
        
        Args:
            url: URL of the policy
            
        Returns:
            Policy if found, None otherwise
        """
        stmt = select(Policy).where(Policy.url == url)
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def search_by_title(self, title_query: str) -> List[Policy]:
        """
        Search policies by title using partial matching.
        
        Args:
            title_query: Title search query
            
        Returns:
            List of policies matching the title query
        """
        stmt = select(Policy).where(Policy.title.ilike(f"%{title_query}%"))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def full_text_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform a full-text search on entire policies (not chunks).
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching policies with relevance scores
        """
        # Convert the query to a tsvector and search against the search_vector column
        search_query = ' & '.join(query.split())
        
        stmt = text("""
            SELECT 
                p.id,
                p.title,
                p.description,
                p.url,
                ts_rank(p.search_vector, to_tsquery('english', :query)) AS relevance
            FROM 
                policies p
            WHERE 
                p.search_vector @@ to_tsquery('english', :query)
            ORDER BY 
                relevance DESC
            LIMIT :limit
        """)
        
        result = await self.session.execute(
            stmt, 
            {"query": search_query, "limit": limit}
        )
        
        return [
            {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "url": row.url,
                "relevance": row.relevance
            }
            for row in result
        ]
        
    async def text_search_chunks(self, query: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Perform a text-based search on policy chunks using full-text search.
        
        This search method uses PostgreSQL's tsvector/tsquery for pure keyword matching
        without using any vector embeddings.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return (defaults to config.RAG.TOP_K)
            
        Returns:
            List of matching chunks with relevance scores
        """
        if limit is None:
            limit = config.RAG.TOP_K
            
        logger.info(f"Performing text-only search for query: '{query}' with limit={limit}")
        
        # Convert the query to a tsvector and search against the search_vector column
        search_query = ' & '.join(query.split())
        
        stmt = text("""
            SELECT 
                pc.id,
                pc.policy_id,
                pc.chunk_index,
                pc.content,
                p.title as policy_title,
                p.url as policy_url,
                ts_rank(pc.search_vector, to_tsquery('english', :query)) AS text_score
            FROM 
                policy_chunks pc
            JOIN 
                policies p ON pc.policy_id = p.id
            WHERE 
                pc.search_vector @@ to_tsquery('english', :query)
            ORDER BY 
                text_score DESC
            LIMIT :limit
        """)
        
        result = await self.session.execute(
            stmt, 
            {"query": search_query, "limit": limit}
        )
        
        return [
            {
                "id": row.id,
                "policy_id": row.policy_id,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "policy_title": row.policy_title,
                "policy_url": row.policy_url,
                "text_score": row.text_score
            }
            for row in result
        ]
    
    async def get_recent_policies(self, limit: int = 10) -> List[Policy]:
        """
        Get most recently added policies.
        
        Args:
            limit: Maximum number of policies to return
            
        Returns:
            List of policies ordered by creation date (newest first)
        """
        stmt = select(Policy).order_by(desc(Policy.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recently_updated_policies(self, limit: int = 10) -> List[Policy]:
        """
        Get most recently updated policies.
        
        Args:
            limit: Maximum number of policies to return
            
        Returns:
            List of policies ordered by update date (newest first)
        """
        stmt = select(Policy).order_by(desc(Policy.updated_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    # Policy chunk methods
    
    async def create_chunk(self, chunk: PolicyChunk) -> PolicyChunk:
        """
        Create a policy chunk with embedding.
        
        Args:
            chunk: PolicyChunk object to create
            
        Returns:
            Created PolicyChunk with ID populated
        """
        self.session.add(chunk)
        await self.session.flush()
        await self.session.refresh(chunk)
        return chunk
    
    async def get_chunks_by_policy_id(self, policy_id: int) -> List[PolicyChunk]:
        """
        Get all chunks for a specific policy.
        
        Args:
            policy_id: ID of the policy
            
        Returns:
            List of PolicyChunk objects
        """
        stmt = (
            select(PolicyChunk)
            .where(PolicyChunk.policy_id == policy_id)
            .order_by(PolicyChunk.chunk_index)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_chunks_by_embedding(
        self, 
        embedding: List[float], 
        limit: int = None,
        similarity_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Find chunks similar to the given embedding using cosine similarity.
        
        This is a pure vector-based semantic search that does not use text/keyword matching.
        It's useful for finding conceptually similar content even when keywords don't match.
        
        Args:
            embedding: Vector embedding to search for
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of chunks with similarity scores
        """
        if limit is None:
            limit = config.RAG.TOP_K
            
        if similarity_threshold is None:
            similarity_threshold = config.RAG.SIMILARITY_THRESHOLD
            
        logger.info(f"Performing vector-only search with limit={limit}, threshold={similarity_threshold}")
        
        # Use pgvector's cosine similarity search
        # This SQL uses the <=> operator for cosine distance (1 - similarity)
        # So we convert it to similarity by doing (1 - distance)
        stmt = text("""
            SELECT 
                pc.id,
                pc.policy_id,
                pc.chunk_index,
                pc.content,
                p.title as policy_title,
                p.url as policy_url,
                (1 - (pc.embedding <=> :embedding)) AS similarity
            FROM 
                policy_chunks pc
            JOIN 
                policies p ON pc.policy_id = p.id
            WHERE 
                (1 - (pc.embedding <=> :embedding)) >= :threshold
            ORDER BY 
                similarity DESC
            LIMIT :limit
        """)
        
        result = await self.session.execute(
            stmt, 
            {"embedding": embedding, "threshold": similarity_threshold, "limit": limit}
        )
        
        return [
            {
                "id": row.id,
                "policy_id": row.policy_id,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "policy_title": row.policy_title,
                "policy_url": row.policy_url,
                "similarity": row.similarity
            }
            for row in result
        ]
    
    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        vector_weight: float = None,
        limit: int = None,
        similarity_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search using both vector similarity and text search.
        
        This method combines semantic search (via vector embeddings) with keyword search
        (via PostgreSQL full-text search) for optimal results. The vector_weight parameter
        controls the balance between these approaches.
        
        Args:
            query: Text query for keyword search
            embedding: Vector embedding for similarity search
            vector_weight: Weight for vector search (0-1), with (1-vector_weight) used for keyword search
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score threshold (0-1)
            
        Returns:
            List of chunks with combined scores
        """
        if vector_weight is None:
            vector_weight = config.RAG.VECTOR_WEIGHT
            
        if limit is None:
            limit = config.RAG.TOP_K
            
        if similarity_threshold is None:
            similarity_threshold = config.RAG.SIMILARITY_THRESHOLD
            
        logger.info(f"Performing hybrid search with query='{query}', weight={vector_weight}, limit={limit}")
        
        # Prepare the text search query
        text_query = ' & '.join(query.split())
        
        # Combine vector and text search with weighted scoring
        stmt = text("""
            WITH vector_results AS (
                SELECT 
                    pc.id,
                    pc.policy_id,
                    pc.chunk_index,
                    pc.content,
                    p.title as policy_title,
                    p.url as policy_url,
                    (1 - (pc.embedding <=> :embedding)) AS vector_score,
                    ts_rank(pc.search_vector, to_tsquery('english', :query)) AS text_score
                FROM 
                    policy_chunks pc
                JOIN 
                    policies p ON pc.policy_id = p.id
                WHERE 
                    (1 - (pc.embedding <=> :embedding)) >= :threshold
                    OR pc.search_vector @@ to_tsquery('english', :query)
            )
            SELECT 
                id,
                policy_id,
                chunk_index,
                content,
                policy_title,
                policy_url,
                vector_score,
                text_score,
                (:vector_weight * vector_score + (1 - :vector_weight) * text_score) AS combined_score
            FROM 
                vector_results
            ORDER BY 
                combined_score DESC
            LIMIT :limit
        """)
        
        result = await self.session.execute(
            stmt, 
            {
                "embedding": embedding, 
                "query": text_query, 
                "threshold": similarity_threshold, 
                "vector_weight": vector_weight,
                "limit": limit
            }
        )
    
        return [
            {
                "id": row.id,
                "policy_id": row.policy_id,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "policy_title": row.policy_title,
                "policy_url": row.policy_url,
                "vector_score": row.vector_score,
                "text_score": row.text_score,
                "combined_score": row.combined_score
            }
            for row in result
        ]
    
    async def get_policies_from_chunks(self, chunk_results: List[Dict[str, Any]]) -> List[Policy]:
        """
        Retrieve complete policies for chunks returned from a search.
        
        Args:
            chunk_results: List of chunk results from a search method
            
        Returns:
            List of complete Policy objects
        """
        # Extract unique policy IDs
        policy_ids = set(result["policy_id"] for result in chunk_results)
        
        if not policy_ids:
            return []
            
        logger.info(f"Retrieving {len(policy_ids)} complete policies from chunk results")
        
        # Fetch all policies in a single query for efficiency
        stmt = select(Policy).where(Policy.id.in_(policy_ids))
        result = await self.session.execute(stmt)
        
        return list(result.scalars().all())
    
    async def log_policy_update(
        self,
        policy_id: int,
        admin_id: Optional[int],
        action: str,
        details: Optional[Dict] = None
    ) -> PolicyUpdate:
        """
        Log a policy update operation.
        
        Args:
            policy_id: ID of the policy being modified
            admin_id: ID of the admin performing the operation (optional)
            action: Type of action ('create', 'update', 'delete')
            details: Additional details about the update (optional)
            
        Returns:
            Created PolicyUpdate record
        """
        policy_update = PolicyUpdate(
            policy_id=policy_id,
            admin_id=admin_id,
            action=action,
            details=details or {},
            created_at=datetime.utcnow()
        )
        
        self.session.add(policy_update)
        await self.session.flush()
        await self.session.refresh(policy_update)
        
        logger.info(f"Logged policy update: policy_id={policy_id}, action={action}")
        return policy_update
    
    async def get_policy_update_history(self, policy_id: int) -> List[PolicyUpdate]:
        """
        Get update history for a specific policy.
        
        Args:
            policy_id: ID of the policy
            
        Returns:
            List of PolicyUpdate records for the policy
        """
        stmt = (
            select(PolicyUpdate)
            .where(PolicyUpdate.policy_id == policy_id)
            .order_by(desc(PolicyUpdate.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())