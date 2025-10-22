import os
from typing import Protocol, Iterator, List, Dict, Optional


class Provider(Protocol):
    """LLM provider protocol for pluggable backends."""

    # Embeddings
    def embed(self, text: str, model: Optional[str] = None, timeout: Optional[float] = None) -> List[float]:
        ...

    # Streaming chat completion; yields content deltas
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Iterator[str]:
        ...

    # List available models, OpenAI-compatible shape: [{"id": "model"}, ...]
    def list_models(self, timeout: Optional[float] = None) -> List[Dict[str, str]]:
        ...


def select_provider_name(req=None) -> str:
    """Select provider name with per-request override.

    Priority:
    1) Query string `provider`
    2) JSON body `provider`
    3) Env `LLM_PROVIDER`
    4) Default 'ollama'
    """
    # Per-request override via query
    if req is not None and hasattr(req, "args"):
        provider = req.args.get("provider")
        if provider:
            return provider.lower()

    # Per-request override via JSON
    if req is not None:
        try:
            body = req.get_json(silent=True) if hasattr(req, "get_json") else None
        except Exception:
            body = None
        if isinstance(body, dict):
            provider = body.get("provider")
            if provider:
                return provider.lower()

    # Env default
    env_provider = os.getenv("LLM_PROVIDER")
    if env_provider:
        return env_provider.lower()

    # Fallback default
    return "ollama"


def get_provider(req=None) -> Provider:
    """Return a provider instance based on selection for this request.

    If `req` is None, uses environment defaults.
    """
    name = select_provider_name(req)
    if name == "bedrock":
        # Lazy import to avoid optional deps for other providers
        from .bedrock_provider import BedrockProvider

        return BedrockProvider()
    # Default to ollama
    from .ollama_provider import OllamaProvider

    return OllamaProvider()

