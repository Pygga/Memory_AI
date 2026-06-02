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
    
    story, is_fallback = await generate_chapter_story(mock_memories, "01.10.2023")
    
    assert story == "Generated cohesive story"
    assert is_fallback is False
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
    
    story, is_fallback = await generate_chapter_story(mock_memories, "01.10.2023")
    
    assert "Went to the park" in story
    assert "Had a great dinner" in story
    assert "Generated cohesive story" not in story
    assert is_fallback is True

@pytest.mark.asyncio
async def test_generate_chapter_story_empty():
    """Test with empty memories."""
    story, is_fallback = await generate_chapter_story([], "01.10.2023")
    assert story == ""
    assert is_fallback is False

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


@pytest.mark.asyncio
@patch('bot.services.semantic_grouper.get_llm_client')
async def test_group_memories_semantically_success(mock_get_client, mock_memories):
    mock_client = AsyncMock()
    mock_client.generate_text.return_value = (
        '[\n'
        '  {\n'
        '    "title": "Глава про парк",\n'
        '    "memory_ids": [1]\n'
        '  },\n'
        '  {\n'
        '    "title": "Глава про ужин",\n'
        '    "memory_ids": [2]\n'
        '  }\n'
        ']'
    )
    mock_get_client.return_value = mock_client
    
    # Assign IDs to mock memories
    mock_memories[0].id = 1
    mock_memories[1].id = 2
    
    from bot.services.semantic_grouper import group_memories_semantically
    result = await group_memories_semantically(mock_memories)
    
    assert len(result) == 2
    assert result[0]["title"] == "Глава про парк"
    assert result[0]["memory_ids"] == [1]
    assert result[1]["title"] == "Глава про ужин"
    assert result[1]["memory_ids"] == [2]


@pytest.mark.asyncio
@patch('bot.services.semantic_grouper.get_llm_client')
async def test_group_memories_semantically_failure(mock_get_client, mock_memories):
    mock_client = AsyncMock()
    mock_client.generate_text.side_effect = Exception("LLM connection error")
    mock_get_client.return_value = mock_client
    
    from bot.services.semantic_grouper import group_memories_semantically
    result = await group_memories_semantically(mock_memories)
    
    assert result == []


@pytest.mark.asyncio
async def test_log_llm_usage():
    from bot.services.llm_logger import log_llm_usage
    from db.models import LLMLog, User
    
    mock_session = AsyncMock()
    mock_user_result = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_user_result
    
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    
    await log_llm_usage(
        user_id_tg=123,
        story_id=456,
        provider="groq",
        model_name="llama-3.3-70b-versatile",
        prompt_t=1000,
        completion_t=500,
        session_factory=mock_session_factory
    )
    
    # Verify session added LLMLog with correct cost
    assert mock_session.add.call_count == 1
    added_log = mock_session.add.call_args[0][0]
    assert isinstance(added_log, LLMLog)
    assert added_log.provider == "groq"
    assert added_log.total_tokens == 1500
    # $0.59 * 1000/1M + $0.79 * 500/1M = 0.00059 + 0.000395 = 0.000985
    assert abs(added_log.cost_usd - 0.000985) < 1e-9
    mock_session.commit.assert_called_once()
