"""
Logging utilities
Handles JSONL logging to actions.log per reference
"""

import json
import os
from datetime import datetime


def log_action(ref_folder, action_type, placeholder_id=None, status=None, model=None, latency_ms=None, **extra):
    """
    Append a JSONL entry to actions.log
    
    Args:
        ref_folder: Path to reference folder
        action_type: Action type (e.g., 'prompt_generated', 'validated_local', 'auto_filled')
        placeholder_id: Optional placeholder ID
        status: Optional status
        model: Optional model name used
        latency_ms: Optional latency in milliseconds
        **extra: Additional fields to log
    
    Returns:
        bool: True if successful
    """
    log_path = os.path.join(ref_folder, 'actions.log')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action_type
    }
    
    if placeholder_id:
        log_entry['placeholder_id'] = placeholder_id
    if status:
        log_entry['status'] = status
    if model:
        log_entry['model'] = model
    if latency_ms is not None:
        log_entry['latency_ms'] = latency_ms
    
    # Add any extra fields
    log_entry.update(extra)
    
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
        return True
    except Exception as e:
        print(f"Error writing to actions.log: {str(e)}")
        return False


def read_actions_log(ref_folder, limit=None):
    """
    Read actions from log (for debugging/admin)
    
    Args:
        ref_folder: Path to reference folder
        limit: Optional maximum number of entries to return (most recent)
    
    Returns:
        list: List of log entry dictionaries
    """
    log_path = os.path.join(ref_folder, 'actions.log')
    
    if not os.path.exists(log_path):
        return []
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        entries = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        if limit:
            return entries[-limit:]
        return entries
    except Exception as e:
        print(f"Error reading actions.log: {str(e)}")
        return []

