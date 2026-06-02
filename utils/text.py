"""Text processing utilities for Telegram HTML and markdown operations."""
import re


def md_to_telegram_html(text: str) -> str:
    """Escape HTML characters and convert basic markdown bold/italic to Telegram HTML tags.
    
    Args:
        text: Raw text possibly containing markdown formatting.
        
    Returns:
        Text safe for Telegram HTML parse mode with bold/italic converted.
    """
    if not text:
        return ""
    # Escape HTML special chars
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convert bold **text** or __text__ to <b>text</b>
    escaped = re.sub(r'\*\*(.*?)\*\*|__(.*?)__', lambda m: f"<b>{m.group(1) or m.group(2)}</b>", escaped)
    # Convert italic *text* or _text_ to <i>text</i>
    escaped = re.sub(r'\*(.*?)\*|_(.*?)_', lambda m: f"<i>{m.group(1) or m.group(2)}</i>", escaped)
    return escaped


def extract_title_from_markdown(story_md: str) -> tuple[str | None, str]:
    """Extract a chapter title from LLM-generated markdown and return cleaned text.
    
    Looks for title patterns: '# Title', 'Title: ...', 'Название: ...'
    at the beginning of the text.
    
    Args:
        story_md: Raw markdown text from LLM.
        
    Returns:
        Tuple of (extracted_title_or_None, cleaned_markdown_text).
    """
    lines = story_md.strip().split('\n')
    clean_lines = []
    title = None
    
    for line in lines:
        stripped = line.strip()
        if title is None:
            if stripped.startswith('# '):
                title = stripped[2:].strip().strip('*').strip('_').strip('"').strip("'")
                continue
            elif stripped.lower().startswith('title:'):
                title = stripped[6:].strip().strip('*').strip('_').strip('"').strip("'")
                continue
            elif stripped.lower().startswith('название:'):
                title = stripped[9:].strip().strip('*').strip('_').strip('"').strip("'")
                continue
        clean_lines.append(line)
    
    return title, '\n'.join(clean_lines).strip()
