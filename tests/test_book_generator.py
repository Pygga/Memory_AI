import pytest
import datetime
from unittest.mock import patch, AsyncMock, MagicMock
from db.models import Memory, User
from bot.services.book_generator import group_memories_by_week, generate_book

def test_group_memories_by_week():
    memories = [
        Memory(created_at=datetime.datetime(2023, 10, 1), content="A"), # Sunday
        Memory(created_at=datetime.datetime(2023, 10, 2), content="B"), # Monday
        Memory(created_at=datetime.datetime(2023, 10, 3), content="C"), # Tuesday
    ]
    weeks = group_memories_by_week(memories)
    
    assert len(weeks) == 2
    assert "2023-10-02" in weeks
    assert "2023-09-25" in weeks
    assert len(weeks["2023-10-02"]["memories"]) == 2
    assert len(weeks["2023-09-25"]["memories"]) == 1

@pytest.mark.asyncio
@patch('bot.services.book_generator.generate_chapter_story', new_callable=AsyncMock)
@patch('bot.services.book_generator.HTML')
@patch('bot.services.book_generator.CSS')
@patch('bot.services.book_generator.markdown')
async def test_generate_book(mock_markdown, mock_css, mock_html, mock_generate_chapter):
    mock_generate_chapter.return_value = ("Story", False)
    mock_markdown.markdown.return_value = "<p>Story</p>"
    
    # Mock HTML object and write_pdf
    mock_html_obj = MagicMock()
    mock_html.return_value = mock_html_obj
    
    # Mock db session and query results
    mock_session = AsyncMock()
    mock_user_result = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user_result.scalar_one_or_none.return_value = mock_user
    
    mock_memory_result = MagicMock()
    mock_memory_result.scalars().all.return_value = [
        Memory(id=1, user_id=1, content="A", created_at=datetime.datetime(2023, 10, 1), memory_type="text", file_id=None),
        Memory(id=2, user_id=1, content="B", created_at=datetime.datetime(2023, 10, 2), memory_type="photo", file_id="abc")
    ]
    
    mock_session.execute.side_effect = [mock_user_result, mock_memory_result]
    
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    
    progress_mock = AsyncMock()
    
    with patch('pathlib.Path.exists', return_value=True), patch('pathlib.Path.mkdir', return_value=None), patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "<html>{{ total_memories }}</html>"
        
        pdf_path, has_fallback = await generate_book(123, mock_session_factory, progress_callback=progress_mock, theme='classic')
        
        assert "memory_book_123_" in pdf_path
        assert has_fallback is False
        assert mock_generate_chapter.call_count == 2 # 2 weeks in memories list
        mock_html_obj.write_pdf.assert_called_once()
        assert progress_mock.call_count == 2


@pytest.mark.asyncio
@patch('bot.services.semantic_grouper.group_memories_semantically', new_callable=AsyncMock)
@patch('bot.services.book_generator.generate_chapter_story', new_callable=AsyncMock)
@patch('bot.services.book_generator.get_llm_client')
async def test_ensure_chapters_exist(mock_get_client, mock_generate_chapter, mock_group_semantically):
    mock_client = MagicMock()
    mock_client.last_prompt_tokens = 100
    mock_client.last_completion_tokens = 50
    mock_get_client.return_value = mock_client
    from bot.services.book_generator import ensure_chapters_exist
    from db.models import Story, Memory
    
    # Mock groups returned by semantic group helper
    mock_group_semantically.return_value = [
        {"title": "Глава про кота", "memory_ids": [1]},
        {"title": "Глава про собаку", "memory_ids": [2]}
    ]
    mock_generate_chapter.return_value = ("Markdown story content", False)
    
    mock_session = AsyncMock()
    mock_story_obj = MagicMock()
    mock_story_obj.chapters = [] # No chapters yet
    
    mock_story_result = MagicMock()
    mock_story_result.scalar_one_or_none.return_value = mock_story_obj
    
    mock_user_result = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user_result.scalar_one_or_none.return_value = mock_user
    
    mock_memories = [
        Memory(id=1, content="Кот спал на мягком диване весь день", created_at=datetime.datetime(2023, 10, 1), memory_type="text"),
        Memory(id=2, content="Пес бегал по зеленому лугу за мячиком", created_at=datetime.datetime(2023, 10, 2), memory_type="text")
    ]
    
    mock_memory_result = MagicMock()
    mock_memory_result.scalars().all.return_value = mock_memories
    
    # Mock executing queries
    mock_session.execute.side_effect = [mock_story_result, mock_user_result, mock_memory_result]
    
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    
    has_fallback = await ensure_chapters_exist(
        story_id=456,
        user_id_tg=123,
        session_factory=mock_session_factory
    )
    
    assert has_fallback is False
    assert mock_group_semantically.call_count == 1
    assert mock_generate_chapter.call_count == 2
    
    # Verify session added two chapters
    assert mock_session.add.call_count == 2
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_validate_story_memories_empty():
    from bot.services.book_generator import validate_story_memories
    mock_session_factory = MagicMock()
    is_valid, err = await validate_story_memories(story_id=1, user_id_tg=123, session_factory=mock_session_factory, memories=[])
    assert is_valid is False
    assert "нет воспоминаний" in err


@pytest.mark.asyncio
async def test_validate_story_memories_single_photo():
    from bot.services.book_generator import validate_story_memories
    from db.models import Memory
    mock_session_factory = MagicMock()
    memories = [
        Memory(id=1, content="", memory_type="photo")
    ]
    is_valid, err = await validate_story_memories(story_id=1, user_id_tg=123, session_factory=mock_session_factory, memories=memories)
    assert is_valid is False
    assert "всего одна фотография" in err


@pytest.mark.asyncio
async def test_validate_story_memories_too_short():
    from bot.services.book_generator import validate_story_memories
    from db.models import Memory
    mock_session_factory = MagicMock()
    memories = [
        Memory(id=1, content="Кот", memory_type="text")
    ]
    is_valid, err = await validate_story_memories(story_id=1, user_id_tg=123, session_factory=mock_session_factory, memories=memories)
    assert is_valid is False
    assert "слишком короткое" in err


@pytest.mark.asyncio
async def test_validate_story_memories_valid():
    from bot.services.book_generator import validate_story_memories
    from db.models import Memory
    mock_session_factory = MagicMock()
    memories = [
        Memory(id=1, content="Сегодня был отличный и очень солнечный день.", memory_type="text"),
        Memory(id=2, content="Мы пошли гулять в большой парк всей семьей.", memory_type="text")
    ]
    is_valid, err = await validate_story_memories(story_id=1, user_id_tg=123, session_factory=mock_session_factory, memories=memories)
    assert is_valid is True
    assert err == ""
