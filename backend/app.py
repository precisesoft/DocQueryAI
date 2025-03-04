import os
import json
import logging
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from PyPDF2 import PdfReader

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
        
        # Get embedding for the document if service is available
        embedding = []
        if HAS_EMBEDDING:
            logger.info("Generating embedding...")
            embedding = get_embedding(text)
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
        else:
            logger.warning("Embedding service not available, skipping embedding generation")
        
        # Save the document data in memory
        document_store[filename] = {
            "text": text,
            "embedding": embedding,
            "path": save_path
        }
        
        # Return success response
        result = {
            "filename": filename,
            "text_excerpt": text[:200],
            "success": True,
            "message": "Document uploaded successfully and ready for chat!",
            "has_embedding": len(embedding) > 0
        }
        
        if not embedding:
            result["warning"] = "Embeddings could not be generated. Some features may be limited."
            
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
        if use_documents and document_names:
            doc_name = document_names[0]
            if doc_name in document_store:
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