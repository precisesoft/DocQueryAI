# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DocQueryAI is a document chat application that enables users to upload documents (PDF, TXT) and query them using AI. The system uses semantic search with embeddings to find relevant document chunks and generates responses using local LLM models via Ollama. For scanned PDFs, the system can use a vision model (OCR) to extract text before processing.

## Architecture

### Three-Tier Architecture

1. **Frontend** (React): User interface for document management and chat
   - Located in `frontend/`
   - Built with shadcn/ui components (Radix UI + Tailwind CSS)
   - Uses axios for API communication
   - Supports markdown rendering and code highlighting in chat responses
   - Manages chat history and conversation state
   - Features: dark mode, keyboard shortcuts, conversation search/filter, compact mode

2. **Backend** (Flask): API server for document processing and LLM orchestration
   - Located in `backend/app.py`
   - Handles document upload, chunking, and embedding generation
   - OCR support for scanned PDFs using vision models (PyMuPDF rendering + Ollama vision API)
   - Manages semantic search across document chunks
   - Proxies requests to Ollama LLM service

3. **LLM Service** (Ollama): Provides embedding and chat completion models
   - Runs on port 11434 (Docker service name: `llm-service`)
   - Models used (current defaults as of Oct 16, 2025):
     - `bge-m3`: Embedding model
     - `gemma2:27b`: Default chat model
     - Vision OCR model: configurable via `VISION_MODEL` (optional). Example: `moondream`.

### Key Architectural Components

**Document Processing Pipeline:**
- Documents are uploaded via `/api/upload` endpoint
- Text is extracted:
  - Regular PDFs: PyPDF2 text extraction
  - Scanned PDFs: PyMuPDF renders pages as images → vision model OCR
  - TXT: Direct read
- Text is split into chunks (1000 chars with 200 char overlap) using smart boundary detection (sentences, paragraphs, lines)
- Each chunk gets an embedding vector from Ollama
- Chunks and embeddings stored in-memory in `document_store` dict

**Semantic Search:**
- Query embeddings are generated for user questions
- Cosine similarity computed between query and all document chunks
- Top 3 most relevant chunks retrieved and provided as context to LLM

**Chat Modes:**
- `general`: Direct chat with LLM without document context
- `document`: Chat with selected document using semantic search for context

## Development Commands

### Running with Docker (Recommended)

```bash
# Start all services (backend, frontend, Ollama)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose build
docker-compose up -d
```

**Ports (Docker):**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5001/api
- Ollama (Ollama HTTP API): http://localhost:11434

