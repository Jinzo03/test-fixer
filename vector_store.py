import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from google import genai


class SemanticMemory:
    """Vector store for semantic text chunks powered by Gemini embeddings."""

    def __init__(
        self,
        memory_file: str = "store/semantic_memory.json",
        embedding_model: str = "gemini-embedding-001",
    ):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.embedding_model = embedding_model
        self.memory_path = Path(memory_file)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.memory_path.exists():
            self.memory_path.write_text("[]", encoding="utf-8")

    def _get_embedding(self, text: str) -> list[float]:
        """Fetch dense vector embedding for a block of text."""
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=text,
        )
        if hasattr(response, "embedding") and response.embedding:
            return response.embedding.values
        if hasattr(response, "embeddings") and response.embeddings:
            return response.embeddings[0].values
        raise ValueError("No embedding returned from Gemini API.")

    def add_documents(self, chunks: list[dict[str, str]]) -> None:
        """Stores text chunks alongside their vector embeddings.
        
        Expected item structure in `chunks`: 
        {"source": "paper.txt", "content": "..."}
        """
        existing_data = self.load_data()

        for chunk in chunks:
            vector = self._get_embedding(chunk["content"])
            existing_data.append({
                "source": chunk.get("source", "unknown"),
                "content": chunk["content"],
                "embedding": vector,
            })

        self.memory_path.write_text(
            json.dumps(existing_data, indent=2), encoding="utf-8"
        )

    def load_data(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Performs cosine similarity search between query and stored vectors."""
        data = self.load_data()
        if not data:
            return []

        query_vec = np.array(self._get_embedding(query))

        results = []
        for item in data:
            doc_vec = np.array(item["embedding"])
            # Cosine similarity formula: (A . B) / (||A|| * ||B||)
            norm_product = np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
            sim = float(np.dot(query_vec, doc_vec) / norm_product) if norm_product != 0 else 0.0

            results.append({
                "source": item["source"],
                "content": item["content"],
                "similarity": sim,
            })

        # Sort descending by similarity score
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]