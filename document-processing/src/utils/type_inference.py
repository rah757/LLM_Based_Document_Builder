"""
Type inference utilities
Infers expected_type and priority for placeholders based on keywords and context
"""

import re


def infer_expected_type(placeholder_name, context_before, context_after, type_map_config):
    """
    Infer the expected type for a placeholder using keyword matching and regex signals
    
    Args:
        placeholder_name: Name of the placeholder
        context_before: Text before the placeholder
        context_after: Text after the placeholder
        type_map_config: Type mapping configuration from expected_type_map.json
    
    Returns:
        str: Expected type (legal_name, date, monetary_value, etc.)
    """
    placeholder_lower = placeholder_name.lower()
    combined_context = (context_before + " " + context_after).lower()
    
    types_config = type_map_config.get('types', {})
    fallback_order = type_map_config.get('fallback_order', [])
    
    # Step 1: Keyword matching in placeholder name
    for type_name in fallback_order:
        type_info = types_config.get(type_name, {})
        keywords = type_info.get('keywords', [])
        
        for keyword in keywords:
            if keyword in placeholder_lower:
                return type_name
    
    # Step 2: Regex signals in context
    # Date patterns
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    if re.search(date_pattern, combined_context):
        return 'date'
    
    # Money patterns
    money_pattern = r'(\$|USD)\s?\d[\d,]*(\.\d{1,2})?'
    if re.search(money_pattern, combined_context):
        return 'monetary_value'
    
    # Email patterns
    email_pattern = r'[^@\s]+@[^@\s]+\.[^@\s]+'
    if re.search(email_pattern, combined_context):
        return 'email'
    
    # Step 3: Default fallback
    return 'text'


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


def enrich_placeholders_with_types(placeholders, type_map_config):
    """
    Enrich all placeholders with expected_type and priority
    
    Args:
        placeholders: List of placeholder dictionaries
        type_map_config: Type mapping configuration
    
    Returns:
        list: Placeholders with expected_type and priority set
    """
    for placeholder in placeholders:
        expected_type = infer_expected_type(
            placeholder['placeholder_name'],
            placeholder['context_before'],
            placeholder['context_after'],
            type_map_config
        )
        
        placeholder['expected_type'] = expected_type
        placeholder['priority'] = assign_priority(expected_type)
    
    return placeholders

