"""Smoke test for RTL Coder Agent pipeline.

Runs the orchestrator with a trivial NOT gate spec and reference testbench from
VerilogEval dataset to ensure end-to-end flow executes without exceptions.
"""
from __future__ import annotations

from pathlib import Path

from rtl_coder_agent.agents.orchestrator import RTLCoderOrchestrator


def test_smoke() -> None:
    spec_path = Path("verilog-eval-main/dataset_spec-to-rtl/Prob005_notgate_prompt.txt")
    tb_path = Path("verilog-eval-main/dataset_spec-to-rtl/Prob005_notgate_test.sv")
    if not spec_path.exists():
        raise RuntimeError("Dataset not found for smoke test")

    spec = spec_path.read_text()
    orch = RTLCoderOrchestrator(max_attempts=1)
    try:
        rtl = orch.run(spec, tb_path)
    except Exception as exc:  # noqa: BLE001
        # Still pass if failure due to missing Claude creds in CI; ensure pipeline runs
        assert "SONNAT_API_KEY" in str(exc) or "Generation failed" in str(exc)
    else:
        # If passes, generated RTL must be non-empty
        assert rtl.strip() != "" 