### Running Locally

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py  # Runs on port 5001
```

**Frontend:**
```bash
cd frontend
npm install
npm start  # Runs on port 3000
npm test  # Run tests
npm run build  # Production build
```

**Ollama Service (local dev, optional if not using Docker):**
```bash
# Install Ollama from ollama.ai, then:
ollama pull bge-m3           # embeddings
ollama pull gemma2:27b       # chat default (matches docker-compose)
# Optional OCR VLM if you plan to use scanned PDFs via OCR:
ollama pull moondream        # or set a different `VISION_MODEL`
ollama serve                 # Runs on port 11434
```

## API Endpoints

- `POST /api/upload`: Upload document (multipart/form-data)
- `GET /api/documents`: List all uploaded documents
- `POST /api/chat`: Send chat message (streaming response)
- `POST /api/documents/clear`: Clear all documents
- `GET /api/models`: List available Ollama models
- `GET /api/health`: Health check endpoint
- `POST /api/embedding-test`: Test embedding generation

## Key Files and Functions

**Backend ([backend/app.py](backend/app.py)):**
- `chunk_text()`: Splits documents into overlapping chunks with smart boundary detection
- `process_document_chunks()`: Generates embeddings for all chunks
- `find_relevant_chunks()`: Semantic search using cosine similarity
- `vector_similarity()`: Cosine similarity calculation
- `get_embedding()`: Calls Ollama embedding API
- `render_pdf_to_images_b64()`: Renders PDF pages to base64 PNG images for OCR
- `ocr_pdf_with_vlm()`: Uses vision model to perform OCR on scanned PDFs
- `document_store`: In-memory dict storing document chunks and embeddings

**Frontend ([frontend/src/App.js](frontend/src/App.js)):**
- Main app state management (documents, messages, chat mode)
- API integration with backend
- Conversation saving to localStorage
- Theme (dark mode) and compact mode persistence

**Frontend Components ([frontend/src/components/](frontend/src/components/)):**
- `RevampLayout.jsx`: Main layout with sidebar, tabbed navigation, and responsive design
- `Composer.jsx`: Chat input with Enter-to-send (Shift+Enter for newlines)
- `MessageBubble.js`: Individual message rendering with markdown/code support (Apple-style alignment)
- `CodeBlock.js`: Code syntax highlighting with copy functionality
- `ModelSettings.js`: LLM parameter configuration (temperature, max tokens)
- `ui/*.jsx`: shadcn/ui components (Button, Input, Card, ScrollArea, Sheet, Dialog, etc.)

## Data Storage

**Runtime:**
- Document chunks and embeddings: In-memory Python dict (`document_store`)
- Saved conversations: Browser localStorage

**Persistent (Docker volumes):**
- `uploads/`: Uploaded document files
- `documents/`: Processed document files
- `ollama_models/`: Downloaded LLM models

## Important Implementation Details

**Chunking Strategy:**
- Default chunk size: 1000 characters
- Overlap: 200 characters (preserves context across chunks)
- Smart boundary detection: Prefers sentence endings (. ? !) > paragraphs (\n\n) > lines (\n) > spaces

**Embedding Availability:**
- Backend checks embedding service availability at startup (`is_embedding_available()`)
- If unavailable, documents are stored without embeddings and warning is shown
- Semantic search falls back to returning first few chunks

**Chat Streaming:**
- Chat responses use Server-Sent Events (SSE) for streaming
- Backend proxies Ollama streaming responses to frontend

**CORS Configuration:**
- Backend allows all origins for `/api/*` endpoints
- Required for local development (different ports)

**UI/UX Features:**
- Keyboard shortcuts:
  - `N`: New chat
  - `R`: Rename selected conversation
  - `Delete/Backspace`: Delete selected conversation
  - `Enter`: Send message (no Shift)
  - `Shift+Enter`: New line in message input
- Collapsible sidebar (desktop) with tooltips
- Mobile-responsive with Sheet navigation
- Conversation search/filter
- Inline conversation rename with hover actions
- Apple-style chat bubbles (user right/blue, bot left/neutral)

## Environment Variables

**Backend (docker-compose.yml):**
- `FLASK_ENV`: Set to `production` in Docker
- Backend connects to Ollama via Docker service name: `llm-service:11434`
- `VISION_MODEL`: Vision model for OCR (default: `moondream`)

**Frontend:**
- `REACT_APP_API_URL`: Backend API URL (default: http://localhost:5001/api)

## Testing

**Frontend:**
- Uses React Testing Library and Jest
- Test files: `*.test.js` in `frontend/src/`
- Run with: `npm test`

**Backend:**
- Manual testing via `backend/test_server.py` and `backend/test_upload.html`
- Health check endpoint: `/api/health`
- Embedding probe endpoint: `/api/embedding-test` (GET/POST)

## Common Development Tasks

**Adding a new document format:**
1. Add reader function in [backend/app.py](backend/app.py) (similar to `read_pdf_file()`)
2. Update file extension check in upload endpoint
3. Update `.dockerignore` if needed

**Modifying chunk size:**
- Update `CHUNK_SIZE` and `CHUNK_OVERLAP` constants in [backend/app.py](backend/app.py)
- Consider impact on embedding quality vs. context precision

**Adding a new LLM model:**
1. Pull model via Ollama: `ollama pull <model-name>`
2. If using Docker, update the `llm-service` `entrypoint` in `docker-compose.yml` to auto-pull on startup
3. Add to model selection in `frontend/src/components/ModelSettings.js`

**Working with shadcn/ui components:**
- Components are in `frontend/src/components/ui/`
- Built on Radix UI primitives with Tailwind CSS
- Use `cn()` utility from `lib/utils.js` for conditional classes
- Styling: Tailwind classes + CSS variables in `index.css` for theming

**Debugging embedding issues:**
- Check `/api/embedding-test` endpoint
- Verify Ollama service is running: `docker-compose ps`
- Check Ollama logs: `docker-compose logs llm-service`

**Debugging OCR/scanned PDF issues:**
- OCR will be attempted for PDFs when PyPDF2 extracts little/no text
- Set `VISION_MODEL` env var (example: `moondream`) and ensure the model is pulled
- Rendering parameters in `render_pdf_to_images_b64()`: scale (DPI), max_pages
- Check backend logs for OCR processing time and errors
- Adjust OCR prompt in `ocr_pdf_with_vlm()` for different document types

## API Endpoints (current)

- `POST /api/upload`: Upload document (multipart/form-data)
- `GET /api/documents`: List uploaded documents (name + excerpt)
- `POST /api/chat`: Chat endpoint with streaming
- `POST /api/documents/clear`: Clear in-memory store; optional file deletion via `delete_files`
- `GET /api/models`: List available Ollama models
- `GET|POST /api/embedding-test`: Verify embedding generation
- `GET /api/health`: Health check

## Defaults and Configuration

- Embedding model: `bge-m3`
- Chat model default: `gemma2:27b` (overridable via `CHAT_MODEL` env)
- Vision model: `VISION_MODEL` env (blank by default; set when OCR is needed)
- Chunking: size 1000 chars, overlap 200
- Ports: frontend 3000, backend 5001, Ollama 11434

## Notes for Contributors

- `backend/app.py` contains the full pipeline: upload → parse → optional OCR → chunk → embed → store → search → chat.
- The live document memory is in-memory only (`document_store`). Restarting the backend clears it unless documents are re-uploaded.
- `query_documents.py` in the repo is a separate local script that uses `embeddings.json` and a local LLM endpoint (defaults differ from Docker). It is not used by the Flask API.
