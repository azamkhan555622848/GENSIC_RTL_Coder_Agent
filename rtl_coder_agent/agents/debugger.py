"""DebuggerAgent – Patch Bot role.

Iteratively fixes RTL based on lint or simulation failures.  Currently a stub
that simply returns the original RTL unchanged.
"""
from __future__ import annotations

from typing import Any
from ..claude import ClaudeClient

FIX_PROMPT_TEMPLATE = (
    "You are an expert Verilog engineer tasked with fixing code. "
    "Given the original code and an error report, output ONLY the corrected "
    "lines inside a fenced ```diff``` block. Do not repeat unchanged lines."
)

class DebuggerAgent:
    """Stub debugger that no-ops for now."""

    def __init__(self, model: str | None = None):
        self.model = model or "claude-3-5-sonnet-20240620"
        self.llm = ClaudeClient()

    # ------------------------------------------------------------------
    def fix(self, rtl_code: str, error_report: Any) -> str:  # noqa: ANN401
        report_text = str(error_report)
        
        # Combine context for user message
        user_content = f"Original code:\n```verilog\n{rtl_code}\n```\n\nErrors:\n{report_text}"
        
        # System prompt passed separately to Claude API
        system_prompt = FIX_PROMPT_TEMPLATE

        messages = [
            {"role": "user", "content": user_content}
        ]
        reply = self.llm.chat(messages, system_prompt=system_prompt)
        diff_text = reply.strip()
        if getattr(error_report, "error_class", "") == "COMPILE_ERROR":
            system_prompt = (
                FIX_PROMPT_TEMPLATE
                + "\nYou are given SystemVerilog code that fails to compile under Icarus Verilog."
                + " Rewrite the entire module so that it compiles and keeps the intended behaviour."
                + " Always output a single fenced ```verilog``` block only."
            )
            user_message = (
                "Compiler errors:\n" + str(error_report.stderr)
                + "\n\nBroken code:\n```verilog\n" + rtl_code + "\n```"
            )
            reply = self.llm.chat([{"role": "user", "content": user_message}], system_prompt=system_prompt)
            fixed = ClaudeClient.extract_verilog(reply)
            return fixed

        # fallback – no change
        return rtl_code 