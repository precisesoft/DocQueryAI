import os
import json
import requests
from PyPDF2 import PdfReader  # pip install PyPDF2

EMBEDDING_ENDPOINT = "http://127.0.0.1:11434/v1/embeddings"
MODEL_NAME = "bge-m3"

def read_text_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def read_pdf_file(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def get_embedding(text):
    payload = {
        "model": MODEL_NAME,
        "text": text
    }
    response = requests.post(EMBEDDING_ENDPOINT, json=payload, stream=True)
    embedding = []
    print("Streaming response:")
    for chunk in response.iter_lines(decode_unicode=True):
        if chunk:
            try:
                data = json.loads(chunk)
                print(data)  # Print the streamed JSON chunk
                if "embedding_chunk" in data:
                    embedding.extend(data["embedding_chunk"])
            except json.JSONDecodeError:
                print("Non-json chunk:", chunk)
    print("Final embedding:", embedding)
    return embedding

def process_documents(folder_path):
    embeddings_data = {}
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".txt") or file.endswith(".pdf"):
                file_path = os.path.join(root, file)
                print(f"Processing {file_path}...")
                if file.endswith(".txt"):
                    text = read_text_file(file_path)
                else:  # handle PDFs
                    text = read_pdf_file(file_path)
                # Optionally preprocess or split text here if needed
                embedding = get_embedding(text)
                if embedding:
                    embeddings_data[file_path] = {
                        "text": text,
                        "embedding": embedding
                    }
    return embeddings_data

def save_embeddings(embeddings_data, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(embeddings_data, f, indent=2)

if __name__ == "__main__":
    folder_path = "./documents"  # Update this path to your actual document folder
    output_file = "embeddings.json"  # The file where embeddings and metadata will be stored
    embeddings_data = process_documents(folder_path)
    save_embeddings(embeddings_data, output_file)
    print(f"Embeddings saved to {output_file}")
