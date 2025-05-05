"""Utility module for interacting with Anthropic Claude via anthropic SDK."""
from __future__ import annotations

import logging
import re
from typing import List

import anthropic

from .config import Config

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Thin wrapper around the Anthropic API with sane defaults."""

    _instance: "ClaudeClient" | None = None

    def __new__(cls):  # noqa: D401
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_once()
        return cls._instance

    # ------------------------------------------------------------------
    def _init_once(self) -> None:  # noqa: D401
        cfg = Config.load()
        self.client = anthropic.Anthropic(api_key=cfg.sonnet_api_key)
        self.model_name = "claude-3-5-sonnet-20240620"  # Default to Sonnet 3.5
        logger.info("Anthropic client initialised with model %s", self.model_name)

    # ------------------------------------------------------------------
    def chat(self, messages: List[dict], system_prompt: str | None = None) -> str:
        """Call Claude with chat-style messages and return the text reply."""
        # Filter out system messages, as Claude takes it as a separate parameter
        user_messages = [msg for msg in messages if msg.get("role") != "system"]

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,  # Generous limit for RTL code
                temperature=0.7,
                system=system_prompt,  # Use the dedicated system parameter
                messages=user_messages,
            )
            # Response structure is different, access content block
            if response.content and isinstance(response.content, list):
                # Assuming the first block is the text reply
                text_block = next((block for block in response.content if hasattr(block, 'text')), None)
                if text_block:
                    return text_block.text
            return ""  # Return empty if no suitable text block found
        except Exception as exc:  # noqa: BLE001
            logger.error("Anthropic request failed: %s", exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    @staticmethod
    def extract_verilog(text: str) -> str:
        """Return first fenced `verilog` or backtick block, else raw text."""
        match = re.search(r"```(?:verilog|systemverilog|sv)\s*\n(.*?)```", text, flags=re.S | re.I)
        if match:
            return match.group(1).strip()
        match2 = re.search(r"```\s+(.*?)```", text, flags=re.S)
        if match2:
            return match2.group(1).strip()
        return text.strip() 