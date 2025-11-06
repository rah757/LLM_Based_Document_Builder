# Document Placeholder Processor

Flask-based backend for detecting and processing placeholders in legal documents. Modular architecture ready for Phase 2 development.

## Features

- Document upload and .docx parsing
- Configurable placeholder detection via regex patterns
- Context extraction (20 words before/after each placeholder)
- Marked document generation with unique placeholder IDs
- AI-powered document summarization using OpenAI GPT-4o-mini
- Reference-numbered folder organization for each upload
- Modular utils for validation, summarization, and RAG preparation

## Project Structure

```
document-processing/
├── config/
│   ├── placeholder_patterns.json       # Placeholder regex patterns
│   └── expected_type_map.json          # Type detection and validation rules
├── src/
│   ├── app.py                          # Main Flask application
│   ├── prompts/                        # LLM prompt templates
│   ├── utils/                          # Modular utilities
│   │   ├── file_utils.py               # File handling and reference numbering
│   │   ├── placeholder_utils.py        # Placeholder detection and marking
│   │   ├── summary_utils.py            # Document summarization
│   │   ├── validation_utils.py         # Input validation
│   │   └── rag_utils.py                # RAG utilities (placeholder)
│   ├── templates/
│   │   └── index.html                  # Upload interface
│   └── static/
│       └── style.css                   # Frontend styling
├── uploads/{ref_number}/               # Processed documents by reference
└── tests/                              # Unit tests
```

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

## Supported Placeholder Formats

[Name], {{Name}}, {Name}

