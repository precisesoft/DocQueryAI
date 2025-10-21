import os
import json
import logging
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add these imports
import re
import time
import numpy as np
from typing import List, Dict, Any
import threading

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Configuration
app.config["UPLOAD_FOLDER"] = "./uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs("./documents", exist_ok=True)

# API endpoints
# Prefer local Ollama by default (http://localhost:11434). Can be overridden via OLLAMA_BASE_URL.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_API_URL = f"{OLLAMA_BASE_URL}/v1"
OLLAMA_NATIVE_API = f"{OLLAMA_BASE_URL}/api"
EMBEDDING_ENDPOINT = f"{LLM_API_URL}/embeddings"
CHAT_ENDPOINT = f"{LLM_API_URL}/chat/completions"
EMBEDDING_MODEL = "bge-m3"
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemma2:27b")
VISION_MODEL = os.getenv("VISION_MODEL", "")

# Store uploaded documents in memory
document_store = {}
jobs_store: Dict[str, Dict[str, Any]] = {}

def _jobs_dir() -> Path:
    p = Path("./tmp/runs/jobs")
    p.mkdir(parents=True, exist_ok=True)
    return p

# Request logging middleware
@app.before_request
def log_request():
    logger.debug(f"Request received: {request.method} {request.path}")
    if not request.path.startswith('/static/'):
        logger.debug(f"Headers: {request.headers}")
        if request.method == 'POST':
            logger.debug(f"Form data: {request.form}")

# Helper functions
def read_text_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading text file: {e}")
        return ""

