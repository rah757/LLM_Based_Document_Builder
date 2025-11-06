from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from docx import Document
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# Import modular utilities
from utils.file_utils import get_next_reference_number, create_reference_folder
from utils.placeholder_utils import extract_document_text, detect_placeholders, create_marked_document
from utils.summary_utils import generate_document_summary
from utils.config_utils import load_models_config, get_model_from_env, load_type_map_config
from utils.llm_type_inference import enrich_placeholders_with_llm_types
from utils.json_io import load_reference_json, save_reference_json, get_placeholder_by_id, update_facts_overlay
from utils.prompt_utils import update_prompt_cache
from utils.log_utils import log_action
from utils.validation_utils_v2 import validate_with_llm_v2, normalize_value_v2
from utils.autofill_utils import auto_suggest_value
from utils.doc_generation_utils import replace_placeholders_in_document, check_all_filled

# Load environment variables
doc_processing_root = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(doc_processing_root, '.env'))

# Load models configuration
models_config = load_models_config()
QA_MODEL = get_model_from_env('qa', models_config['qa_model'])
VALIDATION_MODEL = get_model_from_env('validation', models_config['validation_model'])

print(f"Loaded models - QA: {QA_MODEL}, Validation: {VALIDATION_MODEL}")

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
CONFIG_FOLDER = os.path.join(BASE_DIR, 'config')
PATTERNS_CONFIG_FILE = os.path.join(CONFIG_FOLDER, 'placeholder_patterns.json')
COUNTER_FILE = os.path.join(UPLOAD_FOLDER, '.counter.txt')
ALLOWED_EXTENSIONS = {'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)


def load_placeholder_patterns():
    """Load placeholder patterns from the configuration file"""
    try:
        if os.path.exists(PATTERNS_CONFIG_FILE):
            with open(PATTERNS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        else:
            return {
                "patterns": [
                    {
                        "name": "square_brackets",
                        "regex": "\\[([A-Za-z0-9\\s_\\-]+)\\]",
                        "enabled": True
                    }
                ],
                "context_words_count": 20
            }
    except Exception as e:
        print(f"Error loading patterns config: {str(e)}")
        return {"patterns": [], "context_words_count": 20}


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Serve the upload form"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_document():
    """
    Handle document upload and processing
    
    Returns:
        JSON response with document information and detected placeholders
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Generate reference number and create folder structure
            ref_number = get_next_reference_number(COUNTER_FILE)
            ref_folder = create_reference_folder(UPLOAD_FOLDER, ref_number)
            
            # Secure filename and prepare paths
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1]
            
            # Save original document
            original_filename = f"{base_name}_{timestamp}_original{ext}"
            original_filepath = os.path.join(ref_folder, original_filename)
            file.save(original_filepath)
            
            # Parse document and extract text
            doc = Document(original_filepath)
            full_document_text = extract_document_text(doc)
            
            # Truncate if exceeds max size
            max_chars = models_config.get('max_document_chars', 200000)
            document_text = full_document_text[:max_chars] if len(full_document_text) > max_chars else full_document_text
            
            # Load patterns config
            patterns_config = load_placeholder_patterns()
            
            # Generate document summary FIRST (needed for type inference)
            print("Generating document summary...")
            document_summary = generate_document_summary(document_text, openai_client, QA_MODEL)
            
            # Detect placeholders
            placeholders = detect_placeholders(document_text, patterns_config)
            
            # Type inference using LLM - much smarter than keyword matching
            if len(placeholders) > 0:
                print(f"Running LLM type inference for {len(placeholders)} placeholders...")
                placeholders = enrich_placeholders_with_llm_types(
                    placeholders,
                    document_summary,
                    openai_client,
                    VALIDATION_MODEL  # Use GPT-5-nano for type inference
                )
                print("Type inference complete")
            
            # Create marked document
            marked_filename = f"{base_name}_{timestamp}_placeholder_marked{ext}"
            marked_filepath = os.path.join(ref_folder, marked_filename)
            create_marked_document(original_filepath, placeholders, marked_filepath)
            
            # Prepare JSON output
            json_filename = f"{base_name}_{timestamp}_placeholders.json"
            json_filepath = os.path.join(ref_folder, json_filename)
            
            context_words_count = patterns_config.get('context_words_count', 20)
            placeholders_summary = [p['placeholder_name'] for p in placeholders]
            
            # Check if document was truncated
            max_chars = models_config.get('max_document_chars', 200000)
            was_truncated = len(document_text) > max_chars
            
            # Determine validation status
            if len(placeholders) == 0:
                validation_status = "no_placeholders"
            else:
                validation_status = "pending"
            
            # Extend each placeholder with Phase 2 fields
            # Note: expected_type and priority already set by type inference above
            for placeholder in placeholders:
                # Only add fields that weren't set by type inference
                if 'expected_type' not in placeholder:
                    placeholder['expected_type'] = None
                if 'priority' not in placeholder:
                    placeholder['priority'] = None
                    
                placeholder.update({
                    "prompt_text": None,
                    "prompt_meta": {
                        "generated_from_hash": None,
                        "model": None,
                        "timestamp": None
                    },
                    "status": "pending",
                    "user_input_raw": None,
                    "user_input": None,
                    "attempts": 0
                })
            
            placeholder_data = {
                "reference_number": ref_number,
                "original_document": original_filename,
                "marked_document": marked_filename,
                "upload_timestamp": timestamp,
                "document_text": document_text,
                "document_summary": document_summary,
                "context_policy": {
                    "before_words_default": context_words_count,
                    "after_words_default": context_words_count
                },
                "truncated": was_truncated,
                "facts_overlay": {},
                "facts_overlay_by_name": {},
                "validation_status": validation_status,
                "placeholders_summary": placeholders_summary,
                "total_placeholders": len(placeholders),
                "placeholders": placeholders
            }
            
            # Save JSON
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(placeholder_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Document processed with {len(placeholders)} placeholders")
            print(f"✓ Files saved in uploads/{ref_number}/")
            
            # Get first pending placeholder
            first_pending = next((p for p in placeholders if p['status'] == 'pending'), None)
            
            # Count by status
            pending_count = len([p for p in placeholders if p['status'] == 'pending'])
            
            # Return response
            response = {
                'success': True,
                'message': f'Document processed successfully. Found {len(placeholders)} placeholder(s).',
                'data': {
                    'reference_number': ref_number,
                    'original_document': original_filename,
                    'marked_document': marked_filename,
                    'json_file': json_filename,
                    'document_summary': document_summary,
                    'truncated': was_truncated,
                    'validation_status': validation_status,
                    'total_placeholders': len(placeholders),
                    'pending_count': pending_count,
                    'first_pending_id': first_pending['placeholder_id'] if first_pending else None,
                    'placeholders_summary': placeholders_summary
                }
            }
            
            return jsonify(response), 200
            
        except Exception as e:
            return jsonify({
                'error': f'Error processing document: {str(e)}'
            }), 500
    
    else:
        return jsonify({
            'error': 'Invalid file type. Only .docx files are allowed.'
        }), 400


@app.route('/download/<ref_number>/<filename>')
def download_file(ref_number, filename):
    """Download a processed document"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], ref_number, filename)
        if os.path.exists(filepath):
            # Proper MIME type for .docx files
            return send_file(
                filepath,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/placeholder-data/<ref_number>/<json_filename>')
def get_placeholder_data(ref_number, json_filename):
    """Retrieve placeholder data from JSON file"""
    try:
        json_filepath = os.path.join(app.config['UPLOAD_FOLDER'], ref_number, json_filename)
        if os.path.exists(json_filepath):
            with open(json_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data), 200
        else:
            return jsonify({'error': 'JSON file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/patterns', methods=['GET'])
def get_patterns():
    """Get the current placeholder patterns configuration"""
    try:
        config = load_placeholder_patterns()
        return jsonify({
            'success': True,
            'patterns': config.get('patterns', []),
            'context_words_count': config.get('context_words_count', 20),
            'config_file': PATTERNS_CONFIG_FILE
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/placeholders/<int:ref_number>', methods=['GET'])
def list_placeholders(ref_number):
    """
    List all placeholders for a reference with lazy prompt generation
    
    Args:
        ref_number: Reference number
    
    Returns:
        JSON with placeholders, progress, and document summary
    """
    try:
        # Load reference JSON
        ref_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(ref_number))
        
        if not os.path.exists(ref_folder):
            return jsonify({'error': f'Reference {ref_number} not found'}), 404
        
        data = load_reference_json(ref_folder)
        
        if not data:
            return jsonify({'error': 'Failed to load reference data'}), 500
        
        # Generate prompts for any placeholders with null prompt_text (lazy generation)
        document_summary = data.get('document_summary', '')
        facts_overlay_by_name = data.get('facts_overlay_by_name', {})
        placeholders = data.get('placeholders', [])
        
        prompts_generated = 0
        for placeholder in placeholders:
            if placeholder.get('prompt_text') is None:
                # Lazy prompt generation with caching
                was_generated = update_prompt_cache(
                    placeholder,
                    document_summary,
                    openai_client,
                    QA_MODEL
                )
                
                if was_generated:
                    prompts_generated += 1
                    
                    # Log prompt generation
                    log_action(
                        ref_folder,
                        'prompt_generated',
                        placeholder_id=placeholder['placeholder_id'],
                        model=QA_MODEL
                    )
        
        # Save JSON if prompts were generated
        if prompts_generated > 0:
            save_reference_json(ref_folder, data)
            print(f"✓ Generated {prompts_generated} prompts for reference {ref_number}")
        
        # Calculate progress
        status_counts = {
            'filled': 0,
            'auto_filled': 0,
            'pending': 0,
            'skipped': 0
        }
        
        for placeholder in placeholders:
            status = placeholder.get('status', 'pending')
            if status in status_counts:
                status_counts[status] += 1
        
        # Prepare response (return minimal placeholder info)
        simplified_placeholders = []
        for p in placeholders:
            simplified_placeholders.append({
                'placeholder_id': p['placeholder_id'],
                'placeholder_name': p['placeholder_name'],
                'expected_type': p.get('expected_type'),
                'priority': p.get('priority'),
                'status': p['status'],
                'prompt_text': p.get('prompt_text'),
                'attempts': p.get('attempts', 0),
                'user_input': p.get('user_input')
            })
        
        response = {
            'reference_number': ref_number,
            'document_summary': document_summary,
            'truncated': data.get('truncated', False),
            'validation_status': data.get('validation_status', 'pending'),
            'progress': {
                'filled': status_counts['filled'],
                'auto_filled': status_counts['auto_filled'],
                'pending': status_counts['pending'],
                'skipped': status_counts['skipped'],
                'total': len(placeholders)
            },
            'placeholders': simplified_placeholders
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/fill_placeholder/<int:ref_number>/<placeholder_id>', methods=['POST'])
def fill_placeholder(ref_number, placeholder_id):
    """
    Fill a placeholder with validation pipeline
    
    Args:
        ref_number: Reference number
        placeholder_id: Placeholder ID
    
    Body:
        {
            "user_input": "value",
            "consent_auto_suggest": false  (optional, default false)
        }
    
    Returns:
        JSON with status (accepted, rejected, offer_auto_suggest, auto_filled)
    """
    try:
        # Load reference JSON
        ref_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(ref_number))
        
        if not os.path.exists(ref_folder):
            return jsonify({'error': f'Reference {ref_number} not found'}), 404
        
        data = load_reference_json(ref_folder)
        
        if not data:
            return jsonify({'error': 'Failed to load reference data'}), 500
        
        # Get placeholder
        placeholder = get_placeholder_by_id(data, placeholder_id)
        
        if not placeholder:
            return jsonify({'error': f'Placeholder {placeholder_id} not found'}), 404
        
        # Parse request body
        body = request.get_json()
        if not body:
            return jsonify({'error': 'Request body required'}), 400
        
        user_input = body.get('user_input', '').strip()
        consent_auto_suggest = body.get('consent_auto_suggest', False)
        
        if not user_input:
            return jsonify({'error': 'user_input is required'}), 400
        
        # Increment attempts first
        placeholder['attempts'] = placeholder.get('attempts', 0) + 1
        current_attempts = placeholder['attempts']
        
        # Store user input history (keep FIRST meaningful attempt for auto-suggest context)
        if not placeholder.get('user_input_raw') or placeholder.get('user_input_raw') == '(auto)':
            # First attempt or no previous attempt - store this one
            placeholder['user_input_raw'] = user_input
        # If already has a value, keep it (the first attempt is usually most informative)
        
        # Get placeholder details
        expected_type = placeholder.get('expected_type', 'text')
        placeholder_name = placeholder['placeholder_name']
        document_summary = data.get('document_summary', '')
        facts_overlay_by_name = data.get('facts_overlay_by_name', {})
        
        # LLM-only validation (NO local validation - LLM is smarter)
        llm_result = validate_with_llm_v2(
            user_input,
            placeholder,
            document_summary,
            openai_client,
            VALIDATION_MODEL
        )
        
        log_action(ref_folder, 'validated_llm', placeholder_id=placeholder_id, 
                  status=llm_result['validation'], model=VALIDATION_MODEL)
        
        if llm_result['validation'] == 'VALID':
            # LLM validation passed - use extracted value (doesn't embellish)
            extracted_value = llm_result.get('extracted_value', user_input)
            normalized = normalize_value_v2(extracted_value, expected_type)
            
            # Update placeholder
            placeholder['user_input_raw'] = user_input
            placeholder['user_input'] = normalized
            placeholder['status'] = 'filled'
            placeholder['attempts'] = 0  # Reset attempts on success
            
            # Update facts overlay
            update_facts_overlay(data, placeholder_id, placeholder_name, normalized)
            
            # Save JSON
            save_reference_json(ref_folder, data)
            
            return jsonify({
                'status': 'accepted',
                'normalized_value': normalized
            }), 200
        
        # LLM validation failed
        # Check attempts threshold (FIXED: stop at exactly 2)
        if current_attempts < 2:
            # Not enough attempts yet, just reject with hint
            save_reference_json(ref_folder, data)
            
            return jsonify({
                'status': 'rejected',
                'hint': llm_result.get('hint', 'Invalid input'),
                'attempts': current_attempts
            }), 400
        
        # attempts == 2: Offer auto-suggest ONCE
        if not consent_auto_suggest:
            # First time at threshold, offer auto-suggest
            save_reference_json(ref_folder, data)
            
            return jsonify({
                'status': 'offer_auto_suggest',
                'message': 'We can auto-suggest a value based on the document. Proceed?',
                'attempts': current_attempts
            }), 200
        
        # User declined or attempts > 2: STOP offering, just reject
        if current_attempts > 2:
            save_reference_json(ref_folder, data)
            
            return jsonify({
                'status': 'rejected',
                'hint': llm_result.get('hint', 'Invalid input. Please try a different value.'),
                'attempts': current_attempts
            }), 400
        
        # Step: User consented to auto-suggest, perform auto-fill
        # user_input_raw already contains the first meaningful attempt (set earlier)
        # Don't overwrite it with the latest input
        
        suggested_value = auto_suggest_value(
            placeholder,
            document_summary,
            facts_overlay_by_name,
            openai_client,
            QA_MODEL
        )
        
        # Normalize the suggested value (using v2 - respects extracted values)
        normalized = normalize_value_v2(suggested_value, expected_type)
        
        # Update placeholder with auto-filled value
        placeholder['user_input'] = normalized
        placeholder['status'] = 'auto_filled'
        placeholder['attempts'] = 0  # Reset attempts
        
        # Update facts overlay
        update_facts_overlay(data, placeholder_id, placeholder_name, normalized)
        
        # Save JSON
        save_reference_json(ref_folder, data)
        
        # Log action
        log_action(ref_folder, 'auto_filled', placeholder_id=placeholder_id, model=QA_MODEL)
        
        return jsonify({
            'status': 'auto_filled',
            'value': normalized
        }), 200
        
    except Exception as e:
        print(f"Error in fill_placeholder: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/undo/<int:ref_number>/<placeholder_id>', methods=['POST'])
def undo_placeholder(ref_number, placeholder_id):
    """
    Undo/reset a placeholder back to pending state
    
    Args:
        ref_number: Reference number
        placeholder_id: Placeholder ID
    
    Returns:
        JSON with updated progress
    """
    try:
        # Load reference JSON
        ref_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(ref_number))
        
        if not os.path.exists(ref_folder):
            return jsonify({'error': f'Reference {ref_number} not found'}), 404
        
        data = load_reference_json(ref_folder)
        
        if not data:
            return jsonify({'error': 'Failed to load reference data'}), 500
        
        # Get placeholder
        placeholder = get_placeholder_by_id(data, placeholder_id)
        
        if not placeholder:
            return jsonify({'error': f'Placeholder {placeholder_id} not found'}), 404
        
        placeholder_name = placeholder['placeholder_name']
        
        # Reset placeholder fields
        placeholder['user_input_raw'] = None
        placeholder['user_input'] = None
        placeholder['status'] = 'pending'
        placeholder['attempts'] = 0
        
        # Remove from facts_overlay (by ID)
        if 'facts_overlay' in data and placeholder_id in data['facts_overlay']:
            del data['facts_overlay'][placeholder_id]
        
        # Check if any other placeholder with same name is filled
        other_filled = False
        for p in data.get('placeholders', []):
            if (p['placeholder_id'] != placeholder_id and 
                p['placeholder_name'] == placeholder_name and 
                p.get('status') in ['filled', 'auto_filled']):
                other_filled = True
                break
        
        # Only remove from facts_overlay_by_name if no other instance is filled
        if not other_filled:
            if 'facts_overlay_by_name' in data and placeholder_name in data['facts_overlay_by_name']:
                del data['facts_overlay_by_name'][placeholder_name]
        
        # Save JSON
        save_reference_json(ref_folder, data)
        
        # Log action
        log_action(ref_folder, 'undo', placeholder_id=placeholder_id)
        
        # Calculate updated progress
        status_counts = {
            'filled': 0,
            'auto_filled': 0,
            'pending': 0,
            'skipped': 0
        }
        
        for p in data.get('placeholders', []):
            status = p.get('status', 'pending')
            if status in status_counts:
                status_counts[status] += 1
        
        return jsonify({
            'success': True,
            'message': f'Placeholder {placeholder_id} reset to pending',
            'progress': {
                'filled': status_counts['filled'],
                'auto_filled': status_counts['auto_filled'],
                'pending': status_counts['pending'],
                'skipped': status_counts['skipped'],
                'total': len(data.get('placeholders', []))
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/status/<int:ref_number>', methods=['GET'])
def get_status(ref_number):
    """
    Get current status and progress for a reference
    
    Args:
        ref_number: Reference number
    
    Returns:
        JSON with progress, next pending ID, and ordered pending list
    """
    try:
        # Load reference JSON
        ref_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(ref_number))
        
        if not os.path.exists(ref_folder):
            return jsonify({'error': f'Reference {ref_number} not found'}), 404
        
        data = load_reference_json(ref_folder)
        
        if not data:
            return jsonify({'error': 'Failed to load reference data'}), 500
        
        placeholders = data.get('placeholders', [])
        
        # Calculate progress
        status_counts = {
            'filled': 0,
            'auto_filled': 0,
            'pending': 0,
            'skipped': 0
        }
        
        pending_ordered = []
        next_pending_id = None
        
        for p in placeholders:
            status = p.get('status', 'pending')
            if status in status_counts:
                status_counts[status] += 1
            
            # Collect pending IDs in document order
            if status == 'pending':
                pending_ordered.append(p['placeholder_id'])
                if next_pending_id is None:
                    next_pending_id = p['placeholder_id']
        
        return jsonify({
            'progress': {
                'filled': status_counts['filled'],
                'auto_filled': status_counts['auto_filled'],
                'pending': status_counts['pending'],
                'skipped': status_counts['skipped'],
                'total': len(placeholders)
            },
            'next_pending_id': next_pending_id,
            'pending_ordered': pending_ordered
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/preview/<int:ref_number>', methods=['GET'])
def preview_document(ref_number):
    """
    Get a JSON preview of all placeholders with their current values
    
    Args:
        ref_number: Reference number
    
    Returns:
        JSON preview with all placeholders and their statuses
    """
    try:
        # Load reference JSON
        ref_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(ref_number))
        
        if not os.path.exists(ref_folder):
            return jsonify({'error': f'Reference {ref_number} not found'}), 404
        
        data = load_reference_json(ref_folder)
        
        if not data:
            return jsonify({'error': 'Failed to load reference data'}), 500
        
        # Build preview list
        placeholders_preview = []
        
        for p in data.get('placeholders', []):
            placeholders_preview.append({
                'id': p['placeholder_id'],
                'name': p['placeholder_name'],
                'expected_type': p.get('expected_type'),
                'status': p.get('status', 'pending'),
                'value': p.get('user_input'),
                'attempts': p.get('attempts', 0)
            })
        
        # Calculate progress
        status_counts = {
            'filled': 0,
            'auto_filled': 0,
            'pending': 0,
            'skipped': 0
        }
        
        for p in data.get('placeholders', []):
            status = p.get('status', 'pending')
            if status in status_counts:
                status_counts[status] += 1
        
        return jsonify({
            'reference_number': ref_number,
            'document_summary': data.get('document_summary', ''),
            'validation_status': data.get('validation_status', 'pending'),
            'progress': {
                'filled': status_counts['filled'],
                'auto_filled': status_counts['auto_filled'],
                'pending': status_counts['pending'],
                'skipped': status_counts['skipped'],
                'total': len(data.get('placeholders', []))
            },
            'placeholders_preview': placeholders_preview
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_final_doc/<int:ref_number>', methods=['POST'])
def generate_final_document(ref_number):
    """
    Generate the final document by replacing all placeholders with values
    
    Args:
        ref_number: Reference number
    
    Returns:
        JSON with download link to final document
    """
    import time
    start_time = time.time()
    
    try:
        # Load reference JSON
        ref_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(ref_number))
        
        if not os.path.exists(ref_folder):
            return jsonify({'error': f'Reference {ref_number} not found'}), 404
        
        data = load_reference_json(ref_folder)
        
        if not data:
            return jsonify({'error': 'Failed to load reference data'}), 500
        
        placeholders = data.get('placeholders', [])
        
        # Check if all placeholders are filled
        fill_status = check_all_filled(placeholders)
        
        if not fill_status['all_filled']:
            return jsonify({
                'error': 'Not all placeholders are filled',
                'pending': fill_status['pending'],
                'message': f"{len(fill_status['pending'])} placeholder(s) still pending"
            }), 400
        
        # Get the marked document path
        marked_document = data.get('marked_document')
        if not marked_document:
            return jsonify({'error': 'Marked document not found in metadata'}), 500
        
        marked_doc_path = os.path.join(ref_folder, marked_document)
        
        if not os.path.exists(marked_doc_path):
            return jsonify({'error': f'Marked document file not found: {marked_document}'}), 500
        
        # Determine output filename based on auto_filled presence
        has_auto_filled = fill_status['has_auto_filled']
        
        if has_auto_filled:
            final_filename = 'final_draft.docx'
        else:
            final_filename = 'final_document.docx'
        
        final_doc_path = os.path.join(ref_folder, final_filename)
        
        # Replace placeholders
        print(f"Generating final document for reference {ref_number}...")
        result = replace_placeholders_in_document(
            marked_doc_path,
            placeholders,
            final_doc_path
        )
        
        if not result['success']:
            return jsonify({
                'error': 'Failed to generate final document',
                'details': result['errors']
            }), 500
        
        # Update JSON metadata
        data['validation_status'] = 'complete'
        data['final_document'] = final_filename
        
        save_reference_json(ref_folder, data)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Log action
        log_action(
            ref_folder,
            'final_generated',
            status='complete',
            latency_ms=latency_ms,
            replacements=result['replacements'],
            has_auto_filled=has_auto_filled
        )
        
        print(f"✓ Final document generated: {final_filename}")
        print(f"✓ Made {result['replacements']} replacements")
        
        return jsonify({
            'status': 'ok',
            'message': f'Final document generated successfully ({result["replacements"]} replacements)',
            'final_document': final_filename,
            'has_auto_filled': has_auto_filled,
            'download': f'/download/{ref_number}/{final_filename}'
        }), 200
        
    except Exception as e:
        print(f"Error generating final document: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Document processing service is running'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5051)
