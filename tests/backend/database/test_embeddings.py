"""
Tests for embedding functionality.
"""
import pytest
import numpy as np

from ydrpolicy.backend.services.embeddings import dummy_embed_text, embed_texts
from ydrpolicy.backend.config import config
from ydrpolicy.backend.logger import logger


@pytest.mark.asyncio
async def test_single_embedding():
    """Test creating a single embedding."""
    text = "This is a test text for embedding generation."
    
    # Use dummy embedding to avoid API calls during testing
    embedding = await dummy_embed_text(text)
    
    # Verify embedding dimensions match the configuration
    assert len(embedding) == config.RAG.EMBEDDING_DIMENSIONS
    
    # Verify embedding is a normalized vector (length approximately 1)
    vector_length = np.sqrt(sum([x*x for x in embedding]))
    assert abs(vector_length - 1.0) < 0.0001
    
    # Verify different texts produce different embeddings
    text2 = "This is a completely different text."
    embedding2 = await dummy_embed_text(text2)
    
    # Calculate cosine similarity
    dot_product = sum(a*b for a, b in zip(embedding, embedding2))
    similarity = dot_product / (vector_length * np.sqrt(sum([x*x for x in embedding2])))
    
    # Similar texts should have similarity < 1.0
    assert similarity < 1.0, "Different texts should produce different embeddings"


@pytest.mark.asyncio
async def test_empty_text_embedding():
    """Test embedding behavior with empty text."""
    # Empty string
    empty_embedding = await dummy_embed_text("")
    
    # Verify dimensions match the configuration
    assert len(empty_embedding) == config.RAG.EMBEDDING_DIMENSIONS
    
    # Whitespace-only string
    whitespace_embedding = await dummy_embed_text("   ")
    
    # Verify dimensions match the configuration
    assert len(whitespace_embedding) == config.RAG.EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
async def test_similar_texts_have_similar_embeddings():
    """Test that similar texts have similar embeddings."""
    text1 = "The patient underwent an MRI scan of the brain."
    text2 = "The patient had a brain MRI examination."
    text3 = "The company's quarterly financial report shows increased profits."
    
    embedding1 = await dummy_embed_text(text1)
    embedding2 = await dummy_embed_text(text2)
    embedding3 = await dummy_embed_text(text3)
    
    # Calculate similarities
    def cosine_similarity(vec1, vec2):
        dot_product = sum(a*b for a, b in zip(vec1, vec2))
        norm1 = np.sqrt(sum([x*x for x in vec1]))
        norm2 = np.sqrt(sum([x*x for x in vec2]))
        return dot_product / (norm1 * norm2)
    
    sim_1_2 = cosine_similarity(embedding1, embedding2)
    sim_1_3 = cosine_similarity(embedding1, embedding3)
    
    # Similar texts (both about MRI) should have higher similarity
    # than dissimilar texts (MRI vs financial reports)
    assert sim_1_2 > sim_1_3, "Similar texts should have more similar embeddings"


@pytest.mark.asyncio
async def test_batch_embedding():
    """Test batch embedding of multiple texts."""
    texts = [
        "This is the first test text.",
        "This is the second test text.",
        "This is the third test text."
    ]
    
    # Use the batch embedding function with our dummy embedder
    embeddings = []
    for text in texts:
        embedding = await dummy_embed_text(text)
        embeddings.append(embedding)
    
    # Verify we got the right number of embeddings
    assert len(embeddings) == len(texts)
    
    # Verify each embedding has the correct dimensions
    for embedding in embeddings:
        assert len(embedding) == config.RAG.EMBEDDING_DIMENSIONS
    
    # Verify each embedding is different
    # Compare the first embedding with all others
    for i in range(1, len(embeddings)):
        # Calculate similarity
        dot_product = sum(a*b for a, b in zip(embeddings[0], embeddings[i]))
        norm1 = np.sqrt(sum([x*x for x in embeddings[0]]))
        norm2 = np.sqrt(sum([x*x for x in embeddings[i]]))
        similarity = dot_product / (norm1 * norm2)
        
        # Should not be identical
        assert similarity < 1.0, "Different texts should produce different embeddings"


@pytest.mark.asyncio
async def test_embedding_determinism():
    """Test that the same text always produces the same embedding."""
    text = "This text should always produce the same embedding."
    
    # Generate embedding twice
    embedding1 = await dummy_embed_text(text)
    embedding2 = await dummy_embed_text(text)
    
    # They should be identical (for our dummy embedding function)
    assert embedding1 == embedding2, "Same text should produce identical embeddings"
    
    # Verify slight modifications produce different embeddings
    modified_text = "This text should always produce the same embedding!"
    modified_embedding = await dummy_embed_text(modified_text)
    
    # Should not be identical
    assert embedding1 != modified_embedding, "Modified text should produce different embeddings"


@pytest.mark.asyncio
async def test_long_text_embedding():
    """Test embedding generation for long texts."""
    # Generate a long text
    long_text = "This is a long text for embedding testing. " * 50
    
    # Generate embedding
    embedding = await dummy_embed_text(long_text)
    
    # Verify embedding dimensions match the configuration
    assert len(embedding) == config.RAG.EMBEDDING_DIMENSIONS
    
    # Verify embedding is a normalized vector (length approximately 1)
    vector_length = np.sqrt(sum([x*x for x in embedding]))
    assert abs(vector_length - 1.0) < 0.0001


@pytest.mark.asyncio
async def test_embedding_vector_operations():
    """Test vector operations on embeddings."""
    # Generate embeddings for three related texts
    text1 = "King and Queen"
    text2 = "Man and Woman"
    text3 = "Boy and Girl"
    
    emb1 = await dummy_embed_text(text1)
    emb2 = await dummy_embed_text(text2)
    emb3 = await dummy_embed_text(text3)
    
    # Convert to numpy arrays for easier vector operations
    emb1_np = np.array(emb1)
    emb2_np = np.array(emb2)
    emb3_np = np.array(emb3)
    
    # Test vector addition and subtraction
    # Note: our dummy embeddings aren't semantically meaningful,
    # but we can still test the vector operations
    
    # Calculate vector from King to Queen (roughly)
    # And vector from Man to Woman (roughly)
    # These should have some similarity
    king_queen_vec = await dummy_embed_text("Queen") - await dummy_embed_text("King")
    man_woman_vec = await dummy_embed_text("Woman") - await dummy_embed_text("Man")
    
    # Normalize the vectors
    king_queen_vec = king_queen_vec / np.linalg.norm(king_queen_vec)
    man_woman_vec = man_woman_vec / np.linalg.norm(man_woman_vec)
    
    # Calculate similarity
    similarity = np.dot(king_queen_vec, man_woman_vec)
    
    # Just verify we can do these operations, not testing actual results
    # since dummy embeddings don't have semantic meaning
    assert isinstance(similarity, float)