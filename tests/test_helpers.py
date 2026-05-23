"""Tests for utils/helpers.py"""
import pytest
from utils.helpers import extract_tags


class TestExtractTags:
    """Tests for extract_tags function."""

    def test_extract_single_tag(self):
        """Test extracting one hashtag."""
        text = "Отличный день #счастье"
        assert extract_tags(text) == ["счастье"]

    def test_extract_multiple_tags(self):
        """Test extracting multiple hashtags."""
        text = "Путешествие #отпуск #море #лето"
        tags = extract_tags(text)
        assert len(tags) == 3
        assert set(tags) == {"отпуск", "море", "лето"}

    def test_extract_no_tags(self):
        """Test text without hashtags."""
        text = "Просто текст без тегов"
        assert extract_tags(text) == []

    def test_extract_empty_string(self):
        """Test empty input."""
        assert extract_tags("") == []

    def test_extract_case_insensitive(self):
        """Test that tags are lowercased."""
        text = "Тест #ТеГ #ДРУГОЙ"
        tags = extract_tags(text)
        assert tags == ["тег", "другой"]

    def test_extract_duplicates_removed(self):
        """Test that duplicate tags are removed."""
        text = "Повтор #тест и снова #тест"
        assert extract_tags(text) == ["тест"]