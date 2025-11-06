"""
File handling utilities for document processing
Handles reference number generation, folder creation, and file operations
"""

import os


def get_next_reference_number(counter_file):
    """
    Get the next reference number for uploads
    
    Args:
        counter_file: Path to the counter file
    
    Returns:
        int: Next reference number
    """
    if not os.path.exists(counter_file):
        with open(counter_file, 'w') as f:
            f.write('0')
        return 1
    
    with open(counter_file, 'r') as f:
        current = int(f.read().strip() or '0')
    
    next_num = current + 1
    
    with open(counter_file, 'w') as f:
        f.write(str(next_num))
    
    return next_num


def create_reference_folder(base_folder, ref_number):
    """
    Create folder structure for a reference number
    
    Args:
        base_folder: Base uploads folder
        ref_number: Reference number
    
    Returns:
        str: Path to the reference folder
    """
    ref_folder = os.path.join(base_folder, str(ref_number))
    os.makedirs(ref_folder, exist_ok=True)
    
    # Create embeddings subfolder for future RAG use
    embeddings_folder = os.path.join(ref_folder, 'embeddings')
    os.makedirs(embeddings_folder, exist_ok=True)
    
    return ref_folder

