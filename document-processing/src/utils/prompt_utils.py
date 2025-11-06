"""
Prompt generation and caching utilities
Handles question generation with hash-based caching
"""

import hashlib
import os
from datetime import datetime


def load_prompt_template(template_name):
    """
    Load a prompt template from src/prompts/
    
    Args:
        template_name: Name of the template file (e.g., 'question_builder.txt')
    
    Returns:
        str: Template content
    """
    prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts')
    template_path = os.path.join(prompts_dir, template_name)
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading template {template_name}: {str(e)}")
        return ""


def compute_prompt_hash(document_summary, placeholder_name, expected_type, context_before, context_after):
    """
    Compute SHA256 hash for prompt caching
    
    Args:
        document_summary: Document summary text
        placeholder_name: Placeholder name
        expected_type: Expected type
        context_before: Context before placeholder
        context_after: Context after placeholder
    
    Returns:
        str: SHA256 hash hex string
    """
    hash_input = f"{document_summary}{placeholder_name}{expected_type}{context_before}{context_after}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def render_prompt_template(template_content, **kwargs):
    """
    Simple template rendering using {{ variable }} syntax
    
    Args:
        template_content: Template string
        **kwargs: Variables to inject
    
    Returns:
        str: Rendered template
    """
    result = template_content
    for key, value in kwargs.items():
        placeholder = f"{{{{ {key} }}}}"
        result = result.replace(placeholder, str(value))
    return result


def generate_question_prompt(placeholder, document_summary, facts_overlay_by_name, openai_client, model):
    """
    Generate a question prompt for a placeholder using LLM
    
    Args:
        placeholder: Placeholder dictionary
        document_summary: Document summary
        facts_overlay_by_name: Facts overlay keyed by name
        openai_client: OpenAI client
        model: Model to use (qa_model)
    
    Returns:
        str: Generated question text
    """
    # Load templates
    base_header = load_prompt_template('base_header.txt')
    question_template = load_prompt_template('question_builder.txt')
    
    # Format facts overlay
    facts_text = format_facts_overlay(facts_overlay_by_name)
    
    # Render template
    prompt = render_prompt_template(
        question_template,
        base_header=base_header,
        document_summary=document_summary,
        placeholder_name=placeholder['placeholder_name'],
        expected_type=placeholder['expected_type'],
        context_before=placeholder['context_before'],
        context_after=placeholder['context_after'],
        facts_overlay_text=facts_text
    )
    
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating question: {str(e)}")
        return f"Please provide the {placeholder['placeholder_name']}."


def format_facts_overlay(facts_by_name):
    """
    Format facts overlay as readable text for injection into prompts
    
    Args:
        facts_by_name: Dictionary of {placeholder_name: value}
    
    Returns:
        str: Formatted facts text
    """
    if not facts_by_name:
        return "No information filled yet."
    
    lines = []
    for name, value in facts_by_name.items():
        lines.append(f"{name}: {value}")
    
    return "\n".join(lines)


def update_prompt_cache(placeholder, document_summary, openai_client, model, facts_overlay_by_name=None):
    """
    Update prompt_text and prompt_meta for a placeholder if hash changed
    
    Args:
        placeholder: Placeholder dictionary (will be modified in place)
        document_summary: Document summary
        openai_client: OpenAI client
        model: Model to use
        facts_overlay_by_name: Optional facts overlay (injected at LLM call, not in hash)
    
    Returns:
        bool: True if prompt was regenerated
    """
    if facts_overlay_by_name is None:
        facts_overlay_by_name = {}
    
    # Compute current hash (facts NOT included - static caching)
    current_hash = compute_prompt_hash(
        document_summary,
        placeholder['placeholder_name'],
        placeholder.get('expected_type', 'text'),
        placeholder['context_before'],
        placeholder['context_after']
    )
    
    # Check if regeneration needed
    stored_hash = placeholder.get('prompt_meta', {}).get('generated_from_hash')
    
    if stored_hash == current_hash and placeholder.get('prompt_text'):
        return False  # Cache hit
    
    # Generate new prompt
    # Facts are injected at LLM call time but NOT part of the hash
    prompt_text = generate_question_prompt(
        placeholder, 
        document_summary, 
        facts_overlay_by_name,  # Inject current facts into LLM call
        openai_client, 
        model
    )
    
    # Update metadata
    placeholder['prompt_text'] = prompt_text
    placeholder['prompt_meta'] = {
        'generated_from_hash': current_hash,
        'model': model,
        'timestamp': datetime.now().isoformat()
    }
    
    return True  # Cache miss, regenerated

