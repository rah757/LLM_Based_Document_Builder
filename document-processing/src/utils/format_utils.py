"""
Formatting utilities
Handles facts formatting, display helpers, and safe string operations
"""

import re
import os


def format_facts_for_display(facts_by_name):
    """
    Format facts overlay as readable text for display
    
    Args:
        facts_by_name: Dictionary of {placeholder_name: value}
    
    Returns:
        str: Formatted facts text
    """
    if not facts_by_name:
        return "No information provided yet."
    
    lines = []
    for name, value in sorted(facts_by_name.items()):
        lines.append(f"• {name}: {value}")
    
    return "\n".join(lines)


def format_facts_for_prompt(facts_by_name):
    """
    Format facts overlay for injection into LLM prompts
    
    Args:
        facts_by_name: Dictionary of {placeholder_name: value}
    
    Returns:
        str: Formatted facts text
    """
    if not facts_by_name:
        return "(None)"
    
    lines = []
    for name, value in sorted(facts_by_name.items()):
        lines.append(f"{name}: {value}")
    
    return "\n".join(lines)


def safe_titlecase(text):
    """
    Safe title-casing that preserves certain patterns
    NOT USED for legal_name normalization, only for display
    
    Args:
        text: Input text
    
    Returns:
        str: Title-cased text with exceptions
    """
    # Patterns to preserve (all caps)
    preserve_patterns = ['LLC', 'LLP', 'LP', 'INC', 'CORP', 'LTD', 'USA', 'US', 'UK']
    
    # Simple titlecase
    result = text.title()
    
    # Restore preserved patterns
    for pattern in preserve_patterns:
        # Case-insensitive replacement
        result = re.sub(rf'\b{pattern}\b', pattern, result, flags=re.IGNORECASE)
    
    return result


def is_obvious_placeholder(text):
    """
    Check if text looks like an unfilled placeholder
    
    Args:
        text: Input text
    
    Returns:
        bool: True if text looks like a placeholder
    """
    text_upper = text.upper()
    
    # Check for brackets/braces
    if '[' in text or '{' in text or ']' in text or '}' in text:
        return True
    
    # Check for common placeholder strings
    bad_strings = ['TODO', 'XXX', 'TBD', 'FIXME', 'CHANGEME', 'PLACEHOLDER', 'YOUR NAME', 'ENTER']
    for bad in bad_strings:
        if bad in text_upper:
            return True
    
    # Check for underscore patterns (e.g., "___")
    if '___' in text or '...' in text:
        return True
    
    return False


def truncate_text(text, max_length=100, suffix='...'):
    """
    Truncate text to max length with suffix
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename):
    """
    Sanitize a filename by removing/replacing unsafe characters
    
    Args:
        filename: Input filename
    
    Returns:
        str: Sanitized filename
    """
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:190] + ext
    
    return filename

