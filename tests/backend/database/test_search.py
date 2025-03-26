"""
Tests for search functionality including vector, text, and hybrid search.
"""
import pytest

from ydrpolicy.backend.database.models import Policy, PolicyChunk
from ydrpolicy.backend.services.embeddings import dummy_embed_text
from ydrpolicy.backend.services.chunking import chunk_text
from ydrpolicy.backend.logger import logger


@pytest.fixture(scope="function")
async def search_test_data(policy_repository):
    """
    Create test data for search functionality tests.
    Creates multiple policies with chunks and embeddings.
    """
    # Create a policy for search testing
    policy1 = Policy(
        title="Radiology Contrast Protocol",
        description="Guidelines for administering contrast in radiology",
        url="https://example.com/policy/contrast",
        content="This is a specialized radiology protocol for contrast administration. " * 10,
        metadata={"department": "Radiology", "category": "Protocols"}
    )
    
    policy2 = Policy(
        title="MRI Safety Guidelines",
        description="Safety procedures for MRI examinations",
        url="https://example.com/policy/mri-safety",
        content="MRI safety guidelines require screening for metal objects. " * 10,
        metadata={"department": "Radiology", "category": "Safety"}
    )
    
    policy3 = Policy(
        title="CT Radiation Dose Management",
        description="Protocol for managing radiation dose in CT",
        url="https://example.com/policy/ct-dose",
        content="CT radiation dose should be optimized using ALARA principles. " * 10,
        metadata={"department": "Radiology", "category": "Safety"}
    )
    
    created_policies = []
    created_policies.append(await policy_repository.create(policy1))
    created_policies.append(await policy_repository.create(policy2))
    created_policies.append(await policy_repository.create(policy3))
    
    # Create chunks and embeddings for each policy
    for policy in created_policies:
        chunks = chunk_text(policy.content, chunk_size=100, chunk_overlap=20)
        for i, chunk_content in enumerate(chunks):
            embedding = await dummy_embed_text(chunk_content)
            chunk = PolicyChunk(
                policy_id=policy.id,
                chunk_index=i,
                content=chunk_content,
                embedding=embedding
            )
            await policy_repository.create_chunk(chunk)
    
    return created_policies


@pytest.mark.asyncio
async def test_vector_search(policy_repository, search_test_data):
    """Test vector-based semantic search."""
    # Create a query embedding
    query = "contrast protocol for radiology"
    query_embedding = await dummy_embed_text(query)
    
    # Perform vector search
    vector_results = await policy_repository.search_chunks_by_embedding(
        query_embedding,
        limit=5,
        similarity_threshold=0.1  # Lower threshold for dummy embeddings
    )
    
    assert len(vector_results) > 0
    assert 'similarity' in vector_results[0]
    
    # Verify at least one result mentions contrast
    contains_contrast = False
    for result in vector_results:
        if "contrast" in result["content"].lower():
            contains_contrast = True
            break
    
    assert contains_contrast, "Vector search results should include content about contrast"


@pytest.mark.asyncio
async def test_text_search(policy_repository, search_test_data):
    """Test text-based keyword search."""
    # Perform text search for "contrast"
    text_results = await policy_repository.text_search_chunks("contrast")
    
    assert len(text_results) > 0
    assert 'text_score' in text_results[0]
    
    # All results should contain the word "contrast"
    for result in text_results:
        assert "contrast" in result["content"].lower()
    
    # Now search for "MRI"
    mri_results = await policy_repository.text_search_chunks("mri")
    
    assert len(mri_results) > 0
    for result in mri_results:
        assert "mri" in result["content"].lower()


@pytest.mark.asyncio
async def test_hybrid_search(policy_repository, search_test_data):
    """Test hybrid search combining vector and text search."""
    # Create a query
    query = "radiation safety in CT"
    query_embedding = await dummy_embed_text(query)
    
    # Perform hybrid search
    hybrid_results = await policy_repository.hybrid_search(
        query=query,
        embedding=query_embedding,
        vector_weight=0.7,  # 70% vector search, 30% keyword search
        limit=5, 
        similarity_threshold=0.1  # Lower threshold for dummy embeddings
    )
    
    assert len(hybrid_results) > 0
    assert 'combined_score' in hybrid_results[0]
    assert 'vector_score' in hybrid_results[0]
    assert 'text_score' in hybrid_results[0]
    
    # Results should include content about radiation or CT
    found_relevant = False
    for result in hybrid_results:
        content = result["content"].lower()
        if "radiation" in content or "ct" in content:
            found_relevant = True
            break
            
    assert found_relevant, "Hybrid search results should include content about radiation or CT"
    
    # Verify that combined scores are calculated correctly
    for result in hybrid_results:
        # Combined score should be a weighted average of vector and text scores
        calculated_score = 0.7 * result['vector_score'] + 0.3 * result['text_score']
        assert abs(result['combined_score'] - calculated_score) < 0.0001  # Allow for floating-point precision


@pytest.mark.asyncio
async def test_all_search_methods(policy_repository, search_test_data):
    """Test all three search methods: vector, text, and hybrid."""
    # Common search query
    query = "safety guidelines radiology"
    query_embedding = await dummy_embed_text(query)
    
    # 1. Test vector search
    vector_results = await policy_repository.search_chunks_by_embedding(
        embedding=query_embedding,
        limit=3,
        similarity_threshold=0.1  # Lower threshold for dummy embeddings
    )
    
    assert len(vector_results) > 0
    assert 'similarity' in vector_results[0]
    logger.info(f"Vector search found {len(vector_results)} results")
    
    # 2. Test text-only search
    text_results = await policy_repository.text_search_chunks(
        query=query,
        limit=3
    )
    
    assert len(text_results) > 0
    assert 'text_score' in text_results[0]
    logger.info(f"Text search found {len(text_results)} results")
    
    # 3. Test hybrid search
    hybrid_results = await policy_repository.hybrid_search(
        query=query,
        embedding=query_embedding,
        vector_weight=0.7,  # 70% vector search, 30% keyword search
        limit=3,
        similarity_threshold=0.1  # Lower threshold for dummy embeddings
    )
    
    assert len(hybrid_results) > 0
    assert 'combined_score' in hybrid_results[0]
    assert 'vector_score' in hybrid_results[0]
    assert 'text_score' in hybrid_results[0]
    logger.info(f"Hybrid search found {len(hybrid_results)} results")


@pytest.mark.asyncio
async def test_search_with_different_weights(policy_repository, search_test_data):
    """Test hybrid search with different vector/text weights."""
    query = "radiation safety"
    query_embedding = await dummy_embed_text(query)
    
    # Test with different weight configurations
    weight_configs = [0.0, 0.3, 0.5, 0.7, 1.0]
    
    for weight in weight_configs:
        results = await policy_repository.hybrid_search(
            query=query,
            embedding=query_embedding,
            vector_weight=weight,
            limit=3,
            similarity_threshold=0.1
        )
        
        assert len(results) > 0
        logger.info(f"Vector weight {weight}: found {len(results)} results")
        
        # For pure text search (weight=0) or pure vector search (weight=1),
        # verify the scores are calculated correctly
        if weight == 0.0:
            # Should be equivalent to text search
            for result in results:
                assert abs(result['combined_score'] - result['text_score']) < 0.0001
        elif weight == 1.0:
            # Should be equivalent to vector search
            for result in results:
                assert abs(result['combined_score'] - result['vector_score']) < 0.0001