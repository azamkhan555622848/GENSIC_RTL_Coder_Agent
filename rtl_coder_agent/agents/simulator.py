"""SimulatorTool – compile & run testbench with Icarus Verilog."""
from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class SimulationLog:
    stdout: str
    stderr: str
    error_class: str = "SIM_FAILURE"


class SimulatorTool:
    """Wraps iverilog + vvp to run a testbench and capture pass/fail."""

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    def run(self, rtl_code: str, tb_path: Path, workdir: Path) -> Tuple[bool, SimulationLog]:
        tb_path = Path(tb_path)
        workdir = Path(workdir)

        # Determine the path to the reference module file
        ref_path_str = str(tb_path).replace("_test.sv", "_ref.sv")
        ref_path = Path(ref_path_str)
        if not ref_path.exists():
            logger.warning("Reference module file not found at %s", ref_path)
            ref_path = None # Continue without it, might fail compilation

        # Prepare design file
        design_path = workdir / "design.sv"
        design_path.write_text(rtl_code)

        # Compile design and testbench
        compile_files = [str(design_path), str(tb_path)]
        if ref_path:
            compile_files.append(str(ref_path))

        cmd_compile = [
            "iverilog",
            "-g2012",  # Use SystemVerilog 2012 standard
            "-o",
            str(workdir / "design.vvp"),
            *compile_files,
        ]
        compile_res = subprocess.run(cmd_compile, capture_output=True, text=True)
        if compile_res.returncode != 0:
            # include only first 40 lines of stderr to keep prompt small
            err_snippet = "\n".join(compile_res.stderr.splitlines()[:40])
            return False, SimulationLog(compile_res.stdout, err_snippet, error_class="COMPILE_ERROR")

        # Run simulation
        run_res = subprocess.run(["vvp", str(workdir / "design.vvp")], capture_output=True, text=True)
        ok = run_res.returncode == 0
        err_cls = "PASS" if ok else "SIM_FAIL"
        return ok, SimulationLog(run_res.stdout, run_res.stderr, error_class=err_cls) 