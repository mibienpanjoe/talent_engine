"""Synthetic embedding oracle. Network adapters tested separately."""

from talent_engine.integrations.embeddings import EmbeddingResult


class ControlledEmbeddings:
    model = "synthetic-embedding-v1"
    dimensions = 2

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(texts)
        return EmbeddingResult(
            [[1.0, 0.0] for _ in texts],
            self.model,
            self.dimensions,
            "synthetic",
            0,
            None,
        )
