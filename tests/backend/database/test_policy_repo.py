"""
Tests for policy repository functions.
"""
import pytest
from datetime import datetime

from ydrpolicy.backend.database.models import Policy, PolicyChunk, PolicyUpdate
from ydrpolicy.backend.logger import logger


@pytest.mark.asyncio
async def test_create_policy(policy_repository):
    """Test creating a policy with the repository."""
    policy = Policy(
        title="Repository Test Policy",
        description="This is a test policy description.",
        url="https://example.com/repo-policy",
        content="This is a test policy content.",
        metadata={"department": "Radiology", "category": "Safety"}
    )
    
    created_policy = await policy_repository.create(policy)
    assert created_policy.id is not None
    assert created_policy.title == "Repository Test Policy"
    
    # Test retrieval
    retrieved_policy = await policy_repository.get_by_id(created_policy.id)
    assert retrieved_policy is not None
    assert retrieved_policy.title == "Repository Test Policy"
    assert retrieved_policy.content == "This is a test policy content."


@pytest.mark.asyncio
async def test_get_by_url(policy_repository):
    """Test retrieving a policy by its URL."""
    # Create a policy
    url = "https://example.com/unique-policy-url"
    policy = Policy(
        title="URL Test Policy",
        description="This is a test for URL retrieval",
        url=url,
        content="This policy can be retrieved by URL."
    )
    
    await policy_repository.create(policy)
    
    # Retrieve by URL
    retrieved_policy = await policy_repository.get_by_url(url)
    assert retrieved_policy is not None
    assert retrieved_policy.title == "URL Test Policy"
    
    # Test with non-existent URL
    non_existent = await policy_repository.get_by_url("https://example.com/non-existent")
    assert non_existent is None


@pytest.mark.asyncio
async def test_full_text_search(policy_repository):
    """Test full-text search on policies."""
    # Create policies with specific searchable terms
    policies = [
        Policy(
            title="Radiology Safety Policy",
            description="Guidelines for radiation safety protocols",
            url="https://example.com/rad-safety",
            content="This policy outlines safety measures for radiation exposure."
        ),
        Policy(
            title="Contrast Administration",
            description="Protocols for contrast media administration",
            url="https://example.com/contrast",
            content="This policy covers the use of contrast agents in imaging studies."
        ),
        Policy(
            title="Equipment Maintenance",
            description="Guidelines for equipment upkeep",
            url="https://example.com/equipment",
            content="Regular maintenance procedures for imaging equipment."
        )
    ]
    
    for policy in policies:
        await policy_repository.create(policy)
    
    # Search for "radiation"
    radiation_results = await policy_repository.full_text_search("radiation")
    assert len(radiation_results) > 0
    assert "Radiology Safety Policy" in [r["title"] for r in radiation_results]
    
    # Search for "contrast"
    contrast_results = await policy_repository.full_text_search("contrast")
    assert len(contrast_results) > 0
    assert "Contrast Administration" in [r["title"] for r in contrast_results]
    
    # Search for "policy" (should match multiple)
    policy_results = await policy_repository.full_text_search("policy")
    assert len(policy_results) >= 2


@pytest.mark.asyncio
async def test_policy_update_logging(policy_repository, db_session):
    """Test logging policy updates."""
    # Create a policy
    policy = Policy(
        title="Update Test Policy",
        description="Policy for testing updates",
        url="https://example.com/update-test",
        content="Original content",
        metadata={"department": "Radiology"}
    )
    created_policy = await policy_repository.create(policy)
    
    # Log an update
    update_details = {
        "changed_fields": ["content", "title"],
        "old_title": "Update Test Policy",
        "new_title": "Updated Policy",
        "content_changed": True
    }
    
    admin_id = 1  # Mock admin ID
    
    log_entry = await policy_repository.log_policy_update(
        policy_id=created_policy.id,
        admin_id=admin_id,
        action="update",
        details=update_details
    )
    
    assert log_entry.id is not None
    assert log_entry.policy_id == created_policy.id
    assert log_entry.admin_id == admin_id
    assert log_entry.action == "update"
    
    # Get update history
    history = await policy_repository.get_policy_update_history(created_policy.id)
    assert len(history) == 1
    assert history[0].id == log_entry.id


