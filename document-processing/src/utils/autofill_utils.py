"""
Auto-fill utilities
Handles AI-powered auto-suggestion for placeholders after validation failures
"""

from utils.prompt_utils import load_prompt_template, render_prompt_template
from utils.format_utils import format_facts_for_prompt


def auto_suggest_value(placeholder, document_summary, facts_overlay_by_name, openai_client, model):
    """
    Use LLM to auto-suggest a plausible value based on context
    
    Args:
        placeholder: Placeholder dictionary
        document_summary: Document summary
        facts_overlay_by_name: Facts already filled
        openai_client: OpenAI client
        model: QA model (gpt-4o-mini)
    
    Returns:
        str: Suggested value
    """
    expected_type = placeholder.get('expected_type', 'text')
    placeholder_name = placeholder['placeholder_name']
    context_before = placeholder['context_before']
    context_after = placeholder['context_after']
    prompt_text = placeholder.get('prompt_text', f"Please provide {placeholder_name}")
    
    # Get previous user attempts if available
    user_input_raw = placeholder.get('user_input_raw')
    attempts_context = ""
    if user_input_raw and user_input_raw != '(auto)':
        attempts_context = f"\n\nUser's previous attempt: \"{user_input_raw}\"\n(This was rejected, but might contain useful hints about what the value should be. Extract any useful information from it.)\n"
    
    # Format facts
    facts_text = format_facts_for_prompt(facts_overlay_by_name)
    
    # Build auto-suggest prompt - use the question we asked the user!
    prompt = f"""You are helping fill in a legal document. The user was asked this question but couldn't answer it:

QUESTION: {prompt_text}
{attempts_context}
Based on the context below, suggest a REALISTIC and PLAUSIBLE value. DO NOT return placeholders like [Company Name] or {{Name}}.

CRITICAL PRIORITY RULES (READ CAREFULLY):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. IF the user's previous attempt contains a specific name/value (even with "i think", "maybe", typos):
   → EXTRACT and USE that value IMMEDIATELY
   → Example: "i think its Apple inc" → Return "Apple Inc."
   → DO NOT use facts from other fields or document context instead

2. The "Facts already filled" section below shows OTHER fields already filled.
   → These are for REFERENCE ONLY
   → DO NOT copy values from other fields unless user's attempt is completely useless

3. Only if user's attempt has NO useful info (like "idk", "no idea"):
   → Then use document context to suggest a value
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Document Summary:
{document_summary}

Facts already filled (OTHER fields - for reference only):
{facts_text}

Placeholder field we're filling NOW: {placeholder_name}
Expected type: {expected_type}

Context from document:
BEFORE: ...{context_before[-200:] if len(context_before) > 200 else context_before}
AFTER: {context_after[:200] if len(context_after) > 200 else context_after}...

FORMAT GUIDELINES:
- Provide ONLY a realistic value, no explanation
- DO NOT return placeholders like [Company Name], {{{{Name}}}}, [PLACEHOLDER], etc.
- Match the expected type:
  - date: YYYY-MM-DD format (e.g., 2025-05-15)
  - monetary_value: numeric only (e.g., 50000 or 1000000)
  - email: valid email (e.g., legal@company.com)
  - legal_name: realistic company name (e.g., "Acme Corporation Inc.")
  - jurisdiction: US state name (e.g., "Delaware")

Suggested value (extract from user's attempt if present):"""

    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=50
        )
        
        suggested = response.choices[0].message.content.strip()
        
        # Remove quotes if present
        suggested = suggested.strip('"\'')
        
        # Check if it's still a placeholder pattern
        if is_placeholder_pattern(suggested):
            print(f"Warning: LLM returned a placeholder: {suggested}")
            return get_default_value(expected_type, placeholder_name)
        
        # If unknown or empty
        if not suggested or len(suggested) < 2:
            return get_default_value(expected_type, placeholder_name)
        
        return suggested
        
    except Exception as e:
        print(f"Error in auto-suggest: {str(e)}")
        return get_default_value(expected_type, placeholder_name)


def is_placeholder_pattern(text):
    """Check if text looks like a placeholder"""
    import re
    
    # Check for common placeholder patterns
    patterns = [
        r'\[.*?\]',           # [Something]
        r'\{\{.*?\}\}',       # {{Something}}
        r'\{.*?\}',           # {Something}
        r'^\[?[A-Z_\s]+\]?$', # ALL_CAPS or [ALL CAPS]
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    
    return False


def get_default_value(expected_type, placeholder_name=''):
    """
    Get a reasonable default value for a type
    
    Args:
        expected_type: Type of placeholder
        placeholder_name: Name of the placeholder for context
    
    Returns:
        str: Default value (NEVER a placeholder pattern)
    """
    # Try to generate something based on placeholder name
    if expected_type == 'legal_name':
        # Use placeholder name if available
        if placeholder_name:
            # Clean up the name
            clean_name = placeholder_name.replace('_', ' ').replace('-', ' ').title()
            return f"{clean_name} Inc."
        return "Unknown Company Inc."
    
    defaults = {
        'date': '2025-01-01',
        'monetary_value': '10000.00',
        'email': 'contact@example.com',
        'jurisdiction': 'Delaware',
        'address': '123 Main Street, City, State 12345',
        'numeric': '1000',
        'text': 'To be determined'
    }
    
    return defaults.get(expected_type, 'Unknown')

