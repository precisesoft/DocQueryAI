# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DocQueryAI is a document chat application that enables users to upload documents (PDF, TXT) and query them using AI. The system uses semantic search with embeddings to find relevant document chunks and generates responses using local LLM models via Ollama.

## Architecture

### Three-Tier Architecture

1. **Frontend** (React): User interface for document management and chat
   - Located in `frontend/`
   - Uses axios for API communication
   - Supports markdown rendering and code highlighting in chat responses
   - Manages chat history and conversation state

2. **Backend** (Flask): API server for document processing and LLM orchestration
   - Located in `backend/app.py`
   - Handles document upload, chunking, and embedding generation
   - Manages semantic search across document chunks
   - Proxies requests to Ollama LLM service

3. **LLM Service** (Ollama): Provides embedding and chat completion models
   - Runs on port 1234 (Docker service name: `llm-service`)
   - Models used:
     - `text-embedding-bge-m3`: For generating document/query embeddings
     - `deepseek-r1-distill-qwen-32b-mlx`: For chat completions

### Key Architectural Components

**Document Processing Pipeline:**
- Documents are uploaded via `/api/upload` endpoint
- Text is extracted (PDF via PyPDF2, TXT directly)
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

**Ports:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5001/api
- Ollama: http://localhost:1234

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

**Ollama Service:**
```bash
# Install Ollama from ollama.ai, then:
ollama pull text-embedding-bge-m3
ollama pull deepseek-r1-distill-qwen-32b-mlx
ollama serve  # Runs on port 1234
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
- `document_store`: In-memory dict storing document chunks and embeddings

**Frontend ([frontend/src/App.js](frontend/src/App.js)):**
- Main app state management (documents, messages, chat mode)
- API integration with backend
- Conversation saving to localStorage

**Frontend Components ([frontend/src/components/](frontend/src/components/)):**
- `ChatInterface`: Main chat UI with message display and input
- `Sidebar`: Document list and upload interface
- `MessageBubble`: Individual message rendering with markdown/code support
- `CodeBlock`: Code syntax highlighting with copy functionality
- `ModelSettings`: LLM parameter configuration (temperature, max tokens)
- `SaveConversationModal`: Save/load conversation functionality

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

## Environment Variables

**Backend (docker-compose.yml):**
- `FLASK_ENV`: Set to `production` in Docker
- Backend connects to Ollama via Docker service name: `llm-service:1234`

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
2. Update `docker-compose.yml` entrypoint to auto-pull on startup
3. Add to model selection in [frontend/src/components/ModelSettings.js](frontend/src/components/ModelSettings.js)

**Debugging embedding issues:**
- Check `/api/embedding-test` endpoint
- Verify Ollama service is running: `docker-compose ps`
- Check Ollama logs: `docker-compose logs llm-service`
