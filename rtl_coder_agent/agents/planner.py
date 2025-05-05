"""PlannerAgent – Design Architect role.

Responsible for breaking down a natural‐language specification into a JSON task
plan and (optionally) retrieving few-shot exemplars from a vector DB.  For now
we implement a minimal stub that produces a trivial plan so that the overall
package is runnable even without LLM credentials.  Plugging in a real LLM call
is left as future work.
"""
from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path

from ..config import Config
from ..embedder import Embedder

_CORPUS_DIR = Path("verilog-eval-main/dataset_spec-to-rtl")


class PlannerAgent:
    """Stub planner that returns a simple canonical plan."""

    def __init__(self, model: str | None = None):
        self.model = model or "gpt-4o-mini"
        self.cfg = Config.load()
        self.embedder = Embedder(self.cfg.vector_db_path)
        self._ensure_corpus_ingested()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def plan(self, spec: str) -> Dict[str, Any]:
        """Return a dummy JSON plan for the given *spec*.

        In production, this would invoke an LLM with a system prompt
        instructing it to output a structured JSON task graph.
        """
        # Minimal viable plan
        return {
            "spec": spec,
            "tasks": [
                {"id": "rtl_gen", "desc": "Generate SystemVerilog for spec"},
                {"id": "lint", "desc": "Run Verilator lint"},
                {"id": "simulate", "desc": "Run testbench"},
            ],
        }

    def retrieve_examples(self, spec: str, k: int = 3) -> List[str]:
        """Return *k* example RTL specs from vector store."""
        return self.embedder.query(spec, k=k)

    def _ensure_corpus_ingested(self) -> None:
        """On first run, lazily embed the VerilogEval corpus into FAISS."""
        if self.embedder.index.ntotal > 0:
            return
        if not _CORPUS_DIR.exists():
            return
        specs: List[str] = []
        for prompt_file in _CORPUS_DIR.glob("*_prompt.txt"):
            spec_text = prompt_file.read_text().strip()
            specs.append(spec_text)
        self.embedder.add_corpus(specs) 