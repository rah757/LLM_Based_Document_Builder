# Testing Guide

## Quick Start

### Option 1: Start Both (Recommended for Testing)

```bash
cd document-processing
./start_all.sh
```

This starts both backend (port 5051) and frontend (port 3000) automatically.

### Option 2: Start Separately

**Terminal 1 - Backend:**
```bash
cd document-processing
./run.sh
```

**Terminal 2 - Frontend:**
```bash
cd document-processing/frontend
npm install  # first time only
npm start
```

## Access

- **Frontend UI:** http://localhost:3000
- **Backend API:** http://localhost:5051

## Test Flow

### 1. Upload Document

- Open http://localhost:3000
- Drag & drop a .docx file with placeholders:
  - `[Company Name]`
  - `{{Investor Name}}`
  - `{Date of Agreement}`
- Click "Upload & Start Filling"
- Note the reference number displayed

### 2. Conversational Filling

**Test Happy Path:**
- Answer first question (e.g., "Acme Inc.")
- Should show: ✓ Got it! Saved as: Acme Inc.
- Automatically moves to next question

**Test Validation:**
- For a date field, enter invalid: "asdf"
- Should show: ❌ [hint] Please try again (Attempt 1/2)
- Enter valid date: "05/15/2026"
- Should show: ✓ Got it! Saved as: 2026-05-15

**Test Auto-Suggest:**
- For any field, enter wrong value twice
- Should show: 🤔 Having trouble? I can suggest...
- Click "Accept Auto-Suggestion"
- Should auto-fill and move to next

### 3. Progress Tracking

- Watch progress bar fill up
- Top shows: "X of Y complete"
- Reference badge displays reference number

### 4. Completion

- After last placeholder filled
- Shows: 🎉 Document Complete!
- Download button appears
- If auto-fills used: Shows draft warning

### 5. Download

- Click "Download final_document.docx"
- Open in Word/Google Docs
- Verify all placeholders replaced with correct values

## API Testing (Optional)

### Upload
```bash
curl -X POST http://localhost:5051/upload \
  -F "file=@sample.docx"
```

### Get Placeholders
```bash
curl http://localhost:5051/placeholders/1
```

### Fill Placeholder
```bash
curl -X POST http://localhost:5051/fill_placeholder/1/placeholder_001 \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Acme Inc."}'
```

### Generate Final
```bash
curl -X POST http://localhost:5051/generate_final_doc/1
```

## Test Documents

Create test documents with various placeholder patterns:

**Legal Document:**
- `[Company Name]`
- `[Investor Name]`
- `[Purchase Amount]`
- `[Date of Agreement]`
- `[Governing Law]`

**Contract:**
- `{{Client Name}}`
- `{{Project Start Date}}`
- `{{Payment Amount}}`
- `{{Client Email}}`

## Expected Behaviors

### Type Inference
- Legal names: No special formatting
- Dates: Normalized to YYYY-MM-DD
- Money: Normalized to decimal (12345.00)
- Email: Basic validation

### Validation Tiers
1. **Local** - Fast regex checks
2. **LLM** - GPT-5-nano validation (if local fails)
3. **Auto-suggest** - GPT-4o-mini (after 2 failures)

### Facts Overlay
- After filling "Company Name: Acme Inc."
- Next questions should see this context
- Makes suggestions more accurate

## Troubleshooting

**Backend won't start:**
- Check `.env` has `OPENAI_API_KEY=sk-...`
- Ensure port 5051 is free: `lsof -i :5051`
- Check Python version: `python3 --version` (need 3.8+)

**Frontend won't start:**
- Ensure port 3000 is free: `lsof -i :3000`
- Try: `cd frontend && rm -rf node_modules && npm install`

**Upload fails:**
- File must be .docx (not .doc)
- Check file isn't corrupted
- Try creating a fresh document

**No placeholders detected:**
- System shows: "No placeholders detected"
- Check patterns: `[Name]`, `{{Name}}`, `{Name}`
- Ensure brackets are correct type

**API errors:**
- Check backend logs for OpenAI API errors
- Verify API key is valid
- Check network connectivity

