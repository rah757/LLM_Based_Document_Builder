# Document Placeholder Processor

Flask-based backend for detecting and processing placeholders in legal documents.

## Features

- Document upload and .docx parsing
- Configurable placeholder detection via regex patterns (config/placeholder_patterns.json)
- Context extraction (20 words before/after each placeholder)
- Marked document generation with unique placeholder IDs
- AI-powered document summarization using OpenAI GPT-4o-mini
- Reference-numbered folder organization for each upload

## Setup

```bash
cd document-processing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` file with:
```
OPENAI_API_KEY=your-api-key-here
```

## Run

```bash
./run.sh
```

Then open: http://localhost:5051

## Structure

- `src/app.py` - Main Flask application
- `src/templates/index.html` - Upload interface
- `config/placeholder_patterns.json` - Placeholder detection patterns
- `uploads/{ref_number}/` - Processed documents and JSON metadata

## Supported Formats

[Name], {{Name}}, {Name}