@pytest.mark.asyncio
async def test_create_chunk(policy_repository, db_session):
    """Test creating policy chunks with the repository."""
    # Create a policy
    policy = Policy(
        title="Chunk Repository Test",
        description="Testing chunk creation via repository",
        url="https://example.com/chunk-repo-test",
        content="Full policy content for testing chunks"
    )
    created_policy = await policy_repository.create(policy)
    
    # Create chunks for this policy
    chunks = [
        PolicyChunk(
            policy_id=created_policy.id,
            chunk_index=0,
            content="First chunk of content",
            embedding=[0.1] * 1536  # Dummy embedding
        ),
        PolicyChunk(
            policy_id=created_policy.id,
            chunk_index=1,
            content="Second chunk of content",
            embedding=[0.2] * 1536  # Dummy embedding
        )
    ]
    
    for chunk in chunks:
        await policy_repository.create_chunk(chunk)
    
    # Retrieve chunks for policy
    policy_chunks = await policy_repository.get_chunks_by_policy_id(created_policy.id)
    
    assert len(policy_chunks) == 2
    assert policy_chunks[0].chunk_index == 0
    assert policy_chunks[1].chunk_index == 1


@pytest.mark.asyncio
async def test_recent_policies(policy_repository):
    """Test retrieving recent policies."""
    # Create multiple policies
    for i in range(5):
        policy = Policy(
            title=f"Recent Policy {i}",
            description=f"Testing recent policies retrieval {i}",
            url=f"https://example.com/recent-{i}",
            content=f"Content for recent policy {i}"
        )
        await policy_repository.create(policy)
    
    # Get recent policies
    recent_policies = await policy_repository.get_recent_policies(limit=3)
    
    # Should return 3 most recent policies
    assert len(recent_policies) == 3
    
    # They should be in reverse chronological order (newest first)
    for i in range(len(recent_policies) - 1):
        assert recent_policies[i].created_at >= recent_policies[i+1].created_at


@pytest.mark.asyncio
async def test_get_complete_policies_from_chunks(policy_repository, db_session):
    """Test retrieving complete policies from chunk search results."""
    # Create multiple policies
    policies = [
        Policy(
            title=f"Complete Policy Test {i}",
            description=f"Testing complete policy retrieval {i}",
            url=f"https://example.com/policy/complete-{i}",
            content=f"Complete policy content for test {i}. This is a longer content with more details.",
            metadata={"department": "Radiology", "test_case": "complete_retrieval"}
        )
        for i in range(3)
    ]
    
    created_policies = []
    for policy in policies:
        created = await policy_repository.create(policy)
        created_policies.append(created)
        
        # Create chunks for each policy
        for i in range(2):  # 2 chunks per policy
            chunk = PolicyChunk(
                policy_id=created.id,
                chunk_index=i,
                content=f"Chunk {i} of policy {created.id}: partial content",
                embedding=[0.1 * i] * 1536  # Dummy embedding
            )
            await policy_repository.create_chunk(chunk)
    
    # Create mock chunk results (as if from a search)
    chunk_results = [
        {
            "id": 1,
            "policy_id": created_policies[0].id,
            "chunk_index": 0,
            "content": "Chunk 0 content",
            "policy_title": created_policies[0].title,
            "similarity": 0.95
        },
        {
            "id": 2,
            "policy_id": created_policies[1].id,
            "chunk_index": 1,
            "content": "Chunk 1 content",
            "policy_title": created_policies[1].title,
            "similarity": 0.85
        }
    ]
    
    # Get the complete policies from chunks
    complete_policies = await policy_repository.get_policies_from_chunks(chunk_results)
    
    # Verify we got the correct policies
    assert len(complete_policies) == 2
    policy_ids = [p.id for p in complete_policies]
    assert created_policies[0].id in policy_ids
    assert created_policies[1].id in policy_ids
    
    # Check that each policy has its full content
    for policy in complete_policies:
        assert "Complete policy content for test" in policy.content