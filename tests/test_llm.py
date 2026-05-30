import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from bot.services.llm.gigachat_client import GigaChatClient
from bot.services.llm.groq_client import GroqClient
from bot.services.story_maker import generate_chapter_story
from db.models import Memory
import datetime

@pytest.fixture
def mock_memories():
    return [
        Memory(content="Went to the park", created_at=datetime.datetime(2023, 10, 1), tags=["fun"]),
        Memory(content="Had a great dinner", created_at=datetime.datetime(2023, 10, 2), tags=["food"]),
    ]

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post')
async def test_gigachat_generate_text(mock_post):
    mock_post.return_value = AsyncMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = lambda: None
    
    # First call to auth, second to chat
    mock_post.side_effect = [
        AsyncMock(status_code=200, json=lambda: {"access_token": "test_token"}, raise_for_status=lambda: None),
        AsyncMock(status_code=200, json=lambda: {"choices": [{"message": {"content": "Test story"}}]}, raise_for_status=lambda: None)
    ]
    
    client = GigaChatClient(auth_key="test_auth")
    result = await client.generate_text("System", "User")
    assert result == "Test story"
    assert client.access_token == "test_token"

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post')
async def test_groq_generate_text(mock_post):
    mock_post.return_value = AsyncMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json = lambda: {"choices": [{"message": {"content": "Groq story"}}]}
    mock_post.return_value.raise_for_status = lambda: None
    
    client = GroqClient(api_key="test_key")
    result = await client.generate_text("System", "User")
    assert result == "Groq story"

@pytest.mark.asyncio
@patch('bot.services.story_maker.get_llm_client')
@patch('bot.services.story_maker.redis_async.from_url')
async def test_generate_chapter_story_success(mock_redis, mock_get_client, mock_memories):
    mock_client = AsyncMock()
    mock_client.generate_text.return_value = "Generated cohesive story"
    mock_get_client.return_value = mock_client
    
    mock_redis_client = AsyncMock()
    mock_redis_client.get.return_value = None
    mock_redis.return_value = mock_redis_client
    
    story = await generate_chapter_story(mock_memories, "01.10.2023")
    
    assert story == "Generated cohesive story"
    mock_client.generate_text.assert_called_once()
    mock_redis_client.set.assert_called_once()

@pytest.mark.asyncio
@patch('bot.services.story_maker.get_llm_client')
@patch('bot.services.story_maker.redis_async.from_url')
async def test_generate_chapter_story_fallback(mock_redis, mock_get_client, mock_memories):
    """Test fallback to text concatenation when LLM fails."""
    mock_client = AsyncMock()
    mock_client.generate_text.side_effect = Exception("LLM Error")
    mock_get_client.return_value = mock_client
    
    mock_redis_client = AsyncMock()
    mock_redis_client.get.return_value = None
    mock_redis.return_value = mock_redis_client
    
    story = await generate_chapter_story(mock_memories, "01.10.2023")
    
    assert "Went to the park" in story
    assert "Had a great dinner" in story
    assert "Generated cohesive story" not in story

@pytest.mark.asyncio
async def test_generate_chapter_story_empty():
    """Test with empty memories."""
    story = await generate_chapter_story([], "01.10.2023")
    assert story == ""

@patch.dict('os.environ', {'LLM_PROVIDER': 'groq'})
def test_get_llm_client_groq():
    from bot.services.story_maker import get_llm_client
    client = get_llm_client()
    assert isinstance(client, GroqClient)

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post')
async def test_gigachat_reauth_on_401(mock_post):
    """Test GigaChat client re-authenticates on 401 error."""
    # First call to generate_text -> 401
    # Second call (internal auth) -> 200
    # Third call to generate_text -> 200
    
    mock_401 = AsyncMock(status_code=401)
    mock_401.raise_for_status.side_effect = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_401)
    
    mock_auth_200 = AsyncMock(status_code=200, json=lambda: {"access_token": "new_token"})
    mock_auth_200.raise_for_status = lambda: None
    
    mock_200 = AsyncMock(status_code=200, json=lambda: {"choices": [{"message": {"content": "Success after reauth"}}]})
    mock_200.raise_for_status = lambda: None
    
    mock_post.side_effect = [mock_401, mock_auth_200, mock_200]
    
    client = GigaChatClient(auth_key="test_auth")
    client.access_token = "expired_token"
    
    # We need to test the actual generated text and ensure it retries correctly
    # Due to tenacity, it will retry after raising the error, so side_effect sequence:
    # 1. generate_text -> 401
    # 2. inside generate_text catches 401, calls _authenticate
    # 3. _authenticate calls post -> returns mock_auth_200
    # 4. generate_text calls response.raise_for_status() on mock_401 -> raises Exception -> tenacity retries
    # 5. tenacity retry 1: generate_text calls post -> returns mock_200
    
    # Update side_effects to match this flow
    mock_post.side_effect = [mock_401, mock_auth_200, mock_200]
    
    result = await client.generate_text("System", "User")
    assert result == "Success after reauth"
    assert client.access_token == "new_token"

@pytest.mark.asyncio
async def test_gigachat_no_auth_key():
    client = GigaChatClient(auth_key=None)
    client.auth_key = None # ensure it's empty even if in env
    with pytest.raises(ValueError):
        await client._authenticate()

@pytest.mark.asyncio
async def test_groq_no_api_key():
    client = GroqClient(api_key=None)
    client.api_key = None # ensure it's empty even if in env
    with pytest.raises(Exception):
        await client.generate_text("sys", "usr")
