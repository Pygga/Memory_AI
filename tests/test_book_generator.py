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
    mock_user_result.scalar_one_or_none.return_value = 1
    
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
