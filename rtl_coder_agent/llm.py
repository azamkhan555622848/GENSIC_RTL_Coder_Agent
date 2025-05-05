"""Utility module for interacting with Google Gemini via google-generativeai SDK."""
from __future__ import annotations

import logging
import re
from typing import List

import google.generativeai as genai

from .config import Config

logger = logging.getLogger(__name__)


class GeminiClient:
    """Thin wrapper around the Gemini API with sane defaults."""

    _instance: "GeminiClient" | None = None

    def __new__(cls):  # noqa: D401
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_once()
        return cls._instance

    # ------------------------------------------------------------------
    def _init_once(self) -> None:  # noqa: D401
        cfg = Config.load()
        genai.configure(api_key=cfg.gemini_api_key)
        self.model_name = "gemini-1.5-pro-latest"
        # System instruction will be passed per-call
        self.model = genai.GenerativeModel(self.model_name)
        logger.info("Gemini client initialised with model %s", self.model_name)

    # ------------------------------------------------------------------
    def chat(self, messages: List[dict]) -> str:
        """Call Gemini with chat-style messages and return the text reply."""
        # Convert messages to SDK format (including system message if present)
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            # Gemini SDK expects 'model' role for assistant replies, not 'assistant'
            if role == "assistant":
                role = "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        try:
            response = self.model.generate_content(
                contents=contents,
                generation_config=genai.types.GenerationConfig(temperature=0.7),
            )
            text = response.text
            return text
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini request failed: %s", exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    @staticmethod
    def extract_verilog(text: str) -> str:
        """Return first fenced `verilog` or backtick block, else raw text."""
        match = re.search(r"```verilog\s+(.*?)```", text, flags=re.S | re.I)
        if match:
            return match.group(1).strip()
        match2 = re.search(r"```\s+(.*?)```", text, flags=re.S)
        if match2:
            return match2.group(1).strip()
        return text.strip() 