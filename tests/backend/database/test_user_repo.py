"""
Tests for user repository.
"""
import pytest
from datetime import datetime

from ydrpolicy.backend.database.models import User, Chat
from ydrpolicy.backend.logger import logger


@pytest.mark.asyncio
async def test_create_user(user_repository):
    """Test creating a user with the repository."""
    user = User(
        email="repo-test@example.com",
        password_hash="hashed_password",
        full_name="Repository Test User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    assert created_user.id is not None
    assert created_user.email == "repo-test@example.com"
    assert created_user.full_name == "Repository Test User"
    
    # Test retrieval
    retrieved_user = await user_repository.get_by_email("repo-test@example.com")
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id


@pytest.mark.asyncio
async def test_get_all_users(user_repository):
    """Test getting all users from the repository."""
    # Create multiple users
    users = [
        User(
            email=f"user{i}@example.com",
            password_hash=f"password{i}",
            full_name=f"User {i}",
            is_admin=False
        )
        for i in range(3)
    ]
    
    for user in users:
        await user_repository.create(user)
    
    # Get all users
    all_users = await user_repository.get_all()
    assert len(all_users) >= 3


@pytest.mark.asyncio
async def test_update_user(user_repository):
    """Test updating a user."""
    # Create a user
    user = User(
        email="update-test@example.com",
        password_hash="initial_password",
        full_name="Update Test User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    
    # Update the user
    updated_user = await user_repository.update(
        created_user.id,
        {
            "full_name": "Updated Name",
            "is_admin": True
        }
    )
    
    assert updated_user is not None
    assert updated_user.id == created_user.id
    assert updated_user.full_name == "Updated Name"
    assert updated_user.is_admin is True
    assert updated_user.email == "update-test@example.com"  # Unchanged
    
    # Retrieve to verify the changes were saved
    retrieved_user = await user_repository.get_by_id(created_user.id)
    assert retrieved_user.full_name == "Updated Name"
    assert retrieved_user.is_admin is True


@pytest.mark.asyncio
async def test_delete_user(user_repository):
    """Test deleting a user."""
    # Create a user
    user = User(
        email="delete-test@example.com",
        password_hash="password",
        full_name="Delete Test User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    
    # Delete the user
    deleted = await user_repository.delete(created_user.id)
    assert deleted is True
    
    # Verify the user is gone
    retrieved_user = await user_repository.get_by_id(created_user.id)
    assert retrieved_user is None


@pytest.mark.asyncio
async def test_user_authentication(user_repository):
    """Test user authentication functionality."""
    # Create a user
    user = User(
        email="auth@example.com",
        password_hash="correct_hash",
        full_name="Auth Test User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    
    # Test successful authentication
    authenticated_user = await user_repository.authenticate(
        email="auth@example.com", 
        password_hash="correct_hash"
    )
    assert authenticated_user is not None
    assert authenticated_user.id == created_user.id
    
    # Test authentication with wrong password
    wrong_user = await user_repository.authenticate(
        email="auth@example.com", 
        password_hash="wrong_hash"
    )
    assert wrong_user is None
    
    # Test authentication with non-existent user
    non_existent = await user_repository.authenticate(
        email="nonexistent@example.com", 
        password_hash="any_hash"
    )
    assert non_existent is None


@pytest.mark.asyncio
async def test_admin_user_operations(user_repository):
    """Test admin-specific user operations."""
    # Create a regular user
    user = User(
        email="regular@example.com",
        password_hash="password",
        full_name="Regular User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    assert created_user.is_admin is False
    
    # Promote to admin
    promoted_user = await user_repository.promote_to_admin(created_user.id)
    assert promoted_user.is_admin is True
    
    # Retrieve and verify
    retrieved_user = await user_repository.get_by_id(created_user.id)
    assert retrieved_user.is_admin is True
    
    # Demote from admin
    demoted_user = await user_repository.demote_from_admin(created_user.id)
    assert demoted_user.is_admin is False
    
    # Retrieve and verify
    retrieved_user = await user_repository.get_by_id(created_user.id)
    assert retrieved_user.is_admin is False


@pytest.mark.asyncio
async def test_get_user_chats(user_repository, db_session):
    """Test retrieving a user's chats."""
    # Create a user
    user = User(
        email="chat-user@example.com",
        password_hash="password",
        full_name="Chat User",
        is_admin=False
    )
    
    created_user = await user_repository.create(user)
    
    # Create several chats for this user
    chats = []
    for i in range(3):
        chat = Chat(
            user_id=created_user.id,
            title=f"Chat {i}",
        )
        db_session.add(chat)
        chats.append(chat)
    
    await db_session.flush()
    
    # Retrieve user's chats
    user_chats = await user_repository.get_user_chats(created_user.id, limit=10)
    
    # Verify we got all the chats
    assert len(user_chats) == 3
    
    # Verify correct ordering (most recent first)
    # Since all were created at the same time, we can't test the ordering reliably
    # but we can verify all the chats belong to our user
    for chat in user_chats:
        assert chat.user_id == created_user.id