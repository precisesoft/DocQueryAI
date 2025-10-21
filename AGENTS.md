# AGENTS.md

This file gives coding agents (and humans) a fast, accurate memory of the DocQueryAI repo. It applies to the entire repository tree.

## Overview

- Purpose: Chat with an LLM about uploaded documents (PDF/TXT) using semantic search over chunk embeddings.
- Stack: Flask backend (`backend/`), React frontend (`frontend/`), Ollama for LLMs (Docker service `llm-service`).
- Storage: Runtime in-memory `document_store` (clears on restart); uploaded files stored under `./uploads` (mounted in Docker).

## Run Targets

- Docker (recommended): `docker-compose up -d`
  - Frontend: http://localhost:3000
  - Backend API: http://localhost:5001/api
  - Ollama: http://localhost:11434

- Local dev (alt):
  - Backend: create venv, install `backend/requirements.txt`, run `backend/app.py` (port 5001)
  - Frontend: `cd frontend && npm install && npm start`
  - Ollama: install from ollama.ai and `ollama serve` (port 11434). Pull `bge-m3` and a chat model (default `gemma2:27b`). Optional: pull a vision model and set `VISION_MODEL` for OCR of scanned PDFs.

## Key Defaults (as of Oct 16, 2025)

- Embeddings: `bge-m3`
- Chat model: `gemma2:27b` (override via `CHAT_MODEL` or UI Model Settings)
- Vision OCR model: `VISION_MODEL` env (unset by default). Example: `moondream`.
- Chunking: size 1000 chars, overlap 200

## Important Files

- `backend/app.py`: Upload → parse (PDF/TXT) → optional OCR → chunk → embed → store → search → chat (SSE streaming).
- `frontend/src/App.js`: App state, upload, streaming chat, conversation save/import/export.
- `frontend/src/components/`: UI components; `RevampLayout.jsx`, `ModelSettings.js`, `MessageBubble.js`.
- `docker-compose.yml`: Services (backend, frontend, `llm-service`) and model auto-pulls.
- `CLAUDE.md`: Expanded project memory for LLMs. Keep in sync with code.
- `embeddings.json` and `query_documents.py`: Standalone local script path (not used by Flask API).

## API Surface

- `POST /api/upload` — multipart file upload; extracts text, OCR if needed, chunks + embeds when embeddings available.
- `GET /api/documents` — list uploaded docs (name + excerpt).
- `POST /api/chat` — streaming chat; supports document-mode with semantic context (top-k chunks).
- `POST /api/documents/clear` — clears in-memory store; `delete_files: true` removes files from `./uploads`.
- `GET /api/models` — lists Ollama models.
- `GET|POST /api/embedding-test` — embedding smoke test.
- `GET /api/health` — health and embedding availability.

## Conventions & Notes

- Embedding availability is probed on startup; if unavailable, app still runs but semantic search is disabled.
- Vision OCR uses Ollama native `/api/generate` (not the OpenAI-compatible route). Ensure `VISION_MODEL` is pulled.
- Similarity metric is cosine similarity; top 3 chunks are used as context.
- Frontend persists theme, compact mode, and saved conversations in `localStorage`.

## Known Divergences To Watch

- README local LLM port may reference `1234`, but code and Docker use `11434`.
- Some historical docs reference `phi3:mini`; current default chat model is `gemma2:27b`.
- `query_documents.py` is a separate utility that does not drive the Flask API; its defaults may differ.

## How To Update Memory

- Update this `AGENTS.md` for concise, task-focused guidance.
- Update `CLAUDE.md` for detailed architecture/operations changes.
- If you change models, ports, or endpoints, reflect them in both docs.

## Quick Tasks (agent-friendly)

- Add a model: update `docker-compose.yml` `llm-service` entrypoint to auto-`ollama pull`, and expose it in `frontend/src/components/ModelSettings.js`.
- Adjust chunking: edit `CHUNK_SIZE` and `CHUNK_OVERLAP` in `backend/app.py`.
- Reset state: call `POST /api/documents/clear` (set `delete_files` to also remove uploads).

