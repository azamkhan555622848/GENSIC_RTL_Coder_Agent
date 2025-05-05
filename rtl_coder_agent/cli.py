"""Command-line entry-point for RTL Coder Agent.

Example usage
-------------
python -m rtl_coder_agent.cli spec.txt tb.sv --attempts 3 --out rtl_out.sv
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .agents.orchestrator import RTLCoderOrchestrator

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def _parse_args() -> argparse.Namespace:  # noqa: D401
    """Build ArgumentParser and parse CLI arguments."""
    parser = argparse.ArgumentParser(description="RTL-Coder Agent CLI runner")
    parser.add_argument("spec_file", type=Path, help="Path to text file containing NL spec")
    parser.add_argument("testbench", type=Path, help="Path to Verilog testbench (SV)")
    parser.add_argument("--out", type=Path, default=Path("design_out.sv"), help="Where to write generated RTL")
    parser.add_argument("--attempts", type=int, default=3, help="Maximum regeneration attempts (default: 3)")
    return parser.parse_args()


def main() -> None:  # noqa: D401
    """Entrypoint callable for `python -m rtl_coder_agent.cli`."""
    args = _parse_args()

    if not args.spec_file.exists():
        sys.exit(f"Spec file not found: {args.spec_file}")
    if not args.testbench.exists():
        sys.exit(f"Testbench not found: {args.testbench}")

    spec_text = args.spec_file.read_text()
    orch = RTLCoderOrchestrator(max_attempts=args.attempts)

    try:
        rtl = orch.run(spec_text, args.testbench)
    except RuntimeError as exc:
        logging.error("Generation failed: %s", exc)
        sys.exit(1)

    args.out.write_text(rtl)
    logging.info("Success – RTL written to %s", args.out)


if __name__ == "__main__":
    main() 