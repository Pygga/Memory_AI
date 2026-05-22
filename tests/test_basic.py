"""Tests for tag extraction and basic functionality."""
import pytest
import re


def extract_tags(text: str) -> list[str]:
    """Extract hashtags from text."""
    tags = re.findall(r'#(\w+)', text.lower())
    return tags


class TestTagExtraction:
    """Tests for tag extraction functionality."""
    
    def test_extract_single_tag(self):
        """Test extracting a single tag."""
        text = "Сегодня хороший день #счастье"
        assert extract_tags(text) == ["счастье"]
    
    def test_extract_multiple_tags(self):
        """Test extracting multiple tags."""
        text = "Отличный день #лето #отпуск #море"
        assert extract_tags(text) == ["лето", "отпуск", "море"]
    
    def test_extract_no_tags(self):
        """Test when no tags present."""
        text = "Просто текст без тегов"
        assert extract_tags(text) == []
    
    def test_extract_tags_mixed_content(self):
        """Test extracting tags from mixed content."""
        text = "Встреча с друзьями #друзья в кафе #еда было весело!"
        assert extract_tags(text) == ["друзья", "еда"]
    
    def test_extract_tags_case_insensitive(self):
        """Test that tag extraction is case insensitive."""
        text = "Тег #ТЕСТ и еще #Тест2"
        assert extract_tags(text) == ["тест", "тест2"]


class TestMemoryGrouping:
    """Tests for memory grouping by week."""
    
    def test_group_memories_by_week(self):
        """Test grouping memories by week."""
        from datetime import datetime, timedelta
        from bot.services.book_generator import group_memories_by_week
        
        # Create mock memories
        class MockMemory:
            def __init__(self, date):
                self.created_at = date
        
        # Create memories for different weeks
        today = datetime.now()
        last_week = today - timedelta(days=7)
        
        memories = [
            MockMemory(today),
            MockMemory(today - timedelta(days=1)),
            MockMemory(last_week),
        ]
        
        weeks = group_memories_by_week(memories)
        
        # Should have 2 weeks
        assert len(weeks) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
