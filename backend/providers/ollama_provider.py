import os
import json
from typing import Iterator, List, Dict, Optional

import requests


class OllamaProvider:
    """OpenAI-compatible provider (Ollama/OpenAI API shape).

    Defaults:
    - Base URL: `LLM_API_URL` if set; else `${OLLAMA_BASE_URL}/v1` with default `http://localhost:11434/v1`.
    - Embedding model: `bge-m3`
    - Chat model: `gemma2:27b`
    """

    def __init__(self) -> None:
        self.base_url = self._resolve_base_url()
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "bge-m3")
        self.chat_model = os.getenv("CHAT_MODEL", "gemma2:27b")

    def _resolve_base_url(self) -> str:
        # Highest precedence: explicit API URL
        api_url = os.getenv("LLM_API_URL")
        if api_url:
            return api_url.rstrip("/")

        # Next: derive from Ollama base
        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        return f"{ollama_base}/v1"

    # Embeddings
    def embed(self, text: str, model: Optional[str] = None, timeout: Optional[float] = None) -> List[float]:
        url = f"{self.base_url}/embeddings"
        payload = {
            "model": model or self.embedding_model,
            "input": text,
        }
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            # OpenAI-compatible response: {"data":[{"embedding":[...] }]} or {"embedding": [...]}
            if "data" in data and data["data"]:
                item = data["data"][0]
                if isinstance(item, dict) and "embedding" in item:
                    return item["embedding"]
            if "embedding" in data:
                return data["embedding"]  # Non-standard direct embedding
        return []

    # Streaming chat completion; yields content deltas (strings)
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Iterator[str]:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, object] = {
            "model": model or self.chat_model,
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None and max_tokens >= 0:
            payload["max_tokens"] = max_tokens

        with requests.post(url, json=payload, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            for raw in resp.iter_lines():
                if not raw:
                    continue
                try:
                    line = raw.decode("utf-8")
                except Exception:
                    continue
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]" or line.strip() == "data: [DONE]":
                    # End of stream marker
                    break
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                # Standard OpenAI streaming shape
                try:
                    choices = obj.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta") or {}
                        content = delta.get("content")
                        if content:
                            yield content
                except Exception:
                    continue

    # List available models in {"data": [{"id": "..."}, ...]} shape
    def list_models(self, timeout: Optional[float] = None) -> List[Dict[str, str]]:
        url = f"{self.base_url}/models"
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        payload = r.json()
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            out: List[Dict[str, str]] = []
            for item in payload["data"]:
                if isinstance(item, dict) and "id" in item:
                    out.append({"id": str(item["id"])})
                elif isinstance(item, str):
                    out.append({"id": item})
            return out
        # Some servers might return a bare list
        if isinstance(payload, list):
            return [{"id": str(x)} for x in payload]
        return []

