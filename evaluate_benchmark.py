# evaluate_benchmark.py
import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

# Ensure the agent package is importable
# Add the parent directory to sys.path if running this script directly
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from rtl_coder_agent.agents.orchestrator import RTLCoderOrchestrator
from rtl_coder_agent.config import Config

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)
# Silence the very verbose agent logs during batch runs, show orchestrator logs
logging.getLogger("rtl_coder_agent.agents.planner").setLevel(logging.WARNING)
logging.getLogger("rtl_coder_agent.agents.generator").setLevel(logging.WARNING)
logging.getLogger("rtl_coder_agent.agents.debugger").setLevel(logging.WARNING)
logging.getLogger("rtl_coder_agent.agents.simulator").setLevel(logging.WARNING)
logging.getLogger("rtl_coder_agent.claude").setLevel(logging.WARNING)

logger = logging.getLogger("evaluate_benchmark")


def get_problem_paths(dataset_dir: Path) -> list[tuple[str, Path, Path]]:
    """Finds all problem specifications and their corresponding testbenches."""
    problems = []
    prompt_files = sorted(list(dataset_dir.glob("Prob*_prompt.txt")))
    for prompt_path in prompt_files:
        problem_id = prompt_path.stem.replace("_prompt", "")
        test_path = dataset_dir / f"{problem_id}_test.sv"
        if test_path.exists():
            problems.append((problem_id, prompt_path, test_path))
        else:
            logger.warning(f"Testbench not found for {problem_id}, skipping.")
    return problems

def parse_run_log(log_file: Path) -> tuple[str, int | None]:
    """Parses the run log to find success/failure and attempt count."""
    try:
        with log_file.open("r") as f:
            for line in reversed(f.readlines()): # Check last lines first
                try:
                    entry = json.loads(line)
                    if entry.get("event") == "success":
                        return "pass", entry.get("attempts")
                    if entry.get("event") == "failure":
                        return "fail", entry.get("attempts")
                except json.JSONDecodeError:
                    continue # Ignore malformed lines if any
        return "unknown", None # Should not happen if run completed
    except Exception as e:
        logger.error(f"Error parsing log file {log_file}: {e}")
        return "error", None


def run_evaluation(dataset_dir: Path, output_dir: Path, max_attempts: int, limit: int | None = None):
    """Runs the orchestrator on all problems in the dataset."""
    problems = get_problem_paths(dataset_dir)
    if limit:
        problems = problems[:limit]
        logger.info(f"Running evaluation on the first {limit} problems.")
    else:
         logger.info(f"Running evaluation on all {len(problems)} problems.")

    results = {}
    start_time = time.time()

    # Ensure the temporary workdir used by the orchestrator is cleaned up
    # or a fresh one is created each time if needed.
    # The default orchestrator uses tempfile.mkdtemp() which is fine.
    # We reuse the same config object for API keys etc.
    cfg = Config.load()
    run_log_dir = cfg.log_dir # Get log dir from config

    for i, (problem_id, prompt_path, test_path) in enumerate(problems):
        logger.info(f"--- Running Problem {i+1}/{len(problems)}: {problem_id} ---")
        problem_start_time = time.time()
        orch = RTLCoderOrchestrator(max_attempts=max_attempts)
        spec_text = prompt_path.read_text()
        output_file = output_dir / f"{problem_id}_generated.sv"
        run_id = orch.logger.run_id # Get the unique ID for this run
        run_log_file = None

        try:
            generated_rtl = orch.run(spec_text, test_path)
            # Find the log file for this specific run
            run_log_file = next(run_log_dir.glob(f"run_*_{run_id}.jsonl"), None)
            status, attempts = parse_run_log(run_log_file) if run_log_file else ("pass_run_success_no_log", max_attempts +1) # assume pass if run() returns

            if status.startswith("pass"):
                logger.info(f"Result: PASS (Attempt {attempts})")
                results[problem_id] = {"status": "pass", "attempts": attempts}
                output_file.write_text(generated_rtl)
            else:
                # This case should ideally not happen if run() succeeded, but handle defensively
                logger.warning(f"Run succeeded but log parsing showed '{status}'. Treating as pass.")
                results[problem_id] = {"status": "pass", "attempts": attempts or max_attempts} # Assume max attempts if None
                output_file.write_text(generated_rtl)

        except RuntimeError:
            # Find the log file for this specific run
            run_log_file = next(run_log_dir.glob(f"run_*_{run_id}.jsonl"), None)
            status, attempts = parse_run_log(run_log_file) if run_log_file else ("fail_no_log", max_attempts)
            logger.error(f"Result: FAIL (After {attempts} attempts)")
            results[problem_id] = {"status": "fail", "attempts": attempts}
        except Exception as e:
             logger.exception(f"Unexpected error running {problem_id}: {e}")
             results[problem_id] = {"status": "error", "attempts": 0}
        finally:
             if run_log_file:
                logger.debug(f"Parsed log file: {run_log_file.name}")
             else:
                logger.error(f"Could not find log file for run_id {run_id}")

        problem_duration = time.time() - problem_start_time
        logger.info(f"Problem {problem_id} finished in {problem_duration:.2f}s")


    total_duration = time.time() - start_time
    logger.info(f"\n--- Evaluation Summary ---")
    logger.info(f"Total problems run: {len(results)}")
    logger.info(f"Total time: {total_duration:.2f}s")

    # Calculate pass@k
    total_problems = len(results)
    passes = defaultdict(int)
    failures = 0
    errors = 0

    for res in results.values():
        if res["status"] == "pass":
            for k in range(res["attempts"], max_attempts + 1):
                passes[k] += 1
        elif res["status"] == "fail":
            failures += 1
        else:
            errors +=1

    if total_problems > 0:
        print("\n--- Pass@k Scores ---")
        for k in range(1, max_attempts + 1):
            pass_rate = (passes[k] / total_problems) * 100
            print(f"Pass@{k}: {passes[k]}/{total_problems} ({pass_rate:.2f}%)")
        fail_rate = (failures / total_problems) * 100
        error_rate = (errors / total_problems) * 100
        print(f"Failed: {failures}/{total_problems} ({fail_rate:.2f}%)")
        if errors > 0:
             print(f"Errors: {errors}/{total_problems} ({error_rate:.2f}%)")
    else:
        print("No problems were run.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RTL Coder Agent on VerilogEval benchmark.")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("verilog-eval-main/dataset_spec-to-rtl"),
        help="Path to the VerilogEval dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmark_output"),
        help="Directory to save generated RTL files for successful runs",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=3,
        help="Maximum attempts per problem (should match orchestrator)",
    )
    parser.add_argument(
         "--limit",
         type=int,
         default=None,
         help="Limit run to the first N problems (for quick testing)"
    )
    args = parser.parse_args()

    if not args.dataset_dir.exists():
        sys.exit(f"Error: Dataset directory not found at {args.dataset_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    run_evaluation(args.dataset_dir, args.output_dir, args.attempts, args.limit) 