from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from docx import Document
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re
from datetime import datetime

# Load environment variables from document-processing folder
doc_processing_root = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(doc_processing_root, '.env'))

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
CONFIG_FOLDER = os.path.join(BASE_DIR, 'config')
PATTERNS_CONFIG_FILE = os.path.join(CONFIG_FOLDER, 'placeholder_patterns.json')
ALLOWED_EXTENSIONS = {'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)

# Counter file for reference numbers
COUNTER_FILE = os.path.join(UPLOAD_FOLDER, '.counter.txt')


def get_next_reference_number():
    """
    Get the next reference number for uploads
    
    Returns:
        int: Next reference number
    """
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, 'w') as f:
            f.write('0')
        return 1
    
    with open(COUNTER_FILE, 'r') as f:
        current = int(f.read().strip() or '0')
    
    next_num = current + 1
    
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(next_num))
    
    return next_num


def load_placeholder_patterns():
    """
    Load placeholder patterns from the configuration file
    
    Returns:
        dict: Configuration with patterns and settings
    """
    try:
        if os.path.exists(PATTERNS_CONFIG_FILE):
            with open(PATTERNS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        else:
            # Return default patterns if config file doesn't exist
            return {
                "patterns": [
                    {
                        "name": "square_brackets",
                        "description": "Square brackets format: [Placeholder Name]",
                        "regex": "\\[([A-Za-z0-9\\s_\\-]+)\\]",
                        "enabled": True
                    },
                    {
                        "name": "double_curly_braces",
                        "description": "Double curly braces format: {{Placeholder Name}}",
                        "regex": "\\{\\{([A-Za-z0-9\\s_\\-]+)\\}\\}",
                        "enabled": True
                    },
                    {
                        "name": "single_curly_braces",
                        "description": "Single curly braces format: {Placeholder Name}",
                        "regex": "\\{([A-Za-z0-9\\s_\\-]+)\\}",
                        "enabled": True
                    }
                ],
                "context_words_count": 20
            }
    except Exception as e:
        print(f"Error loading patterns config: {str(e)}")
        # Return minimal default
        return {
            "patterns": [
                {"name": "square_brackets", "regex": "\\[([A-Za-z0-9\\s_\\-]+)\\]", "enabled": True}
            ],
            "context_words_count": 20
        }


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_context(text, start_pos, end_pos, words_count):
    """
    Extract context before and after a placeholder position
    
    Args:
        text: The full document text
        start_pos: Start position of the placeholder
        end_pos: End position of the placeholder
        words_count: Number of words to extract before and after
    
    Returns:
        tuple: (context_before, context_after, before_words_actual, after_words_actual)
    """
    # Extract text before the placeholder
    text_before = text[:start_pos].strip()
    words_before = text_before.split()
    context_before = ' '.join(words_before[-words_count:]) if len(words_before) > words_count else text_before
    before_words_actual = min(len(words_before), words_count)
    
    # Extract text after the placeholder
    text_after = text[end_pos:].strip()
    words_after = text_after.split()
    context_after = ' '.join(words_after[:words_count]) if len(words_after) > words_count else text_after
    after_words_actual = min(len(words_after), words_count)
    
    return context_before, context_after, before_words_actual, after_words_actual


def generate_document_summary(document_text):
    """
    Generate a ~100 word summary of the document using OpenAI
    
    Args:
        document_text: The full document text
    
    Returns:
        str: Document summary
    """
    try:
        prompt = f"""You are a precise summarizer for legal and investment agreements.

Summarize the following document in about 100 words.

Focus on:
- The type of agreement (e.g., SAFE, investment, loan, etc.)
- The involved parties
- The main purpose or obligations
- Any key variables such as amount, dates, or governing law

Avoid filler language and boilerplate.
Output only the summary paragraph, without bullets or formatting.

Document Text:
{document_text[:5000]}"""  # Limit to first 5000 chars to save tokens

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating document summary: {str(e)}")
        return "Document summary generation failed."


def detect_placeholders(text):
    """
    Detect placeholders in the document text using regex patterns from config file
    
    Args:
        text: The document text
    
    Returns:
        list: List of dictionaries containing placeholder information
    """
    # Load patterns from configuration
    config = load_placeholder_patterns()
    patterns = config.get('patterns', [])
    context_words_count = config.get('context_words_count', 20)
    
    # Filter enabled patterns only
    enabled_patterns = [p for p in patterns if p.get('enabled', True)]
    
    placeholders = []
    placeholder_counter = 1
    
    for pattern_config in enabled_patterns:
        pattern = pattern_config.get('regex')
        pattern_name = pattern_config.get('name', 'unknown')
        
        if not pattern:
            continue
        
        try:
            for match in re.finditer(pattern, text):
                placeholder_text = match.group(0)
                placeholder_name = match.group(1).strip()
                start_pos = match.start()
                end_pos = match.end()
                
                # Extract context using configured word count
                context_before, context_after, before_words_actual, after_words_actual = extract_context(
                    text, start_pos, end_pos, context_words_count
                )
                
                placeholder_info = {
                    "placeholder_id": f"placeholder_{str(placeholder_counter).zfill(3)}",
                    "placeholder": placeholder_text,
                    "placeholder_name": placeholder_name,
                    "description": f"the '{placeholder_name}'",
                    "pattern_type": pattern_name,
                    "position": {
                        "start": start_pos,
                        "end": end_pos
                    },
                    "context_before": context_before,
                    "context_after": context_after,
                    "context_window": {
                        "before_words": before_words_actual,
                        "after_words": after_words_actual
                    },
                    "user_input": None,
                    "status": "pending"
                }
                
                placeholders.append(placeholder_info)
                placeholder_counter += 1
        except re.error as e:
            print(f"Error in regex pattern '{pattern_name}': {str(e)}")
            continue
    
    # Sort placeholders by position to maintain order
    placeholders.sort(key=lambda x: x['position']['start'])
    
    return placeholders


def extract_document_text(doc):
    """
    Extract full text from a docx Document object
    
    Args:
        doc: python-docx Document object
    
    Returns:
        str: Extracted text
    """
    full_text = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            full_text.append(paragraph.text)
    
    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    full_text.append(cell.text)
    
    return '\n'.join(full_text)


def create_marked_document(original_doc_path, placeholders, output_path):
    """
    Create a new document with placeholders marked with unique IDs
    
    Args:
        original_doc_path: Path to the original document
        placeholders: List of placeholder dictionaries
        output_path: Path where the marked document will be saved
    
    Returns:
        str: Path to the saved marked document
    """
    doc = Document(original_doc_path)
    
    # Create a mapping of original placeholders to marked versions
    placeholder_map = {}
    for ph in placeholders:
        original = ph['placeholder']
        marked = f"[{ph['placeholder_id']}: {ph['description']}]"
        placeholder_map[original] = marked
    
    # Replace placeholders in paragraphs
    for paragraph in doc.paragraphs:
        for original, marked in placeholder_map.items():
            if original in paragraph.text:
                # Replace the placeholder while preserving formatting
                for run in paragraph.runs:
                    if original in run.text:
                        run.text = run.text.replace(original, marked)
    
    # Replace placeholders in tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for original, marked in placeholder_map.items():
                        if original in paragraph.text:
                            for run in paragraph.runs:
                                if original in run.text:
                                    run.text = run.text.replace(original, marked)
    
    # Save the marked document
    doc.save(output_path)
    return output_path


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
    # Check if file is present in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if file is allowed
    if file and allowed_file(file.filename):
        try:
            # Get reference number and create folder
            ref_number = get_next_reference_number()
            ref_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(ref_number))
            os.makedirs(ref_folder, exist_ok=True)
            
            # Secure the filename and save
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1]
            
            # Save original document in reference folder
            original_filename = f"{base_name}_{timestamp}_original{ext}"
            original_filepath = os.path.join(ref_folder, original_filename)
            file.save(original_filepath)
            
            # Parse the document
            doc = Document(original_filepath)
            document_text = extract_document_text(doc)
            
            # Detect placeholders
            placeholders = detect_placeholders(document_text)
            
            if len(placeholders) == 0:
                return jsonify({
                    'warning': 'No placeholders detected in the document',
                    'uploaded_document': original_filename,
                    'document_text': document_text,
                    'placeholders': []
                }), 200
            
            # Generate document summary
            print("Generating document summary...")
            document_summary = generate_document_summary(document_text)
            
            # Create marked document in reference folder
            marked_filename = f"{base_name}_{timestamp}_placeholder_marked{ext}"
            marked_filepath = os.path.join(ref_folder, marked_filename)
            create_marked_document(original_filepath, placeholders, marked_filepath)
            
            # Save placeholder data as JSON in reference folder
            json_filename = f"{base_name}_{timestamp}_placeholders.json"
            json_filepath = os.path.join(ref_folder, json_filename)
            
            # Load context policy from config
            config = load_placeholder_patterns()
            context_words_count = config.get('context_words_count', 20)
            
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
                "total_placeholders": len(placeholders),
                "placeholders": placeholders
            }
            
            # Save JSON
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(placeholder_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Document processed with {len(placeholders)} placeholders")
            print(f"✓ Files saved in uploads/{ref_number}/")
            
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
                    'total_placeholders': len(placeholders),
                    'placeholders': placeholders,
                    'verification_status': 'Placeholders correctly detected and marked.'
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
    """
    Download a processed document
    
    Args:
        ref_number: Reference number folder
        filename: Name of the file to download
    
    Returns:
        File download response
    """
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], ref_number, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/placeholder-data/<ref_number>/<json_filename>')
def get_placeholder_data(ref_number, json_filename):
    """
    Retrieve placeholder data from JSON file
    
    Args:
        ref_number: Reference number folder
        json_filename: Name of the JSON file
    
    Returns:
        JSON response with placeholder data
    """
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
    """
    Get the current placeholder patterns configuration
    
    Returns:
        JSON response with patterns configuration
    """
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


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Document processing service is running'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5051)
