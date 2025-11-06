"""
Smart number parsing for monetary values
Handles: 1000, 1 million, 1m, 1.5M, etc.
"""

import re
from decimal import Decimal


def parse_number_input(user_input):
    """
    Parse user input into a numerical value
    Handles various formats: 1000, 1 million, 1m, 1.5M, $50k, etc.
    
    Args:
        user_input: User's input string
    
    Returns:
        tuple: (success: bool, value: Decimal or None, error: str or None)
    """
    user_input = user_input.strip().lower()
    
    # Remove dollar signs and commas
    user_input = user_input.replace('$', '').replace(',', '').strip()
    
    # Check for multipliers
    multipliers = {
        'k': 1_000,
        'thousand': 1_000,
        'm': 1_000_000,
        'million': 1_000_000,
        'b': 1_000_000_000,
        'billion': 1_000_000_000
    }
    
    # Try to extract number with multiplier
    # Patterns: "1.5m", "1 million", "50k", "1.5 million"
    pattern = r'([\d.]+)\s*(k|thousand|m|million|b|billion)?'
    match = re.match(pattern, user_input)
    
    if match:
        try:
            number_part = match.group(1)
            multiplier_part = match.group(2)
            
            base_value = Decimal(number_part)
            
            if multiplier_part and multiplier_part in multipliers:
                final_value = base_value * multipliers[multiplier_part]
            else:
                final_value = base_value
            
            return (True, final_value, None)
            
        except Exception as e:
            return (False, None, f'Could not parse "{user_input}" as a number')
    
    # If no match, try basic decimal parse
    try:
        value = Decimal(user_input)
        return (True, value, None)
    except:
        return (False, None, f'"{user_input}" is not a valid number')


def format_money(value):
    """
    Format a monetary value for storage
    
    Args:
        value: Decimal value
    
    Returns:
        str: Formatted as "1000000.00"
    """
    return f"{value:.2f}"

