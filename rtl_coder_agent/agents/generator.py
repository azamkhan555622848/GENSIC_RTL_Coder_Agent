"""GeneratorAgent – Gemini-Coder role.

Uses an LLM to turn a task plan (plus few-shot examples) into Verilog RTL.  The
current placeholder returns an empty module so that downstream tooling works in
unit tests.
"""
from __future__ import annotations

from typing import List
from ..claude import ClaudeClient

PROMPT_TEMPLATE = (
    "You are an expert RTL designer. Generate synthesizable SystemVerilog code "
    "that satisfies the following specification. The top-level module MUST be "
    "named exactly `TopModule` (case sensitive) so that the provided testbench "
    "can instantiate it. Ensure the design is simple, uses non-blocking assignments "
    "for sequential logic, and compiles under Icarus Verilog. Return *only* the code "
    "inside a fenced ```verilog``` block."
)

class GeneratorAgent:
    """Stub code generator."""

    def __init__(self, model: str | None = None):
        self.model = model or "claude-3-5-sonnet-20240620"  # Default to Claude
        self.llm = ClaudeClient()

    def generate(self, plan: dict, exemplars: List[str] | None = None) -> str:
        spec = plan.get("spec", "")
        
        # Combine system prompt and examples into one string
        system_instructions = PROMPT_TEMPLATE
        if exemplars:
            examples_text = "\n\n".join(exemplars[:3])
            system_instructions += "\n\nRelevant examples:\n" + examples_text
        
        # Claude API takes system prompt separately
        messages = [
            {"role": "user", "content": spec},
        ]

        raw_reply = self.llm.chat(messages, system_prompt=system_instructions)
        verilog_code = ClaudeClient.extract_verilog(raw_reply)
        return verilog_code 