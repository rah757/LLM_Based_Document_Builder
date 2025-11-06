"""
LLM-based type inference using GPT-5-nano
Much smarter than regex - understands context
"""

import json


def infer_type_with_llm(placeholder_name, context_before, context_after, document_summary, openai_client, model):
    """
    Use LLM to infer the expected type for a placeholder
    
    Args:
        placeholder_name: Name of the placeholder
        context_before: Text before placeholder
        context_after: Text after placeholder  
        document_summary: Document summary for additional context
        openai_client: OpenAI client
        model: Model to use (GPT-5-nano)
    
    Returns:
        str: Expected type (legal_name, date, monetary_value, email, address, jurisdiction, numeric, text)
    """
    
    prompt = f"""You are analyzing a legal document placeholder to determine what type of value it expects.

Document type: SAFE Agreement

Placeholder name: {placeholder_name}

Context BEFORE the placeholder:
{context_before[-200:] if len(context_before) > 200 else context_before}

Context AFTER the placeholder:
{context_after[:200] if len(context_after) > 200 else context_after}

Based on the context, what type of value should go here?

Available types:
- legal_name: Company or person name (e.g., "Acme Inc.", "John Smith")
- date: Calendar date (e.g., "2025-05-15", "May 5, 2025")
- monetary_value: Dollar amount (e.g., "1000000", "$1,000,000")
- email: Email address
- address: Physical/mailing address
- jurisdiction: US state or legal jurisdiction (e.g., "Delaware", "California")
- numeric: Plain number (shares, quantity, etc.)
- text: Free text or anything else

Respond with ONLY the type name, nothing else. Be smart - if context shows "$" before the placeholder, it's monetary_value even if the placeholder name is unclear.

Type:"""

    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=20
        )
        
        inferred_type = response.choices[0].message.content.strip().lower()
        
        # Validate it's a known type
        valid_types = ['legal_name', 'date', 'monetary_value', 'email', 'address', 'jurisdiction', 'numeric', 'text']
        if inferred_type in valid_types:
            return inferred_type
        
        # Fallback
        return 'text'
        
    except Exception as e:
        print(f"Error in LLM type inference: {str(e)}")
        return 'text'


def enrich_placeholders_with_llm_types(placeholders, document_summary, openai_client, model):
    """
    Enrich all placeholders with LLM-inferred types
    
    Args:
        placeholders: List of placeholder dictionaries
        document_summary: Document summary
        openai_client: OpenAI client
        model: GPT-5-nano model
    
    Returns:
        list: Placeholders with expected_type and priority
    """
    for placeholder in placeholders:
        expected_type = infer_type_with_llm(
            placeholder['placeholder_name'],
            placeholder['context_before'],
            placeholder['context_after'],
            document_summary,
            openai_client,
            model
        )
        
        placeholder['expected_type'] = expected_type
        placeholder['priority'] = assign_priority(expected_type)
    
    return placeholders


def assign_priority(expected_type):
    """
    Assign priority tier based on expected type
    
    Args:
        expected_type: The inferred type
    
    Returns:
        int: Priority (0=entities, 1=date/money, 2=other)
    """
    priority_map = {
        # Tier 0: Entities (legal names)
        'legal_name': 0,
        
        # Tier 1: Critical values
        'date': 1,
        'monetary_value': 1,
        
        # Tier 2: Other
        'email': 2,
        'address': 2,
        'jurisdiction': 2,
        'numeric': 2,
        'text': 2
    }
    
    return priority_map.get(expected_type, 2)

