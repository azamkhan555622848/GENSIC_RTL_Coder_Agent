"""Vector store based on FAISS + SentenceTransformers."""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import List, Tuple

import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class Embedder:
    """Lazy-initialised singleton managing vector index + mapping."""

    _instance: "Embedder" | None = None

    def __new__(cls, index_path: Path):  # noqa: D401
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_once(index_path)
        return cls._instance

    # ------------------------------------------------------------------
    def _init_once(self, index_path: Path) -> None:  # noqa: D401
        self.index_path = index_path
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self._id_to_text: List[str] = []

        if index_path.exists():
            logger.info("Loading FAISS index from %s", index_path)
            self.index = faiss.read_index(str(index_path))
            mapping_path = index_path.with_suffix(".json")
            self._id_to_text = json.loads(mapping_path.read_text())
        else:
            logger.warning("FAISS index %s not found; starting empty", index_path)
            self.index = faiss.IndexFlatIP(384)  # 384 dims for MiniLM

    # ------------------------------------------------------------------
    def add_corpus(self, records: List[str]) -> None:
        if not records:
            return
        embeds = self.model.encode(records, convert_to_numpy=True, normalize_embeddings=True)
        self.index.add(embeds)
        self._id_to_text.extend(records)
        self._persist()

    # ------------------------------------------------------------------
    def query(self, text: str, k: int = 3) -> List[str]:
        if self.index.ntotal == 0:
            return []
        query_emb = self.model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
        scores, idx = self.index.search(query_emb, k)
        idx = idx[0]
        results = [self._id_to_text[i] for i in idx if i < len(self._id_to_text)]
        return results

    # ------------------------------------------------------------------
    def _persist(self) -> None:
        logger.info("Persisting FAISS index to %s", self.index_path)
        with open(self.index_path, "wb") as fh:
            fh.write(faiss.serialize_index(self.index))
        mapping_path = self.index_path.with_suffix(".json")
        mapping_path.write_text(json.dumps(self._id_to_text)) 