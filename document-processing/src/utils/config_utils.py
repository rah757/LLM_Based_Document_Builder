"""
Configuration loading utilities
Loads models, type mappings, validation rules, and other config files
"""

import os
import json


def get_config_path(filename):
    """Get absolute path to a config file"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, 'config', filename)


def load_models_config():
    """
    Load models configuration from config/models.json
    
    Returns:
        dict: Models configuration with defaults
    """
    config_path = get_config_path('models.json')
    
    defaults = {
        "qa_model": "gpt-4o-mini",
        "validation_model": "gpt-5-nano",
        "embeddings_backend": "none",
        "rag_top_k": 4,
        "max_document_chars": 200000,
        "max_validation_retries": 2,
        "context_window_words": 20
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults
                return {**defaults, **config}
        return defaults
    except Exception as e:
        print(f"Error loading models config: {str(e)}")
        return defaults


def load_type_map_config():
    """
    Load expected type mappings from config/expected_type_map.json
    
    Returns:
        dict: Type mappings with keywords, descriptions, examples
    """
    config_path = get_config_path('expected_type_map.json')
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"types": {}, "fallback_order": []}
    except Exception as e:
        print(f"Error loading type map config: {str(e)}")
        return {"types": {}, "fallback_order": []}


def load_validation_rules_config():
    """
    Load validation rules from config/validation_rules.json
    
    Returns:
        dict: Validation rules per type with regex patterns and normalization
    """
    config_path = get_config_path('validation_rules.json')
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading validation rules config: {str(e)}")
        return {}


def load_placeholder_patterns_config():
    """
    Load placeholder patterns from config/placeholder_patterns.json
    
    Returns:
        dict: Placeholder regex patterns and context settings
    """
    config_path = get_config_path('placeholder_patterns.json')
    
    defaults = {
        "patterns": [
            {
                "name": "square_brackets",
                "regex": "\\[([A-Za-z0-9\\s_\\-]+)\\]",
                "enabled": True
            }
        ],
        "context_words_count": 20
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return defaults
    except Exception as e:
        print(f"Error loading placeholder patterns config: {str(e)}")
        return defaults


def get_model_from_env(model_type, default_model):
    """
    Get model name from environment variable or use default
    
    Args:
        model_type: Type of model ('qa' or 'validation')
        default_model: Default model name from config
    
    Returns:
        str: Model name to use
    """
    env_var_map = {
        'qa': 'OPENAI_MODEL_QA',
        'validation': 'OPENAI_MODEL_VALIDATOR'
    }
    
    env_var = env_var_map.get(model_type)
    if env_var:
        return os.getenv(env_var, default_model)
    return default_model

