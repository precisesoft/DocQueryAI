import os
import json
import logging
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from PyPDF2 import PdfReader

# Add these imports
import re
import time
import numpy as np
from typing import List, Dict, Any

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
LLM_API_URL = "http://localhost:1234/v1"
EMBEDDING_ENDPOINT = f"{LLM_API_URL}/embeddings"
CHAT_ENDPOINT = f"{LLM_API_URL}/chat/completions"
EMBEDDING_MODEL = "text-embedding-bge-m3"
CHAT_MODEL = "deepseek-r1-distill-qwen-32b-mlx"

# Store uploaded documents in memory
document_store = {}

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
        
        # Return success response
        result = {
            "filename": filename,
            "text_excerpt": text[:200],
            "success": True,
            "message": f"Document uploaded and processed into {chunk_data['chunk_count']} chunks!",
            "chunk_count": chunk_data["chunk_count"],
            "successful_embeddings": chunk_data["successful_embeddings"],
            "processing_time": chunk_data.get("processing_time", 0)
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
            # Call API with streaming enabled
            logger.info(f"Calling chat API with streaming")
            response = requests.post(
                CHAT_ENDPOINT,
                headers={"Content-Type": "application/json"},
                json={
                    "model": CHAT_MODEL,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": message}
                    ],
                    "temperature": 0.7,
                    "max_tokens": -1,
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

# Run the app
if __name__ == '__main__':
    port = 5001  # Use port 5001 to avoid conflict with AirPlay on Mac
    logger.info(f"Starting Flask server on port {port}")
    app.run(debug=True, port=port)