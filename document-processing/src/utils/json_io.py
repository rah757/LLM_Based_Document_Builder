"""
JSON I/O utilities
Handles atomic loading and saving of per-reference JSON files
"""

import json
import os
import tempfile
import shutil


def load_reference_json(ref_folder):
    """
    Load the placeholders JSON for a reference
    
    Args:
        ref_folder: Path to the reference folder
    
    Returns:
        dict: Loaded JSON data, or None if not found
    """
    # Find the JSON file (should be only one *_placeholders.json)
    json_files = [f for f in os.listdir(ref_folder) if f.endswith('_placeholders.json')]
    
    if not json_files:
        return None
    
    json_path = os.path.join(ref_folder, json_files[0])
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON from {json_path}: {str(e)}")
        return None


def save_reference_json(ref_folder, data):
    """
    Atomically save the placeholders JSON for a reference
    Uses temp file + rename for atomic write
    
    Args:
        ref_folder: Path to the reference folder
        data: Dictionary to save
    
    Returns:
        bool: True if successful
    """
    # Find the JSON file name
    json_files = [f for f in os.listdir(ref_folder) if f.endswith('_placeholders.json')]
    
    if not json_files:
        print(f"No JSON file found in {ref_folder}")
        return False
    
    json_path = os.path.join(ref_folder, json_files[0])
    
    try:
        # Write to temp file first
        temp_fd, temp_path = tempfile.mkstemp(dir=ref_folder, suffix='.json')
        
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        shutil.move(temp_path, json_path)
        
        return True
    except Exception as e:
        print(f"Error saving JSON to {json_path}: {str(e)}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False


def get_placeholder_by_id(data, placeholder_id):
    """
    Get a specific placeholder from JSON data
    
    Args:
        data: JSON data dictionary
        placeholder_id: Placeholder ID to find
    
    Returns:
        dict: Placeholder dictionary, or None if not found
    """
    placeholders = data.get('placeholders', [])
    
    for placeholder in placeholders:
        if placeholder.get('placeholder_id') == placeholder_id:
            return placeholder
    
    return None


def update_facts_overlay(data, placeholder_id, placeholder_name, value):
    """
    Update facts_overlay with a new value (by both ID and name)
    Only stores if value is not a placeholder pattern
    
    Args:
        data: JSON data dictionary (modified in place)
        placeholder_id: Placeholder ID
        placeholder_name: Placeholder name
        value: Normalized value to store
    """
    from utils.format_utils import is_obvious_placeholder
    import re
    
    # Don't store if the value looks like a placeholder
    if is_obvious_placeholder(value):
        print(f"Warning: Not storing placeholder pattern '{value}' in facts overlay")
        return
    
    # Check additional placeholder patterns
    placeholder_patterns = [
        r'^\[.*\]$',           # [Something]
        r'^\{\{.*\}\}$',       # {{Something}}
        r'^\{.*\}$',           # {Something}
        r'^\[?[A-Z_\s]+\]?$',  # [ALL CAPS] or ALL_CAPS
        r'^placeholder_\d+$',  # placeholder_001
    ]
    
    for pattern in placeholder_patterns:
        if re.match(pattern, value.strip()):
            print(f"Warning: Value '{value}' looks like a placeholder, not storing in facts overlay")
            return
    
    # Update by ID (authoritative)
    if 'facts_overlay' not in data:
        data['facts_overlay'] = {}
    data['facts_overlay'][placeholder_id] = value
    
    # Update by name (suggestion pool)
    if 'facts_overlay_by_name' not in data:
        data['facts_overlay_by_name'] = {}
    data['facts_overlay_by_name'][placeholder_name] = value


def remove_from_facts_overlay(data, placeholder_id, placeholder_name):
    """
    Remove a placeholder from facts_overlay (for undo)
    
    Args:
        data: JSON data dictionary (modified in place)
        placeholder_id: Placeholder ID
        placeholder_name: Placeholder name
    """
    if 'facts_overlay' in data:
        data['facts_overlay'].pop(placeholder_id, None)
    
    if 'facts_overlay_by_name' in data:
        data['facts_overlay_by_name'].pop(placeholder_name, None)

