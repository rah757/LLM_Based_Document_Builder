"""
Simplified validation - LLM-only, no local validation
Much more lenient, extracts exact values without embellishment
"""

import json
from utils.number_parser import parse_number_input, format_money


def validate_with_llm_v2(user_input, placeholder, document_summary, openai_client, model):
    """
    Validate input using LLM (GPT-5-nano) - lenient and smart
    
    Args:
        user_input: User's input
        placeholder: Placeholder dictionary
        document_summary: Document summary
        openai_client: OpenAI client
        model: Validation model (GPT-5-nano)
    
    Returns:
        dict: {
            'validation': 'VALID' or 'INVALID',
            'extracted_value': str (if VALID),
            'hint': str (if INVALID)
        }
    """
    from utils.prompt_utils import load_prompt_template, render_prompt_template
    
    # Quick pre-filter: empty input
    if not user_input or not user_input.strip():
        return {
            'validation': 'INVALID',
            'extracted_value': None,
            'hint': 'Input cannot be empty'
        }
    
    # Load templates
    base_header = load_prompt_template('base_header.txt')
    try:
        validation_template = load_prompt_template('validation_checker_v2.txt')
    except:
        # Fallback to old template if new one doesn't exist yet
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
            max_tokens=150
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        result = json.loads(result_text)
        
        validation_status = result.get('validation', 'INVALID')
        extracted_value = result.get('extracted_value', user_input)
        hint = result.get('hint', '')
        
        return {
            'validation': validation_status,
            'extracted_value': extracted_value if validation_status == 'VALID' else None,
            'hint': hint
        }
        
    except Exception as e:
        print(f"Error in LLM validation: {str(e)}")
        print(f"Response was: {result_text if 'result_text' in locals() else 'N/A'}")
        
        # Fallback: Be permissive
        return {
            'validation': 'VALID',
            'extracted_value': user_input.strip(),
            'hint': ''
        }


def normalize_value_v2(extracted_value, expected_type):
    """
    Normalize extracted value to canonical format
    Much simpler than before - trusts LLM extraction
    
    Args:
        extracted_value: Value extracted by LLM
        expected_type: Expected type
    
    Returns:
        str: Normalized value
    """
    if not extracted_value:
        return ''
    
    extracted_value = extracted_value.strip()
    
    # For monetary values, try smart number parsing
    if expected_type == 'monetary_value':
        success, parsed_value, error = parse_number_input(extracted_value)
        if success:
            return format_money(parsed_value)
        # If parsing fails, just return as-is
        return extracted_value
    
    # For dates, try to parse (simple)
    if expected_type == 'date':
        try:
            from dateutil import parser as dateutil_parser
            parsed_date = dateutil_parser.parse(extracted_value, fuzzy=False)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            # If fails, return as-is
            return extracted_value
    
    # For email, lowercase
    if expected_type == 'email':
        return extracted_value.lower()
    
    # For everything else, return as-is (trust LLM extraction)
    return extracted_value

