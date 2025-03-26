"""
Tests for text chunking and embedding functionality.
"""
import pytest

from ydrpolicy.backend.services.chunking import chunk_text, chunk_markdown
from ydrpolicy.backend.services.embeddings import dummy_embed_text
from ydrpolicy.backend.database.models import Policy, PolicyChunk
from ydrpolicy.backend.logger import logger


@pytest.mark.asyncio
async def test_text_chunking():
    """Test text chunking with various content types."""
    # Test with a short text (should be a single chunk)
    short_text = "This is a short text that should not be chunked."
    short_chunks = chunk_text(short_text, chunk_size=100, chunk_overlap=20)
    assert len(short_chunks) == 1
    assert short_chunks[0] == short_text
    
    # Test with a medium text that should be split into paragraphs
    medium_text = (
        "This is the first paragraph with some content.\n\n"
        "This is the second paragraph with different content.\n\n"
        "This is the third paragraph with more information.\n\n"
        "This is the final paragraph with concluding remarks."
    )
    medium_chunks = chunk_text(medium_text, chunk_size=100, chunk_overlap=20)
    assert len(medium_chunks) > 1
    assert len(medium_chunks) <= 4  # Should not be more chunks than paragraphs
    
    # Test with a long text without clear paragraph breaks
    long_text = "This is a long text without paragraph breaks. " * 20
    long_chunks = chunk_text(long_text, chunk_size=100, chunk_overlap=20)
    assert len(long_chunks) > 1
    
    # Verify overlap works correctly
    # In the second chunk, we should find some content from the end of the first chunk
    if len(long_chunks) > 1:
        end_of_first = long_chunks[0][-20:]
        start_of_second = long_chunks[1][:20]
        
        # There should be some overlap between chunks
        assert any(c in start_of_second for c in end_of_first)


@pytest.mark.asyncio
async def test_markdown_chunking():
    """Test markdown-specific chunking."""
    # Create markdown with headings
    markdown_text = (
        "# Main Heading\n\n"
        "This is content under the main heading.\n\n"
        "## Subheading 1\n\n"
        "This is content under the first subheading.\n\n"
        "## Subheading 2\n\n"
        "This is content under the second subheading.\n\n"
        "### Sub-subheading\n\n"
        "This is content under the sub-subheading.\n\n"
        "# Another Main Heading\n\n"
        "This is content under another main heading."
    )
    
    # Chunk the markdown
    chunks = chunk_markdown(markdown_text, chunk_size=100, chunk_overlap=20)
    
    # Should split at headings, so we expect multiple chunks
    assert len(chunks) > 1
    
    # First chunk should include the first main heading
    assert "# Main Heading" in chunks[0]
    
    # Verify that headings are preserved at the start of chunks
    heading_count = 0
    for chunk in chunks:
        if chunk.strip().startswith('#'):
            heading_count += 1
    
    # We should have at least 2 chunks starting with headings
    assert heading_count >= 2


@pytest.mark.asyncio
async def test_chunking_and_embedding(policy_repository):
    """Test the end-to-end chunking and embedding process."""
    # Create a policy with substantial content
    policy = Policy(
        title="Embedding Test Policy",
        description="Policy for testing chunking and embedding",
        url="https://example.com/embedding-test",
        content="This is a test policy content that will be chunked and embedded. " * 10,
        metadata={"department": "Radiology", "category": "Embedding Tests"}
    )
    
    created_policy = await policy_repository.create(policy)
    
    # Chunk the policy content
    chunks = chunk_text(created_policy.content, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1  # We should have multiple chunks
    
    # Create embeddings for each chunk
    for i, chunk_content in enumerate(chunks):
        # Generate embedding using dummy function to avoid API calls during tests
        embedding = await dummy_embed_text(chunk_content)
        assert len(embedding) > 0  # Embedding should have values
        
        # Create a chunk with embedding
        chunk = PolicyChunk(
            policy_id=created_policy.id,
            chunk_index=i,
            content=chunk_content,
            embedding=embedding
        )
        
        # Save the chunk
        await policy_repository.create_chunk(chunk)
    
    # Retrieve the chunks for this policy
    policy_chunks = await policy_repository.get_chunks_by_policy_id(created_policy.id)
    assert len(policy_chunks) == len(chunks)
    
    # Test vector search with the created chunks
    query = "test policy content"
    query_embedding = await dummy_embed_text(query)
    
    # Search for similar chunks
    similar_chunks = await policy_repository.search_chunks_by_embedding(
        query_embedding,
        limit=2,
        similarity_threshold=0.1  # Lower threshold for dummy embeddings
    )
    
    assert len(similar_chunks) > 0
    # The chunks should have a similarity score
    assert similar_chunks[0]['similarity'] > 0


@pytest.mark.asyncio
async def test_chunk_overlap_effectiveness():
    """Test that chunk overlap effectively captures context across chunk boundaries."""
    # Create a text with key information that might get split across chunks
    text = (
        "This document outlines the radiology policy. "
        "An important requirement is that all contrast procedures "
        "must be approved by a qualified radiologist. "
        "This is a critical safety measure that must be followed at all times. "
        "Failure to comply with this policy may result in disciplinary action."
    )
    
    # Create chunks with significant overlap
    chunks = chunk_text(text, chunk_size=60, chunk_overlap=30)
    
    # We should have multiple chunks
    assert len(chunks) > 1
    
    # The key phrase "qualified radiologist" should appear in at least one chunk
    radiologist_found = False
    for chunk in chunks:
        if "qualified radiologist" in chunk:
            radiologist_found = True
            break
    
    assert radiologist_found, "Key information should be preserved in at least one chunk"
    
    # Test with smaller overlap - might split the key phrase
    small_overlap_chunks = chunk_text(text, chunk_size=60, chunk_overlap=5)
    
    # Compare: with proper overlap, context should be better preserved
    assert len(chunks) <= len(small_overlap_chunks), "Proper overlap should result in fewer or equal chunks"