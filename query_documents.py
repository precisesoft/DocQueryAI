import json
import math
import requests

EMBEDDING_FILE = "embeddings.json"
LLM_ENDPOINT = "http://localhost:1234/v1/chat/completions"
LLM_MODEL = "deepseek-r1-distill-qwen-32b-mlx"

def load_embeddings(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_embedding(text):
    # Dummy embedding for testing; in production, replace with an API call if needed.
    embedding = [0.123, 0.456, 0.789, 0.012, 0.345]
    return embedding

def cosine_similarity(vec_a, vec_b):
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0
    return dot / (norm_a * norm_b)

def search_documents(query_embedding, embeddings_data, top_k=3):
    similarities = []
    for doc_path, data in embeddings_data.items():
        doc_embedding = data.get("embedding")
        if doc_embedding:
            sim = cosine_similarity(query_embedding, doc_embedding)
            similarities.append((doc_path, sim, data["text"]))
    # sort by similarity in descending order
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]

def call_llm(query, context, stream=True):
    # Format a prompt that combines the context and query
    prompt = f"Context:\n{context}\n\nQuestion: {query}"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "Use the provided document context to answer the question."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": stream
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(LLM_ENDPOINT, headers=headers, json=payload, stream=stream)
    
    if stream:
        final_answer = ""
        try:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    # Remove any prefix if needed (e.g., "data:")
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    # End of stream marker (could be "[DONE]" or similar depending on your API)
                    if line == "[DONE]":
                        break
                    data = json.loads(line)
                    # Access delta content if available
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    chunk = delta.get("content", "")
                    print(chunk, end="", flush=True)
                    final_answer += chunk
        except Exception as e:
            print("\nError reading stream:", e)
        print()  # Ensure newline after streaming
        # Return a dummy structure that mimics non-streamed response for further processing.
        return {"choices": [{"message": {"content": final_answer}}]}
    else:
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error from LLM: {response.status_code} {response.text}")
            return None

def main():
    embeddings_data = load_embeddings(EMBEDDING_FILE)
    # Prompt the user to input their question
    query = input("Enter your question: ")
    query_embedding = get_embedding(query)
    top_docs = search_documents(query_embedding, embeddings_data)

    if not top_docs:
        print("No relevant documents found.")
        return

    # Concatenate the text of top documents as context
    context = "\n-----\n".join(doc_text for _, sim, doc_text in top_docs)
    # print("Retrieved Context:")
    # print(context)
    
    # Enable streaming in the call_llm function
    llm_response = call_llm(query, context, stream=True)
    
    if llm_response:
        # Assuming the LLM returns a 'choices' field with message content
        answer = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if "</think>" in answer:
            thoughts, final_answer = answer.split("</think>", 1)
            print("\nThought Process:")
            print(thoughts.strip())
            print("\nFinal Answer:")
            print(final_answer.strip())
        else:
            print("\nLLM Answer:")
            print(answer)
    else:
        print("Failed to get a response from LLM.")

if __name__ == "__main__":
    main()