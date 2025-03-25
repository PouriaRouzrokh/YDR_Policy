from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import or_, and_

from ydrpolicy.backend.database.models import Policy, PolicyChunk
from ydrpolicy.backend.database.repository.base import BaseRepository
from ydrpolicy.backend.config import config

class PolicyRepository(BaseRepository[Policy]):
    """Repository for working with Policy models and related operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Policy)
    
    async def filter_by_department(self, department: str) -> List[Policy]:
        """
        Filter policies by department.
        
        Args:
            department: Department name to filter by
            
        Returns:
            List of policies belonging to the specified department
        """
        stmt = select(Policy).where(Policy.department == department)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def filter_by_category(self, category: str) -> List[Policy]:
        """
        Filter policies by category.
        
        Args:
            category: Category name to filter by
            
        Returns:
            List of policies belonging to the specified category
        """
        stmt = select(Policy).where(Policy.category == category)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def filter_by_tags(self, tags: List[str]) -> List[Policy]:
        """
        Filter policies by tags.
        
        Args:
            tags: List of tags to filter by
            
        Returns:
            List of policies containing any of the specified tags
        """
        # Use PostgreSQL array overlap
        stmt = select(Policy).where(Policy.tags.overlap(tags))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def full_text_search(self, query: str) -> List[Policy]:
        """
        Perform a full-text search on policies.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching policies
        """
        # Convert the query to a tsvector and search against the search_vector column
        search_query = func.to_tsquery('english', ' & '.join(query.split()))
        stmt = (
            select(Policy)
            .where(Policy.search_vector.op('@@')(search_query))
            .order_by(func.ts_rank(Policy.search_vector, search_query).desc())
        )
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
    
    async def get_chunks_by_policy_id(self, policy_id: UUID) -> List[PolicyChunk]:
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
        limit: int = config.RAG.TOP_K,
        similarity_threshold: float = config.RAG.SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Find chunks similar to the given embedding using cosine similarity.
        
        Args:
            embedding: Vector embedding to search for
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of chunks with similarity scores
        """
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
                p.department,
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
                "department": row.department,
                "similarity": row.similarity
            }
            for row in result
        ]
    
    async def hybrid_search(
        self,
        query: str,
        embedding: Optional[List[float]] = None,
        vector_weight: float = config.RAG.VECTOR_WEIGHT,
        limit: int = config.RAG.TOP_K,
        similarity_threshold: float = config.RAG.SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search using both vector similarity and text search.
        
        Args:
            query: Text query for keyword search
            embedding: Vector embedding for similarity search (if None, only keyword search is used)
            vector_weight: Weight for vector search (0-1), with (1-vector_weight) used for keyword search
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score threshold (0-1)
            
        Returns:
            List of chunks with combined scores
        """
        # If no embedding provided, fall back to text search only
        if embedding is None:
            # Convert the query to a tsquery for text search
            search_query = func.to_tsquery('english', ' & '.join(query.split()))
            stmt = text("""
                SELECT 
                    pc.id,
                    pc.policy_id,
                    pc.chunk_index,
                    pc.content,
                    p.title as policy_title,
                    p.department,
                    ts_rank(pc.search_vector, to_tsquery('english', :query)) AS text_score,
                    ts_rank(pc.search_vector, to_tsquery('english', :query)) AS combined_score
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
                {"query": ' & '.join(query.split()), "limit": limit}
            )
        else:
            # Combine vector and text search with weighted scoring
            stmt = text("""
                WITH vector_results AS (
                    SELECT 
                        pc.id,
                        pc.policy_id,
                        pc.chunk_index,
                        pc.content,
                        p.title as policy_title,
                        p.department,
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
                    department,
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
                    "query": ' & '.join(query.split()), 
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
                "department": row.department,
                "vector_score": getattr(row, "vector_score", 0),
                "text_score": getattr(row, "text_score", 0),
                "combined_score": row.combined_score
            }
            for row in result
        ]