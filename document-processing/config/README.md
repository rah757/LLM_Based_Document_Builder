# Configuration Files

## models.json
Defines which LLM models to use for different tasks:
- `qa_model` - Main model for question generation and interaction (gpt-4o-mini)
- `validation_model` - Lightweight model for input validation (gpt-5-nano)
- `embeddings_backend` - Set to "none" (RAG disabled)
- `max_document_chars` - Maximum document size to process (200,000)
- `max_validation_retries` - Number of invalid attempts before auto-fill (2)

## expected_type_map.json
Maps placeholder names to expected types using keyword matching.
Each type includes:
- `keywords` - Terms to match in placeholder name
- `description` - Human-readable type description
- `examples` - Sample valid inputs

## validation_rules.json
Defines local validation rules per type:
- `regex_patterns` - Patterns to match for format validation
- `normalization` - How to normalize valid input (iso_date, decimal, lowercase, etc.)
- `min_length` - Minimum character length required

## placeholder_patterns.json
Regex patterns for detecting placeholders in documents:
- Square brackets: `[Name]`
- Double curly braces: `{{Name}}`
- Single curly braces: `{Name}`

