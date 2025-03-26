"""
Tests for pgvector functionality and vector similarity calculations.
"""
import pytest
import numpy as np
from sqlalchemy import text
import math

from ydrpolicy.backend.logger import logger
from ydrpolicy.backend.database.models import PolicyChunk, Policy


@pytest.mark.asyncio
async def test_pgvector_extension_loading(db_session):
    """Test that the pgvector extension is properly loaded."""
    # Verify pgvector extension is installed
    result = await db_session.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
    assert result.scalar() is not None, "pgvector extension not installed"
    
    # Verify we can create a vector
    result = await db_session.execute(text("SELECT ARRAY[1,2,3]::vector"))
    assert result.scalar() is not None, "Cannot create vector type"


@pytest.mark.asyncio
async def test_pgvector_similarity_calculation(db_session):
    """Test that pgvector calculates cosine similarity correctly."""
    # Create pairs of vectors with known similarities
    test_cases = [
        # Identical vectors (similarity = 1.0)
        ([1.0, 0.0, 0.0], [1.0, 0.0, 0.0], 1.0),
        
        # Perpendicular vectors (similarity = 0.0)
        ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], 0.0),
        
        # Opposite vectors (similarity = -1.0)
        ([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], -1.0),
        
        # 45-degree angle (similarity = 0.7071)
        ([1.0, 0.0, 0.0], [1.0, 1.0, 0.0], 0.7071),
        
        # Random unit vectors
        (
            [0.5773, 0.5773, 0.5773],  # Normalized [1,1,1]
            [0.8165, 0.4082, 0.4082],  # Normalized [2,1,1]
            0.9428  # Expected similarity
        )
    ]
    
    # Test each pair using pgvector's cosine similarity
    for vec1, vec2, expected_similarity in test_cases:
        # Convert arrays to PostgreSQL vector syntax
        vec1_str = str(vec1).replace('[', '{').replace(']', '}')
        vec2_str = str(vec2).replace('[', '{').replace(']', '}')
        
        # Calculate cosine similarity using pgvector
        # Note: <=> is cosine distance (1 - similarity), so we convert it
        stmt = text(f"SELECT 1 - ('{vec1_str}'::vector <=> '{vec2_str}'::vector) AS similarity")
        result = await db_session.execute(stmt)
        pgvector_similarity = result.scalar()
        
        # Compare with expected similarity (allowing for floating point precision)
        assert abs(pgvector_similarity - expected_similarity) < 0.01, \
            f"Similarity calculation incorrect for vectors {vec1} and {vec2}: " \
            f"expected {expected_similarity}, got {pgvector_similarity}"


@pytest.mark.asyncio
async def test_pgvector_indexed_search(db_session):
    """Test that pgvector indexed search works correctly."""
    # Create some sample policy
    policy = Policy(
        title="Vector Test Policy",
        description="Testing vector operations",
        url="https://example.com/vector-test",
        content="Content for vector testing"
    )
    db_session.add(policy)
    await db_session.flush()
    
    # Create chunks with known embeddings
    chunks = [
        # Chunk with vector [1,0,0,...] (aligned with x-axis)
        PolicyChunk(
            policy_id=policy.id,
            chunk_index=0,
            content="X-axis aligned content",
            embedding=[1.0] + [0.0] * 1535
        ),
        # Chunk with vector [0,1,0,...] (aligned with y-axis)
        PolicyChunk(
            policy_id=policy.id,
            chunk_index=1,
            content="Y-axis aligned content",
            embedding=[0.0, 1.0] + [0.0] * 1534
        ),
        # Chunk with vector [0.7,0.7,0,...] (45 degrees in x-y plane)
        PolicyChunk(
            policy_id=policy.id,
            chunk_index=2,
            content="45-degree content",
            embedding=[0.707, 0.707] + [0.0] * 1534
        )
    ]
    
    for chunk in chunks:
        db_session.add(chunk)
    
    await db_session.flush()
    
    # Query vector along x-axis [1,0,0,...]
    x_query = [1.0] + [0.0] * 1535
    
    # Use raw SQL to query by vector similarity
    stmt = text("""
        SELECT 
            pc.chunk_index,
            pc.content,
            (1 - (pc.embedding <=> :embedding)) AS similarity
        FROM 
            policy_chunks pc
        ORDER BY 
            similarity DESC
    """)
    
    result = await db_session.execute(stmt, {"embedding": x_query})
    rows = result.fetchall()
    
    # Verify results
    assert len(rows) == 3, "Should have retrieved all 3 chunks"
    
    # Most similar should be the x-axis aligned chunk
    assert rows[0].chunk_index == 0, "X-axis query should match x-axis chunk first"
    assert rows[0].similarity > 0.95, "Similarity with matching vector should be close to 1.0"
    
    # Second most similar should be the 45-degree chunk
    assert rows[1].chunk_index == 2, "X-axis query should match 45-degree chunk second"
    assert abs(rows[1].similarity - 0.707) < 0.1, "Similarity should be close to 0.707"
    
    # Least similar should be the y-axis chunk
    assert rows[2].chunk_index == 1, "X-axis query should match y-axis chunk last"
    assert abs(rows[2].similarity) < 0.1, "Similarity should be close to 0"


