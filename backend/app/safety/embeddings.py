from abc import ABC, abstractmethod

import httpx
from app.core.config import get_settings
from app.core.errors import ApiError


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible embedding provider (e.g., Groq, OpenAI)."""

    def __init__(self, api_key: str, base_url: str, model: str = "text-embedding-3-small", expected_dimension: int = 1536):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._expected_dimension = expected_dimension
        self._dimension = expected_dimension  # Will be validated on first embedding

    def embed_text(self, text: str) -> list[float]:
        result = self.embed_texts([text])
        return result[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            response = httpx.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"input": texts, "model": self.model},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]

            # Validate embedding dimension
            if embeddings:
                actual_dim = len(embeddings[0])
                if actual_dim != self._expected_dimension:
                    raise ApiError(
                        500,
                        "EMBEDDING_DIMENSION_MISMATCH",
                        f"Embedding dimension mismatch: expected {self._expected_dimension}, got {actual_dim}. "
                        f"Model '{self.model}' may have changed. Update EMBEDDING_DIMENSION configuration."
                    )

            return embeddings
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ApiError(503, "EMBEDDING_UNAVAILABLE", "Embedding service is temporarily unavailable.") from exc

    @property
    def dimension(self) -> int:
        return self._dimension


def get_embedding_provider() -> EmbeddingProvider:
    """Factory function to get the configured embedding provider."""
    settings = get_settings()
    if settings.groq_api_key is None:
        raise ApiError(503, "EMBEDDING_UNAVAILABLE", "Embedding provider is not configured.")
    # Using Groq's OpenAI-compatible embeddings endpoint
    return OpenAIEmbeddingProvider(
        api_key=settings.groq_api_key.get_secret_value(),
        base_url=str(settings.groq_base_url),
        model=settings.embedding_model,
        expected_dimension=settings.embedding_dimension,
    )
