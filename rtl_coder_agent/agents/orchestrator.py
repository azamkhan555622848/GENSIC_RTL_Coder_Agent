"""RTLCoderOrchestrator – high-level pipeline controller.

The orchestrator wires together the different agent roles (planner, coder,
linter, simulator, debugger) into the closed-loop described in
ImplementationPlan.md.  Each role is represented by a light-weight Python class
wrapping either an external tool (Verilator, Icarus) or an LLM call (OpenAI /
Gemini).  The orchestrator exposes a single entry-point `run(spec, tb_path)`
that returns the final RTL string (or raises if failing after N attempts).
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from .planner import PlannerAgent
from .generator import GeneratorAgent
from .linter import LinterTool
from .simulator import SimulatorTool
from .debugger import DebuggerAgent
from ..telemetry import RunLogger

logger = logging.getLogger(__name__)


class RTLCoderOrchestrator:
    """Main class that coordinates the RTL-generation workflow."""

    def __init__(
        self,
        max_attempts: int = 3,
        workdir: Optional[Path] = None,
        model_planner: str | None = "gpt-4o-mini",
        model_generator: str | None = "gemini-2.5-pro",
        model_debugger: str | None = "gemini-2.5-pro",
    ) -> None:
        self.max_attempts = max_attempts
        self.workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp())
        self.planner = PlannerAgent(model=model_planner)
        self.coder = GeneratorAgent(model=model_generator)
        self.linter = LinterTool()
        self.sim = SimulatorTool()
        self.debugger = DebuggerAgent(model=model_debugger)
        self.logger = RunLogger()

        # ensure working directory exists
        self.workdir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, spec: str, tb_path: Path | str) -> str:
        """Generate and verify RTL given a natural-language *spec* and a testbench path.

        Parameters
        ----------
        spec : str
            Natural-language design specification.
        tb_path : Path | str
            Path to the Verilog testbench to use for simulation.

        Returns
        -------
        str
            Functionally correct Verilog RTL code that passes the testbench.

        Raises
        ------
        RuntimeError
            If generation fails to pass the testbench after *max_attempts*.
        """
        tb_path = Path(tb_path)

        self.logger.emit("start", spec_len=len(spec))

        # ------------------------------------------------------------------
        # 1. Plan decomposition (Design Architect role)
        # ------------------------------------------------------------------
        plan = self.planner.plan(spec)
        logger.debug("Task plan generated: %s", plan)
        self.logger.emit("plan", tasks=len(plan.get("tasks", [])))

        # Fetch few-shot exemplars (Prompt Curator)
        examples = self.planner.retrieve_examples(spec)

        # ------------------------------------------------------------------
        # 2. First-pass RTL generation (Gemini Coder role)
        # ------------------------------------------------------------------
        rtl_code = self.coder.generate(plan=plan, exemplars=examples)

        # ------------------------------------------------------------------
        # 3. Static lint before simulation (Lint Guardian)
        # ------------------------------------------------------------------
        lint_errors = self.linter.check(rtl_code)
        if lint_errors:
            logger.info("Lint found %d issues – invoking debugger patch", len(lint_errors))
            rtl_code = self.debugger.fix(rtl_code, lint_errors)
            self.logger.emit("lint_errors", count=len(lint_errors))

        # ------------------------------------------------------------------
        # 4. Simulation loop with iterative patching (Sim Runner / Patch Bot)
        # ------------------------------------------------------------------
        for attempt in range(1, self.max_attempts + 1):
            logger.info("Simulation attempt %d/%d", attempt, self.max_attempts)
            sim_ok, sim_log = self.sim.run(rtl_code, tb_path, self.workdir)
            self.logger.emit("sim", attempt=attempt, success=sim_ok)
            if sim_ok:
                logger.info("Design passes testbench on attempt %d", attempt)
                self.logger.emit("success", attempts=attempt)
                self.logger.close()
                return rtl_code

            # Failure – patch only affected regions
            logger.warning("Simulation failed, invoking debugger. Error class: %s", sim_log.error_class)
            self.logger.emit("sim_fail", attempt=attempt, error_class=sim_log.error_class, stderr=sim_log.stderr)
            rtl_code = self.debugger.fix(rtl_code, sim_log)

        # ------------------------------------------------------------------
        # 5. Exhausted regeneration budget
        # ------------------------------------------------------------------
        self.logger.emit("failure", attempts=self.max_attempts)
        self.logger.close()
        logger.error("Failed to generate correct RTL after %d attempts", self.max_attempts)
        raise RuntimeError("RTL generation failed") 