@pytest.mark.asyncio
async def test_pgvector_threshold_filtering(db_session):
    """Test that pgvector threshold filtering works correctly."""
    # Create a policy
    policy = Policy(
        title="Threshold Test Policy",
        description="Testing similarity thresholds",
        url="https://example.com/threshold-test",
        content="Content for threshold testing"
    )
    db_session.add(policy)
    await db_session.flush()
    
    # Create chunks with varying similarity to our test vector
    chunks = [
        # Very similar (0.95)
        PolicyChunk(
            policy_id=policy.id,
            chunk_index=0,
            content="Very similar content",
            embedding=[0.95, 0.31] + [0.0] * 1534  # ~0.95 similarity to [1,0,0]
        ),
        # Moderately similar (0.7)
        PolicyChunk(
            policy_id=policy.id,
            chunk_index=1,
            content="Moderately similar content",
            embedding=[0.7, 0.714] + [0.0] * 1534  # ~0.7 similarity to [1,0,0]
        ),
        # Barely similar (0.51)
        PolicyChunk(
            policy_id=policy.id,
            chunk_index=2,
            content="Barely similar content",
            embedding=[0.51, 0.86] + [0.0] * 1534  # ~0.51 similarity to [1,0,0]
        ),
        # Not very similar (0.3)
        PolicyChunk(
            policy_id=policy.id,
            chunk_index=3,
            content="Not very similar content",
            embedding=[0.3, 0.954] + [0.0] * 1534  # ~0.3 similarity to [1,0,0]
        )
    ]
    
    for chunk in chunks:
        db_session.add(chunk)
    
    await db_session.flush()
    
    # Query vector [1,0,0,...]
    query_vector = [1.0] + [0.0] * 1535
    
    # Test different thresholds
    thresholds = [0.9, 0.6, 0.5, 0.2]
    expected_counts = [1, 2, 3, 4]  # How many results we expect for each threshold
    
    for threshold, expected_count in zip(thresholds, expected_counts):
        stmt = text("""
            SELECT 
                pc.chunk_index,
                (1 - (pc.embedding <=> :embedding)) AS similarity
            FROM 
                policy_chunks pc
            WHERE 
                (1 - (pc.embedding <=> :embedding)) >= :threshold
            ORDER BY 
                similarity DESC
        """)
        
        result = await db_session.execute(
            stmt, 
            {"embedding": query_vector, "threshold": threshold}
        )
        rows = result.fetchall()
        
        assert len(rows) == expected_count, \
            f"Threshold {threshold} should return {expected_count} results, got {len(rows)}"
        
        # Verify all results meet the threshold
        for row in rows:
            assert row.similarity >= threshold, \
                f"Result with similarity {row.similarity} below threshold {threshold}"