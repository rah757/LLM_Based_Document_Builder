"""
Input validation and normalization utilities
Handles placeholder type detection and input validation
"""

import re
import json
from dateutil import parser as dateutil_parser
from decimal import Decimal, InvalidOperation
from utils.format_utils import is_obvious_placeholder


def validate_local(user_input, expected_type):
    """
    Minimal local pre-filter validation
    Only catches obvious errors before sending to LLM
    
    Args:
        user_input: The user's input string
        expected_type: Expected type
    
    Returns:
        dict: {'valid': bool, 'error': str or None}
    """
    user_input = user_input.strip()
    
    # Empty check
    if not user_input:
        return {'valid': False, 'error': 'Input cannot be empty'}
    
    # Length check (minimum 1 character)
    if len(user_input) < 1:
        return {'valid': False, 'error': 'Input too short'}
    
    # Check for obvious placeholders like [XXX], {{{}}}, etc.
    if is_obvious_placeholder(user_input):
        return {'valid': False, 'error': 'Input appears to be a placeholder, not actual data'}
    
    # Pass everything else to LLM validation
    return {'valid': True, 'error': None}


def validate_date(user_input):
    """Validate date input using dateutil"""
    try:
        # Try parsing with dateutil (handles many formats)
        parsed_date = dateutil_parser.parse(user_input, fuzzy=False)
        return {'valid': True, 'error': None}
    except (ValueError, TypeError):
        return {'valid': False, 'error': 'Invalid date format'}


def validate_monetary_value(user_input):
    """Validate monetary value"""
    # Remove common formatting
    cleaned = user_input.replace('$', '').replace(',', '').replace(' ', '').strip()
    
    # Check if it's a valid number
    try:
        value = float(cleaned)
        if value < 0:
            return {'valid': False, 'error': 'Amount cannot be negative'}
        return {'valid': True, 'error': None}
    except ValueError:
        return {'valid': False, 'error': 'Invalid monetary value'}


def validate_email(user_input):
    """Validate email with simple regex"""
    email_pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    if re.match(email_pattern, user_input.strip()):
        return {'valid': True, 'error': None}
    return {'valid': False, 'error': 'Invalid email format'}


def validate_text_type(user_input):
    """Validate text/legal_name/jurisdiction types with sanity checks"""
    user_input = user_input.strip()
    
    # Length check
    if len(user_input) < 3:
        return {'valid': False, 'error': 'Input too short (minimum 3 characters)'}
    
    # Must contain at least one letter
    if not any(c.isalpha() for c in user_input):
        return {'valid': False, 'error': 'Input must contain at least one letter'}
    
    # Check for obvious placeholders
    if is_obvious_placeholder(user_input):
        return {'valid': False, 'error': 'Input appears to be a placeholder, not actual data'}
    
    return {'valid': True, 'error': None}


def normalize_value(user_input, expected_type):
    """
    Normalize validated input to canonical format
    
    Args:
        user_input: The validated input string
        expected_type: Expected type
    
    Returns:
        str: Normalized value
    """
    user_input = user_input.strip()
    
    if expected_type == 'date':
        return normalize_date(user_input)
    elif expected_type == 'monetary_value':
        return normalize_monetary_value(user_input)
    elif expected_type == 'email':
        return user_input.lower()
    elif expected_type == 'legal_name':
        # Do NOT normalize legal names - keep exact input
        return user_input
    elif expected_type == 'jurisdiction':
        # Keep as-is
        return user_input
    else:
        return user_input


def normalize_date(user_input):
    """Normalize date to YYYY-MM-DD"""
    try:
        parsed_date = dateutil_parser.parse(user_input, fuzzy=False)
        return parsed_date.strftime('%Y-%m-%d')
    except:
        return user_input  # Fallback


def normalize_monetary_value(user_input):
    """Normalize money to decimal format without symbol"""
    # Remove formatting
    cleaned = user_input.replace('$', '').replace(',', '').replace(' ', '').strip()
    
    try:
        value = Decimal(cleaned)
        # Format to 2 decimal places
        return f"{value:.2f}"
    except (ValueError, InvalidOperation):
        return user_input  # Fallback


def validate_with_llm(user_input, placeholder, document_summary, openai_client, model):
    """
    Validate input using LLM (gpt-5-nano)
    
    Args:
        user_input: User's input
        placeholder: Placeholder dictionary
        document_summary: Document summary
        openai_client: OpenAI client
        model: Validation model
    
    Returns:
        dict: {'validation': 'VALID' or 'INVALID', 'hint': str}
    """
    from utils.prompt_utils import load_prompt_template, render_prompt_template
    
    # Load templates
    base_header = load_prompt_template('base_header.txt')
    validation_template = load_prompt_template('validation_checker.txt')
    
    # Render prompt
    prompt = render_prompt_template(
        validation_template,
        base_header=base_header,
        placeholder_name=placeholder['placeholder_name'],
        expected_type=placeholder.get('expected_type', 'text'),
        user_input=user_input,
        context_before=placeholder['context_before'],
        context_after=placeholder['context_after']
    )
    
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        result = json.loads(result_text)
        
        return {
            'validation': result.get('validation', 'INVALID'),
            'hint': result.get('hint', 'Invalid input')
        }
    except Exception as e:
        print(f"Error in LLM validation: {str(e)}")
        # Fallback
        return {
            'validation': 'INVALID',
            'hint': f'Input must match expected type: {placeholder.get("expected_type", "text")}'
        }

