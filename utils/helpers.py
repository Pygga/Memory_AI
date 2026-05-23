"""General helper utilities."""
import re


def extract_tags(text: str) -> list[str]:
    """
    Extract hashtags from text.
    
    Args:
        text: Input text that may contain #tags
        
    Returns:
        List of tag strings without # prefix, lowercase
    """
    if not text:
        return []
    tags = re.findall(r'#(\w+)', text.lower())
    return list(set(tags))  # Remove duplicates