def read_pdf_file(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Error reading PDF file: {e}")
        return ""

def render_pdf_to_images_b64(file_path: str, scale: float = 2.0, max_pages: int = 0) -> List[str]:
    """Render PDF pages to base64-encoded PNG images using PyMuPDF.
    scale: 2.0 ~ 144 DPI (approx), higher gives sharper OCR but slower.
    max_pages: limit number of pages (0 = all).
    """
    images_b64: List[str] = []
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        pages = range(page_count) if max_pages <= 0 else range(min(max_pages, page_count))
        mat = fitz.Matrix(scale, scale)
        for i in pages:
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            images_b64.append(base64.b64encode(png_bytes).decode("utf-8"))
        doc.close()
    except Exception as e:
        logger.exception(f"Error rendering PDF to images: {e}")
    return images_b64

def ocr_pdf_with_vlm(file_path: str, vision_model: str = VISION_MODEL, pages_limit: int = 0) -> str:
    """Use a vision LLM via Ollama's native /api/generate endpoint to transcribe a scanned PDF."""
    images = render_pdf_to_images_b64(file_path, scale=2.0, max_pages=pages_limit)
    if not images:
        return ""
    prompt = (
        "You are an OCR assistant. Transcribe the page content faithfully into plain text. "
        "Preserve reading order, bullet points, and approximate tables as tab-separated text. "
        "Do not add commentary or headers; output only the transcribed text."
    )
    all_text: List[str] = []
    for idx, img in enumerate(images):
        try:
            resp = requests.post(
                f"{OLLAMA_NATIVE_API}/generate",
                json={
                    "model": vision_model,
                    "prompt": prompt,
                    "images": [img],
                    "stream": False
                },
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            page_text = data.get("response", "") or data.get("data", "")
            if page_text:
                all_text.append(page_text.strip())
            else:
                logger.warning(f"Empty OCR response for page {idx+1}")
        except Exception as e:
            logger.exception(f"Vision OCR failed on page {idx+1}: {e}")
    return "\n\n".join(all_text).strip()

# ----------------------------
# EntryDetail Extraction (Vision-only, wrapper output)
# ----------------------------

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text_candidates(rel_path: str) -> str:
    """Read a text file trying common roots (repo root, backend/)."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / rel_path,   # project root relative
        here / rel_path           # backend relative
    ]
    for p in candidates:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            continue
    return ""


def _sha256_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _format_wrapper_schema() -> Dict[str, Any]:
    # Lightweight JSON schema for the wrapper to guide structured output
    return {
        "type": "object",
        "required": ["schema_id", "schema_version", "data", "meta"],
        "properties": {
            "schema_id": {"type": "string", "const": "EntryDetailExtraction"},
            "schema_version": {"type": "string", "const": "1.0"},
            "data": {"type": "object"},
            "meta": {
                "type": "object",
                "required": ["agent_version", "model", "generated_at", "job_id", "overall_confidence", "validation"],
                "properties": {
                    "agent_version": {"type": "string"},
                    "model": {"type": "string"},
                    "generated_at": {"type": "string"},
                    "job_id": {"type": "string"},
                    "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "field_confidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "confidence"],
                            "properties": {"path": {"type": "string"}, "confidence": {"type": "number"}}
                        }
                    },
                    "field_evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "evidence"],
                            "properties": {
                                "path": {"type": "string"},
                                "evidence": {"type": "array"}
                            }
                        }
                    },
                    "validation": {
                        "type": "object",
                        "required": ["schema_ok"],
                        "properties": {
                            "schema_ok": {"type": "boolean"},
                            "missing_required": {"type": "array"},
                            "warnings": {"type": "array"}
                        }
                    }
                }
            }
        }
    }


def _local_validate_entrydetail(data_obj: Dict[str, Any]) -> Dict[str, Any]:
    report = {"schema_ok": True, "missing_required": [], "warnings": []}

    required_top = [
        "entryTypeCode", "operType", "mnlFileInd", "entrdThruPortId",
        "sbmsnDate", "lines", "entryAddress", "uspsContentReviewedAcceptedFlag"
    ]
    for k in required_top:
        if k not in data_obj or data_obj[k] in (None, ""):
            report["missing_required"].append(k)

    addrs = data_obj.get("entryAddress", []) or []
    if not isinstance(addrs, list) or len(addrs) != 2:
        report["warnings"].append("entryAddress should contain exactly 2 records")
        if len(addrs) < 2:
            report["missing_required"].append("entryAddress[2]")

    lines = data_obj.get("lines", []) or []
    if not isinstance(lines, list) or len(lines) < 1:
        report["missing_required"].append("lines[1]")
    for i, line in enumerate(lines):
        qty = (line or {}).get("quantity", []) or []
        if len(qty) != 2:
            report["warnings"].append(f"line[{i}].quantity should contain exactly 2 records")
        total_qty = (line or {}).get("totalQty")
        if isinstance(total_qty, (int, float)) and total_qty < 1.0:
            report["warnings"].append(f"line[{i}].totalQty < 1.0 (min)")
        value_amt = (line or {}).get("valueGoodsAmt")
        if isinstance(value_amt, (int, float)) and value_amt < 0.01:
            report["warnings"].append(f"line[{i}].valueGoodsAmt < 0.01 (min)")

    report["schema_ok"] = len(report["missing_required"]) == 0
    return report


def _postprocess_meta(wrapper_obj: Dict[str, Any]) -> None:
    """Cap confidences without evidence and ensure overall_confidence present."""
    meta = wrapper_obj.setdefault("meta", {})
    fc = meta.get("field_confidence", []) or []
    fe = meta.get("field_evidence", []) or []
    paths_with_evidence = set()
    for item in fe:
        try:
            p = item.get("path")
            ev = item.get("evidence", [])
            if p and isinstance(ev, list) and len(ev) > 0:
                paths_with_evidence.add(p)
        except Exception:
            continue
    for item in fc:
        try:
            p = item.get("path")
            c = float(item.get("confidence", 0))
            if p not in paths_with_evidence and c > 0.5:
                item["confidence"] = 0.5
        except Exception:
            continue
    if fc:
        try:
            vals = [float(x.get("confidence", 0)) for x in fc]
            overall = sum(vals) / max(len(vals), 1)
            meta.setdefault("overall_confidence", overall)
        except Exception:
            meta.setdefault("overall_confidence", 0.5)
    else:
        meta.setdefault("overall_confidence", 0.5)


def _collect_non_null_leaf_paths(data: Any, base: str = "") -> List[str]:
    paths = []
    if isinstance(data, dict):
        for k, v in data.items():
            sub = f"{base}.{k}" if base else k
            paths.extend(_collect_non_null_leaf_paths(v, sub))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            sub = f"{base}[{i}]"
            paths.extend(_collect_non_null_leaf_paths(v, sub))
    else:
        # primitive leaf
        if data is not None:
            paths.append(base)
    return paths


def _validate_evidence(wrapper_obj: Dict[str, Any]) -> List[str]:
    """Return list of non-null data paths that lack any evidence entries."""
    data_obj = wrapper_obj.get("data", {})
    meta = wrapper_obj.get("meta", {})
    non_null_paths = set(_collect_non_null_leaf_paths(data_obj))
    evidence = meta.get("field_evidence", []) or []
    paths_with_ev = set()
    for item in evidence:
        try:
            p = item.get("path")
            ev = item.get("evidence", [])
            if p and isinstance(ev, list) and len(ev) > 0:
                paths_with_ev.add(p)
        except Exception:
            continue
    missing = sorted([p for p in non_null_paths if p not in paths_with_ev])
    return missing


def _get_by_path(data: Any, path: str) -> Any:
    cur = data
    i = 0
    while i < len(path):
        if path[i] == '[':
            j = path.find(']', i)
            if j == -1:
                return None
            idx = path[i+1:j]
            try:
                cur = cur[int(idx)]
            except Exception:
                return None
            i = j + 1
        else:
            # read key until '.' or '[' or end
            j = i
            while j < len(path) and path[j] not in '.[':
                j += 1
            key = path[i:j]
            try:
                cur = cur[key]
            except Exception:
                return None
            i = j
        if i < len(path) and path[i] == '.':
            i += 1
    return cur


DEFAULT_SENTINELS: Dict[str, Any] = {
    # Address defaults
    'name': 'UNKNOWN',
    'line1Adrs': 'UNKNOWN',
    'cityName': 'UNKNOWN',
    'stateCode': '??',
    'isoCntryCode': '??',
    'zipCode': '00000',
    # Line defaults
    'imprtrPrdctDescText': 'UNKNOWN',
    'unitOfMsrCode': 'LB',
    'unitType': 'W',
    'totalQty': 1.0,
    'valueGoodsAmt': 0.01,
}


CRITICAL_EVIDENCE_PATHS: List[str] = [
    # Shipper (0) and Consignee (1)
    'entryAddress[0].name', 'entryAddress[0].line1Adrs', 'entryAddress[0].cityName', 'entryAddress[0].isoCntryCode', 'entryAddress[0].zipCode',
    'entryAddress[1].name', 'entryAddress[1].line1Adrs', 'entryAddress[1].cityName', 'entryAddress[1].isoCntryCode', 'entryAddress[1].zipCode',
    # Line description and key amounts
    'lines[0].imprtrPrdctDescText', 'lines[0].totalQty', 'lines[0].valueGoodsAmt',
    # Optional tracking if present
    'pstlTrckngNum'
]


def _is_default_sentinel(path: str, value: Any) -> bool:
    if value is None:
        return True
    # match by final key name
    tail = path.split('.')[-1]
    sentinel = DEFAULT_SENTINELS.get(tail, object())
    if sentinel is object():
        return False
    try:
        return value == sentinel
    except Exception:
        return False


def _run_entrydetail_job(file_path: str, max_pages: int = 2, scale: float = 1.6, model: str = "gemma3:12b", agent_version: str = "v1") -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Render pages
    images = render_pdf_to_images_b64(file_path, scale=scale, max_pages=max_pages)

    # Prompts
    sys_prompt = _read_text_candidates("data/derived/entrydetail.system.txt")
    user_guidance = _read_text_candidates("data/derived/entrydetail.user-guidance.txt")
    today = datetime.utcnow().date().isoformat()
    job_id = str(uuid.uuid4())
    doc_filename = os.path.basename(file_path)
    # Wrapper schema
    fmt = _format_wrapper_schema()

    user_instructions = (
        "You must return the wrapper object with keys schema_id='EntryDetailExtraction', schema_version='1.0', "
        "data (EntryDetail), and meta (metadata). "
        f"Set meta.agent_version='{agent_version}', meta.model='{model}', meta.generated_at='{_utcnow_iso()}', meta.job_id='{job_id}'. "
        "Populate meta.field_confidence and meta.field_evidence for non-null data fields; set overall_confidence. "
        "Set meta.validation with schema_ok and any missing_required/warnings you detect. "
        f"Use today's date for fields that require it: {today}. "
        f"Document: filename={doc_filename}. "
    )
    prompt = (sys_prompt or "") + "\n\n" + (user_guidance or "") + "\n\n" + user_instructions

    payload = {
        "model": model,
        "prompt": prompt,
        "images": images,
        "format": fmt,
        "stream": False,
        "options": {"temperature": 0.2}
    }

    # Call Ollama
    t0 = time.time()
    resp = requests.post(f"{OLLAMA_NATIVE_API}/generate", json=payload, timeout=900)
    elapsed = time.time() - t0
    resp.raise_for_status()
    data = resp.json()
    wrapper_text = data.get("response", "")
    wrapper = json.loads(wrapper_text)

    # Local validation
    data_obj = wrapper.get("data", {})
    local_val = _local_validate_entrydetail(data_obj)
    wrapper.setdefault("meta", {}).setdefault("validation", local_val)

    # Meta post process
    _postprocess_meta(wrapper)

    # Evidence validation: warn when non-null fields lack evidence
    missing_ev = _validate_evidence(wrapper)
    if missing_ev:
        v = wrapper.setdefault("meta", {}).setdefault("validation", {"schema_ok": True})
        warns = v.setdefault("warnings", [])
        warns.append(f"missing_evidence_count={len(missing_ev)} (see meta.missing_evidence_paths)")
        wrapper.setdefault("meta", {})["missing_evidence_paths"] = missing_ev
        # Optionally reduce overall confidence slightly for missing evidence
        try:
            oc = float(wrapper["meta"].get("overall_confidence", 0.5))
            # deduct up to 0.15 based on proportion of missing evidence among non-null leaves
            non_null_count = max(1, len(_collect_non_null_leaf_paths(data_obj)))
            penalty = min(0.15, 0.15 * len(missing_ev) / non_null_count)
            wrapper["meta"]["overall_confidence"] = max(0.0, oc - penalty)
        except Exception:
            pass

    # Hard fail on critical evidence missing when values are not defaults
    critical_missing = []
    for p in CRITICAL_EVIDENCE_PATHS:
        if p in missing_ev:
            val = _get_by_path(data_obj, p)
            if val not in (None, "") and not _is_default_sentinel(p, val):
                critical_missing.append({"path": p, "value": val})
    if critical_missing:
        v = wrapper.setdefault("meta", {}).setdefault("validation", {"schema_ok": True})
        v["schema_ok"] = False
        errs = v.setdefault("missing_required", [])
        errs.extend([f"missing_evidence:{cm['path']}" for cm in critical_missing])
        warns = v.setdefault("warnings", [])
        warns.append(f"critical_missing_evidence_count={len(critical_missing)}")

    result = {
        "job_id": job_id,
        "elapsed_sec": elapsed,
        "model": model,
        "wrapper": wrapper,
        "local_validation": local_val
    }
    return result

def get_embedding(text):
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text  # OpenAI-compatible format
    }
    try:
        logger.info(f"Calling embedding endpoint for text length: {len(text)}")
        response = requests.post(EMBEDDING_ENDPOINT, json=payload)
        response.raise_for_status()
        
        # Parse the response as JSON
        result = response.json()
        logger.debug(f"Embedding API response keys: {list(result.keys())}")
        
        # Handle different response formats based on the API
        if "data" in result and len(result["data"]) > 0 and "embedding" in result["data"][0]:
            # Standard OpenAI format
            return result["data"][0]["embedding"]
        elif "embedding" in result:
            # Direct embedding format
            return result["embedding"]
        else:
            logger.warning(f"Unexpected embedding response format: {result}")
            return []
            
    except requests.RequestException as e:
        logger.error(f"Error calling embedding endpoint: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response content: {e.response.text}")
        return []

def is_embedding_available():
    try:
        test_response = requests.post(
            EMBEDDING_ENDPOINT,
            json={
                "model": EMBEDDING_MODEL,
                "input": "Test"
            },
            timeout=3  # Short timeout for quick check
        )
        return test_response.status_code == 200
    except Exception as e:
        logger.error(f"Error checking embedding availability: {e}")
        return False

# Check if embedding service is available
HAS_EMBEDDING = is_embedding_available()
logger.info(f"Embedding API available: {HAS_EMBEDDING}")

# Add constants for chunking
CHUNK_SIZE = 1000  # Characters per chunk
CHUNK_OVERLAP = 200  # Overlap between chunks for context preservation

# Add this chunking function
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks of specified size."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Find the end of the current chunk
        end = start + chunk_size
        
        # If we're not at the end of the text, try to find a good breaking point
        if end < len(text):
            # Try to find sentence end (period, question mark, exclamation point)
            sentence_end = max(
                text.rfind('.', start, end),
                text.rfind('?', start, end),
                text.rfind('!', start, end)
            )
            
            # If found a sentence end, use it
            if sentence_end > start + (chunk_size // 2):  # At least half the chunk size
                end = sentence_end + 1
            else:
                # Try to find paragraph break
                para_end = text.rfind('\n\n', start, end)
                if para_end > start + (chunk_size // 3):
                    end = para_end + 2
                else:
                    # Try to find line break
                    line_end = text.rfind('\n', start, end)
                    if line_end > start + (chunk_size // 3):
                        end = line_end + 1
                    else:
                        # Try to find space
                        space_end = text.rfind(' ', start, end)
                        if space_end > start + (chunk_size // 2):
                            end = space_end + 1
        
        # Add the chunk
        chunks.append(text[start:end])
        
        # Move start position for next chunk, considering overlap
        start = end - chunk_overlap
        
        # Make sure we're making progress
        if start >= len(text):
            break
    
    return chunks

# Add this function to process chunks and generate embeddings
def process_document_chunks(text: str) -> Dict[str, Any]:
    """Process a document by chunking and generating embeddings for each chunk."""
    start_time = time.time()
    
    # Split text into chunks
    chunks = chunk_text(text)
    logger.info(f"Document split into {len(chunks)} chunks")
    
    # Generate embeddings for each chunk
    chunk_data = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Generating embedding for chunk {i+1}/{len(chunks)}")
        
        embedding = get_embedding(chunk)
        
        # Store chunk and its embedding
        if embedding:
            chunk_data.append({
                "chunk_id": i,
                "text": chunk,
                "embedding": embedding
            })
        else:
            logger.warning(f"Failed to generate embedding for chunk {i+1}")
    
    process_time = time.time() - start_time
    logger.info(f"Document processing completed in {process_time:.2f} seconds")
    
    return {
        "chunks": chunk_data,
        "chunk_count": len(chunks),
        "successful_embeddings": len(chunk_data),
        "processing_time": process_time
    }

# Add this function for semantic search

def vector_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 * magnitude2 == 0:
        return 0
    
    return dot_product / (magnitude1 * magnitude2)

def find_relevant_chunks(query: str, doc_name: str, top_k: int = 3):
    """Find the most relevant chunks for a query using semantic search."""
    if doc_name not in document_store or not document_store[doc_name].get("chunks"):
        return []
    
    # Get query embedding
    query_embedding = get_embedding(query)
    if not query_embedding:
        logger.warning("Could not generate embedding for query")
        return []
    
    # Get document chunks
    chunks = document_store[doc_name]["chunks"]
    
    # Calculate similarity scores
    chunk_scores = []
    for chunk in chunks:
        chunk_embedding = chunk.get("embedding")
        if chunk_embedding:
            similarity = vector_similarity(query_embedding, chunk_embedding)
            chunk_scores.append((chunk, similarity))
    
    # Sort by similarity score
    chunk_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top_k chunks
    return [chunk for chunk, score in chunk_scores[:top_k]]

# API routes
@app.route('/api/upload', methods=['POST'])
def upload_document():
    try:
        logger.info("Upload request received")
        
        if "file" not in request.files:
            logger.warning("No file part in request")
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files["file"]
        if file.filename == "":
            logger.warning("No selected file")
            return jsonify({"error": "No selected file"}), 400

        filename = file.filename
        file_ext = os.path.splitext(filename)[1].lower()
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        
        logger.info(f"Saving file: {filename} to {save_path}")
        try:
            file.save(save_path)
            logger.info(f"File saved successfully")
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return jsonify({"error": f"Could not save file: {e}"}), 500

        # Process the file based on its extension
        if file_ext == ".txt":
            logger.info("Processing text file")
            text = read_text_file(save_path)
        elif file_ext == ".pdf":
            logger.info("Processing PDF file")
            text = read_pdf_file(save_path)
            if not text or len(text.strip()) < 20:
                logger.info("Minimal or no text extracted; attempting vision OCR via LLM...")
                ocr_text = ocr_pdf_with_vlm(save_path)
                if ocr_text:
                    text = ocr_text
                    logger.info("Vision OCR succeeded; proceeding with embeddings.")
                else:
                    logger.warning("Vision OCR produced no text.")
        else:
            logger.warning(f"Unsupported file type: {file_ext}")
            return jsonify({"error": "Unsupported file type"}), 400

        if not text:
            logger.warning("No text extracted from file")
            return jsonify({"error": "No text extracted from file"}), 400

        logger.info(f"Extracted {len(text)} characters from file")
        
        # Process document with chunking if embeddings are available
        chunk_data = {"chunks": [], "chunk_count": 0, "successful_embeddings": 0}
        if HAS_EMBEDDING:
            logger.info("Processing document with chunking...")
            chunk_data = process_document_chunks(text)
            logger.info(f"Document processed into {chunk_data['chunk_count']} chunks with {chunk_data['successful_embeddings']} embeddings")
        
        # Save the document data in memory
        document_store[filename] = {
            "text": text,
            "chunks": chunk_data["chunks"],
            "path": save_path,
            "processed": True,
            "chunk_count": chunk_data["chunk_count"],
            "has_embeddings": chunk_data["successful_embeddings"] > 0
        }
        
        # After successful upload, auto-queue an extraction job
        try:
            max_pages = int(request.args.get('pages', 2))
        except Exception:
            max_pages = 2
        try:
            scale = float(request.args.get('scale', 1.6))
        except Exception:
            scale = 1.6
        model = request.args.get('model', 'gemma3:12b')

        # idempotent queue by file hash + options
        try:
            file_sha = _sha256_file(save_path)
        except Exception:
            file_sha = filename
        job_key = f"{file_sha}:{max_pages}:{scale}:{model}:v1"
        for jid, j in jobs_store.items():
            if j.get('job_key') == job_key and j.get('status') in ('queued','running'):
                job_id = jid
                break
        else:
            job_id = str(uuid.uuid4())
            jobs_store[job_id] = {
                'job_id': job_id,
                'filename': filename,
                'file_sha': file_sha,
                'job_key': job_key,
                'file_path': save_path,
                'status': 'queued',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'params': { 'max_pages': max_pages, 'scale': scale, 'model': model, 'agent_version': 'v1' },
                'events': [ { 'ts': datetime.now(timezone.utc).isoformat(), 'message': 'job queued (upload)'} ]
            }
            def _worker():
                try:
                    jobs_store[job_id]['status'] = 'running'
                    jobs_store[job_id]['events'].append({'ts': datetime.now(timezone.utc).isoformat(), 'message': 'job started'})
                    result_run = _run_entrydetail_job(save_path, max_pages=max_pages, scale=scale, model=model, agent_version='v1')
                    out_dir = _jobs_dir() / job_id
                    out_dir.mkdir(parents=True, exist_ok=True)
                    with open(out_dir / 'result.wrapper.json', 'w', encoding='utf-8') as f:
                        json.dump(result_run['wrapper'], f, indent=2)
                    with open(out_dir / 'summary.json', 'w', encoding='utf-8') as f:
                        json.dump({k: v for k, v in result_run.items() if k != 'wrapper'}, f, indent=2)
                    jobs_store[job_id].update({ 'status': 'done', 'elapsed_sec': result_run.get('elapsed_sec'), 'model': result_run.get('model'), 'updated_at': datetime.now(timezone.utc).isoformat() })
                    jobs_store[job_id]['events'].append({'ts': datetime.now(timezone.utc).isoformat(), 'message': 'job done'})
                except Exception as e:
                    jobs_store[job_id].update({ 'status': 'failed', 'error': str(e), 'updated_at': datetime.now(timezone.utc).isoformat() })
                    jobs_store[job_id].setdefault('events', []).append({'ts': datetime.now(timezone.utc).isoformat(), 'message': f'job failed: {e}'})
            threading.Thread(target=_worker, daemon=True).start()

        # Return success response with job id
        result = {
            "filename": filename,
            "text_excerpt": text[:200],
            "success": True,
            "message": f"Document uploaded and processed into {chunk_data['chunk_count']} chunks!",
            "chunk_count": chunk_data["chunk_count"],
            "successful_embeddings": chunk_data["successful_embeddings"],
            "processing_time": chunk_data.get("processing_time", 0),
            "job_id": job_id,
            "job_status": jobs_store.get(job_id,{}).get('status','queued')
        }
        
        if not chunk_data["chunks"]:
            result["warning"] = "Embeddings could not be generated. Semantic search will not be available."
            
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"Unexpected error in upload: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/api/documents', methods=['GET'])
def list_documents():
    docs = [{"name": name, "excerpt": data["text"][:100]} for name, data in document_store.items()]
    return jsonify(docs)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data or "message" not in data:
            return jsonify({"error": "No message provided"}), 400
        
        message = data["message"]
        use_documents = data.get("use_documents", False)
        document_names = data.get("documents", [])
        
        # Get model parameters
        model = data.get("model", DEFAULT_MODEL)
        temperature = data.get("temperature", DEFAULT_TEMPERATURE)
        max_tokens = data.get("max_tokens", DEFAULT_MAX_TOKENS)
        
        # Prepare context based on mode
        system_message = "You are a helpful assistant."
        
        # Process document if in document mode
        if use_documents and document_names:
            doc_name = document_names[0]
            if doc_name in document_store:
                # Use semantic search to find relevant chunks
                if document_store[doc_name].get("chunks"):
                    relevant_chunks = find_relevant_chunks(message, doc_name)
                    
                    if relevant_chunks:
                        # Combine relevant chunks for context
                        context_text = "\n\n---\n\n".join(chunk["text"] for chunk in relevant_chunks)
                        system_message = (
                            f"You are a helpful assistant. Use the following document excerpts as context to answer questions.\n\n"
                            f"Document: {doc_name}\n\n{context_text}"
                        )
                        logger.info(f"Using {len(relevant_chunks)} relevant chunks for context")
                    else:
                        # Fallback to using first part of document if no relevant chunks found
                        doc_text = document_store[doc_name]["text"]
                        system_message = f"You are a helpful assistant. Use the following document as context to answer questions:\n\n{doc_text[:2000]}"
                        logger.warning("No relevant chunks found, using document start instead")
                else:
                    # No chunks available, use regular document text
                    doc_text = document_store[doc_name]["text"]
                    system_message = f"You are a helpful assistant. Use the following document as context to answer questions:\n\n{doc_text[:2000]}"
        
        # Set up streaming response to LLM API
        def generate():
            # Call API with streaming enabled and selected parameters
            logger.info(f"Calling chat API with model: {model}, temp: {temperature}, max_tokens: {max_tokens}")
            response = requests.post(
                CHAT_ENDPOINT,
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": message}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True  # Enable streaming
                },
                stream=True  # Enable HTTP streaming
            )
            
            # Stream the response chunks to frontend
            for chunk in response.iter_lines():
                if chunk:
                    try:
                        chunk_data = chunk.decode('utf-8')
                        # Remove "data: " prefix if present (common in SSE)
                        if chunk_data.startswith("data: "):
                            chunk_data = chunk_data[6:]
                        
                        # Skip "[DONE]" message
                        if chunk_data.strip() == "[DONE]":
                            continue
                            
                        json_data = json.loads(chunk_data)
                        # Extract the text from the chunk
                        if 'choices' in json_data and len(json_data['choices']) > 0:
                            if 'delta' in json_data['choices'][0]:
                                content = json_data['choices'][0]['delta'].get('content', '')
                                if content:
                                    yield f"data: {json.dumps({'delta': content})}\n\n"
                    except Exception as e:
                        logger.error(f"Error processing chunk: {e}, chunk: {chunk}")
                        continue
            
            # Signal end of stream
            yield f"data: {json.dumps({'end': True})}\n\n"
            
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
    except Exception as e:
        logger.exception(f"Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

# Combined test endpoint with unique name to avoid conflicts
@app.route('/api/embedding-test', methods=['GET', 'POST'])
def test_embedding_api():
    try:
        # For POST requests, use the provided text
        if request.method == 'POST':
            data = request.json
            test_text = data.get('text', 'This is a test text for embedding.')
            logger.info(f"Testing embedding API with provided text: {test_text[:50]}...")
        else:  # For GET requests, use a default text
            test_text = "This is a test of the embedding API."
            logger.info(f"Testing embedding API with default text: {test_text}")
        
        # Generate embedding
        embedding = get_embedding(test_text)
        
        if embedding:
            return jsonify({
                "success": True,
                "message": "Embedding API is working correctly!",
                "dimensions": len(embedding),
                "sample": embedding[:5]
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to generate embedding. Check logs for details."
            }), 500
    except Exception as e:
        logger.exception(f"Error testing embedding API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "embedding_api": HAS_EMBEDDING
    })

# Add this new API endpoint

@app.route('/api/documents/clear', methods=['POST'])
def clear_documents():
    try:
        global document_store
        
        # Clear the in-memory document store
        document_count = len(document_store)
        document_store = {}
        
        # Optionally remove files from the uploads folder
        delete_files = request.json.get('delete_files', False)
        if delete_files:
            import shutil
            try:
                # Remove all files in upload folder
                shutil.rmtree(app.config["UPLOAD_FOLDER"])
                # Recreate the empty directory
                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                logger.info(f"Removed all files from {app.config['UPLOAD_FOLDER']}")
            except Exception as e:
                logger.error(f"Error removing files: {e}")
                return jsonify({"error": f"Cleared document store but failed to remove files: {e}"}), 500
        
        return jsonify({
            "success": True, 
            "message": f"Cleared {document_count} documents and their embeddings",
            "files_removed": delete_files
        })
    except Exception as e:
        logger.exception(f"Error clearing documents: {e}")
        return jsonify({"error": str(e)}), 500

# Add this endpoint to fetch available models

DEFAULT_MODEL = "gemma2:27b"  # Default chat model
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = -1

@app.route('/api/models', methods=['GET'])
def list_models():
    try:
        # Call the models endpoint of your local API
        response = requests.get(f"{LLM_API_URL}/models")
        
        if response.status_code == 200:
            models_data = response.json()
            return jsonify(models_data)
        else:
            logger.error(f"Failed to fetch models: {response.status_code}")
            return jsonify({
                "error": f"Failed to fetch models: {response.status_code}",
                # Fallback to a minimal set
                "data": [
                    {"id": "gemma2:27b"},
                ]
            }), 502
    except Exception as e:
        logger.exception(f"Error fetching models: {e}")
        return jsonify({
            "error": str(e),
            # Fallback
            "data": [
                {"id": "gemma2:27b"}
            ]
        }), 500

# ----------------------------
# Jobs API (vision-only EntryDetail extraction)
# ----------------------------

@app.route('/api/jobs', methods=['POST'])
def create_job():
    try:
        data = request.get_json(force=True)
        filename = data.get('filename')
        max_pages = int(data.get('max_pages', 2))
        scale = float(data.get('scale', 1.6))
        model = data.get('model', 'gemma3:12b')
        agent_version = data.get('agent_version', 'v1')

        if not filename:
            return jsonify({"error": "filename is required (must exist under uploads/)"}), 400
        file_path = filename
        if not os.path.isabs(file_path):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Synchronous execution (legacy endpoint keeps behavior)
        result = _run_entrydetail_job(file_path, max_pages=max_pages, scale=scale, model=model, agent_version=agent_version)

        # Persist artifacts under tmp/runs/jobs/<job_id>
        out_dir = _jobs_dir() / result["job_id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "result.wrapper.json", "w", encoding="utf-8") as f:
            json.dump(result["wrapper"], f, indent=2)
        with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in result.items() if k != "wrapper"}, f, indent=2)

        return jsonify({
            "job_id": result["job_id"],
            "elapsed_sec": result["elapsed_sec"],
            "model": result["model"],
            "local_validation": result["local_validation"],
            "result": result["wrapper"]
        })
    except Exception as e:
        logger.exception(f"Error creating job: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/jobs/<job_id>/result', methods=['GET'])
def get_job_result(job_id: str):
    try:
        p = Path("./tmp/runs/jobs") / job_id / "result.wrapper.json"
        if not p.exists():
            return jsonify({"error": "job result not found"}), 404
        with open(p, "r", encoding="utf-8") as f:
            wrapper = json.load(f)
        return jsonify(wrapper)
    except Exception as e:
        logger.exception(f"Error reading job result: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id: str):
    try:
        j = jobs_store.pop(job_id, None)
        # Remove artifacts directory if exists
        try:
            d = _jobs_dir() / job_id
            if d.exists():
                import shutil
                shutil.rmtree(d)
        except Exception as e:
            logger.warning(f"Could not remove artifacts for job {job_id}: {e}")
        if not j:
            return jsonify({"deleted": False, "message": "job not found"}), 404
        return jsonify({"deleted": True})
    except Exception as e:
        logger.exception(f"Error deleting job: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id: str):
    try:
        j = jobs_store.get(job_id)
        if not j:
            return jsonify({"error": "job not found"}), 404
        j['cancel'] = True
        j.setdefault('events', []).append({'ts': _utcnow_iso(), 'message': 'cancel requested'})
        if j.get('status') == 'queued':
            j['status'] = 'canceled'
            j['events'].append({'ts': _utcnow_iso(), 'message': 'job canceled'})
        elif j.get('status') == 'running':
            j['status'] = 'cancel_requested'
        j['updated_at'] = _utcnow_iso()
        return jsonify({"canceled": True, "status": j['status']})
    except Exception as e:
        logger.exception(f"Error canceling job: {e}")
        return jsonify({"error": str(e)}), 500

# Shipments API facade (versioned surface)

@app.route('/api/shipments/jobs', methods=['POST'])
def shipments_create_job():
    # Delegate to async job creation
    return create_job_async()

@app.route('/api/shipments/jobs/<job_id>', methods=['GET'])
def shipments_get_job(job_id: str):
    return get_job(job_id)

@app.route('/api/shipments/jobs/<job_id>/result', methods=['GET'])
def shipments_get_job_result(job_id: str):
    return get_job_result(job_id)

@app.route('/api/shipments/jobs/<job_id>', methods=['DELETE'])
def shipments_delete_job(job_id: str):
    return delete_job(job_id)

@app.route('/api/shipments/jobs/<job_id>/cancel', methods=['POST'])
def shipments_cancel_job(job_id: str):
    return cancel_job(job_id)


@app.route('/api/jobs/create', methods=['POST'])
def create_job_async():
    try:
        data = request.get_json(force=True)
        filename = data.get('filename')
        max_pages = int(data.get('max_pages', 2))
        scale = float(data.get('scale', 1.6))
        model = data.get('model', 'gemma3:12b')
        agent_version = data.get('agent_version', 'v1')

        if not filename:
            return jsonify({"error": "filename is required (must exist under uploads/)"}), 400
        file_path = filename
        if not os.path.isabs(file_path):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Compute file hash for robust idempotency
        base_fn = os.path.basename(file_path)
        try:
            file_sha = _sha256_file(file_path)
        except Exception as e:
            logger.exception(f"Failed to hash file {file_path}: {e}")
            file_sha = base_fn  # fallback to filename

        job_key = f"{file_sha}:{max_pages}:{scale}:{model}:{agent_version}"
        # De-dup: if a job for this hash+options is queued or running, return it
        for jid, j in jobs_store.items():
            if j.get('job_key') == job_key and j.get('status') in ('queued','running'):
                return jsonify({"job_id": jid, "status": j.get('status'), "dedup": True})

        job_id = str(uuid.uuid4())
        jobs_store[job_id] = {
            "job_id": job_id,
            "filename": base_fn,
            "file_sha": file_sha,
            "job_key": job_key,
            "file_path": file_path,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "params": {"max_pages": max_pages, "scale": scale, "model": model, "agent_version": agent_version}
        }

        def _evt(msg):
            try:
                jobs_store[job_id].setdefault('events', []).append({
                    'ts': datetime.now(timezone.utc).isoformat(),
                    'message': msg
                })
                jobs_store[job_id]['updated_at'] = datetime.now(timezone.utc).isoformat()
            except Exception:
                pass

        def _worker():
            try:
                jobs_store[job_id]["status"] = "running"
                _evt("job started")
                # If canceled before heavy work, exit early
                if jobs_store[job_id].get('cancel'):
                    jobs_store[job_id]['status'] = 'canceled'
                    _evt("job canceled before start")
                    return
                _evt("generating entry detail")
                result = _run_entrydetail_job(file_path, max_pages=max_pages, scale=scale, model=model, agent_version=agent_version)
                _evt("generation complete; saving artifacts")
                out_dir = _jobs_dir() / job_id
                out_dir.mkdir(parents=True, exist_ok=True)
                with open(out_dir / "result.wrapper.json", "w", encoding="utf-8") as f:
                    json.dump(result["wrapper"], f, indent=2)
                with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
                    json.dump({k: v for k, v in result.items() if k != "wrapper"}, f, indent=2)
                if jobs_store[job_id].get('cancel'):
                    jobs_store[job_id].update({
                        "status": "canceled",
                        "elapsed_sec": result.get("elapsed_sec"),
                        "model": result.get("model"),
                        "updated_at": _utcnow_iso(),
                    })
                    _evt("job canceled (post-run)")
                else:
                    jobs_store[job_id].update({
                        "status": "done",
                        "elapsed_sec": result.get("elapsed_sec"),
                        "model": result.get("model"),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
                    _evt("job done")
            except Exception as e:
                logger.exception(f"Job {job_id} failed: {e}")
                jobs_store[job_id].update({
                    "status": "failed",
                    "error": str(e),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                _evt(f"job failed: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        return jsonify({"job_id": job_id, "status": "queued"})
    except Exception as e:
        logger.exception(f"Error creating async job: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs', methods=['GET'])
def list_jobs_api():
    try:
        # Build list from in-memory store; augment done jobs with schema_ok/confidence if available
        jobs = []
        for jid, j in jobs_store.items():
            item = dict(j)
            try:
                item['size_bytes'] = os.path.getsize(j.get('file_path',''))
            except Exception:
                pass
            if j.get("status") == "done":
                p = _jobs_dir() / jid / "result.wrapper.json"
                if p.exists():
                    try:
                        with open(p, 'r', encoding='utf-8') as f:
                            wrapper = json.load(f)
                            val = wrapper.get('meta', {}).get('validation', {})
                            item['schema_ok'] = val.get('schema_ok')
                            item['overall_confidence'] = wrapper.get('meta', {}).get('overall_confidence')
                    except Exception:
                        pass
            jobs.append(item)
        # Sort newest first
        jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jsonify({"jobs": jobs})
    except Exception as e:
        logger.exception(f"Error listing jobs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id: str):
    try:
        j = jobs_store.get(job_id)
        if not j:
            return jsonify({"error": "job not found"}), 404
        item = dict(j)
        if j.get("status") == "done":
            p = _jobs_dir() / job_id / "result.wrapper.json"
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    wrapper = json.load(f)
                    val = wrapper.get('meta', {}).get('validation', {})
                    item['schema_ok'] = val.get('schema_ok')
                    item['overall_confidence'] = wrapper.get('meta', {}).get('overall_confidence')
        return jsonify(item)
    except Exception as e:
        logger.exception(f"Error reading job: {e}")
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == '__main__':
    port = 5001  # Use port 5001 to avoid conflict with AirPlay on Mac
    logger.info(f"Starting Flask server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
