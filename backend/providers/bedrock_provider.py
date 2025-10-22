from typing import Iterator, List, Dict, Optional


class BedrockProvider:
    """AWS Bedrock provider stub. Implemented in later tasks."""

    def __init__(self) -> None:
        pass

    def embed(self, text: str, model: Optional[str] = None, timeout: Optional[float] = None) -> List[float]:
        raise NotImplementedError("Bedrock embeddings not implemented yet")

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Iterator[str]:
        raise NotImplementedError("Bedrock chat streaming not implemented yet")

    def list_models(self, timeout: Optional[float] = None) -> List[Dict[str, str]]:
        raise NotImplementedError("Bedrock list models not implemented yet")

