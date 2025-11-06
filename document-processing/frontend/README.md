# Document Placeholder Filler - Frontend

Simple React frontend for testing the conversational document filling system.

## Setup

```bash
cd frontend
npm install
```

## Run

Make sure the backend is running on port 5051, then:

```bash
npm start
```

Opens on http://localhost:3000 (proxies API calls to backend on port 5051)

## Features

- Drag & drop document upload
- Conversational chat interface for filling placeholders
- Real-time progress tracking
- Auto-suggest for failed validation attempts
- Preview and download final document

## Flow

1. **Upload** - Drop .docx file with placeholders
2. **Chat** - Answer questions one by one
3. **Validate** - System validates inputs (3-tier)
4. **Auto-suggest** - Offers AI completion after 2 failed attempts
5. **Complete** - Download final filled document

