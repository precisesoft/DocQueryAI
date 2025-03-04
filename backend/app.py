import os
import json
import requests
import logging
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS
from PyPDF2 import PdfReader

app = Flask(__name__)
# Enable CORS for all routes with proper configuration
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
app.config["UPLOAD_FOLDER"] = "./uploads"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Connect to your local OpenAI-compatible API
LLM_API_URL = "http://localhost:1234/v1"
EMBEDDING_ENDPOINT = f"{LLM_API_URL}/embeddings"
CHAT_ENDPOINT = f"{LLM_API_URL}/chat/completions"
EMBEDDING_MODEL = "text-embedding-bge-m3"
CHAT_MODEL = "deepseek-r1-distill-qwen-32b-mlx"

# Store uploaded documents in memory for the chat feature
document_store = {}

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def read_text_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading text file: {e}")
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
        print(f"Error reading PDF file: {e}")
        return ""

def get_embedding(text):
    payload = {
        "model": EMBEDDING_MODEL,
        "text": text
    }
    try:
        response = requests.post(EMBEDDING_ENDPOINT, json=payload, stream=True)
        response.raise_for_status()  # raise an error for bad responses
    except requests.RequestException as e:
        print(f"Error calling embedding endpoint: {e}")
        return []

    embedding = []
    print("Streaming response:")
    for chunk in response.iter_lines(decode_unicode=True):
        if chunk:
            try:
                data = json.loads(chunk)
                print(data)
                if "embedding_chunk" in data:
                    embedding.extend(data["embedding_chunk"])
            except json.JSONDecodeError:
                print("Non-json chunk:", chunk)
    print("Final embedding:", embedding)
    return embedding

@app.before_request
def log_request():
    logger.debug(f"Request received: {request.method} {request.path}")
    logger.debug(f"Headers: {request.headers}")
    logger.debug(f"Data: {request.get_data()}")

@app.route('/')
def index():
    return render_template("index.html")

# Ensure these routes match what the frontend is calling:
@app.route('/api/upload', methods=['POST'])
def upload():
    print("Upload request received")
    if "file" not in request.files:
        print("No file part in request")
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    print(f"Received file: {file.filename}")

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = file.filename
    file_ext = os.path.splitext(filename)[1].lower()
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    try:
        file.save(save_path)
    except Exception as e:
        return jsonify({"error": f"Could not save file: {e}"}), 500

    # Process the file based on its extension
    if file_ext == ".txt":
        text = read_text_file(save_path)
    elif file_ext == ".pdf":
        text = read_pdf_file(save_path)
    else:
        return jsonify({"error": "Unsupported file type"}), 400

    if not text:
        return jsonify({"error": "No text extracted from file"}), 400

    embedding = get_embedding(text)
    
    # Save the document data in memory for chat feature
    document_store[filename] = {
        "text": text,
        "embedding": embedding,
        "path": save_path
    }
    
    result = {
        "filename": filename,
        "embedding": embedding,
        "text_excerpt": text[:200]  # first 200 characters as excerpt
    }
    return jsonify(result)

@app.route('/api/documents', methods=['GET'])
def list_documents():
    documents = [{"filename": name, "path": data["path"]} for name, data in document_store.items()]
    return jsonify(documents)

# Add a general chat endpoint that doesn't use documents
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
            collected_chunks = []
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
                                    collected_chunks.append(content)
                                    yield f"data: {json.dumps({'text': content})}\n\n"
                    except Exception as e:
                        print(f"Error processing chunk: {e}, chunk: {chunk}")
                        continue
            
            # Signal end of stream
            yield f"data: {json.dumps({'end': True})}\n\n"
            
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({"status": "API is working"})

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Changed from 5000 to 5001