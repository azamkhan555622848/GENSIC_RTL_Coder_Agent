"""LinterTool – Verilator lint wrapper."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import List


class LintError(Exception):
    """Simple structured lint error container."""

    def __init__(self, line: int, msg: str):
        self.line = line
        self.msg = msg

    def __repr__(self) -> str:  # pragma: no cover
        return f"LintError(line={self.line}, msg={self.msg!r})"


class LinterTool:
    """Executes `verilator --lint-only` and parses warnings/errors."""

    def __init__(self):
        self._regex = re.compile(r"%Error:.*?(\d+): (.*)")

    # ------------------------------------------------------------------
    def check(self, rtl_code: str) -> List[LintError]:
        """Run Verilator lint; return list of errors (empty if clean)."""
        with tempfile.TemporaryDirectory() as td:
            src_path = Path(td) / "design.sv"
            src_path.write_text(rtl_code)

            cmd = [
                "verilator",
                "--quiet",
                "--lint-only",
                "--sv",
                str(src_path),
            ]
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return []
            except subprocess.CalledProcessError as exc:
                output = exc.stderr or exc.stdout
                return self._parse_output(output)

    # ------------------------------------------------------------------
    def _parse_output(self, text: str) -> List[LintError]:
        errs: List[LintError] = []
        for match in self._regex.finditer(text):
            line = int(match.group(1))
            msg = match.group(2).strip()
            errs.append(LintError(line=line, msg=msg))
        return errs 