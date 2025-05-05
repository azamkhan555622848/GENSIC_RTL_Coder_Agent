# RTL Coder Agent

This project implements an AI agent designed to generate synthesizable SystemVerilog RTL (Register-Transfer Level) code from natural language specifications. It leverages Large Language Models (LLMs), specifically Anthropic's Claude Sonnet 3.5, along with standard Verilog simulation tools to create and verify hardware designs.

## Features

*   **Natural Language Specification:** Takes plain text descriptions of hardware modules as input.
*   **LLM-Powered Generation:** Uses Claude Sonnet 3.5 via the Anthropic API to generate initial Verilog code.
*   **Simulation & Verification:** Compiles and simulates the generated code against a provided SystemVerilog testbench using Icarus Verilog (`iverilog` and `vvp`).
*   **Iterative Debugging:** Includes a debugger agent that attempts to fix compilation or simulation errors by prompting the LLM with the error context.
*   **Multi-Agent Architecture:** Employs distinct agent roles:
    *   `PlannerAgent`: Analyzes the spec and retrieves relevant few-shot examples (using a FAISS vector store).
    *   `GeneratorAgent`: Performs the initial code generation.
    *   `SimulatorTool`: Wraps Icarus Verilog for compilation and simulation.
    *   `DebuggerAgent`: Attempts to fix errors based on simulator feedback.
    *   `RTLCoderOrchestrator`: Coordinates the workflow between agents.
*   **Benchmarking:** Includes a script (`evaluate_benchmark.py`) to run the agent against the VerilogEval benchmark and calculate pass@k scores.

## Setup

The recommended way to set up and run the agent is using Docker, which ensures all system dependencies (Python, iverilog, Verilator, etc.) are correctly installed.

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd RTL-Coder-Agent
    ```

2.  **Build the Docker Image:**
    ```bash
    docker build -t rtl-coder .
    ```

3.  **Configure API Key:**
    *   Create a file named `.env` in the project root directory.
    *   Add your Anthropic API key to it:
        ```dotenv
        SONNAT_API_KEY=sk-ant-api03-...
        ```
    *   Alternatively, you can pass the key directly via the `-e` flag in `docker run` commands.

## Usage

Ensure the Docker image (`rtl-coder`) is built and the API key is configured (either in `.env` or via `-e`).

### Running a Single Problem

This uses the default `ENTRYPOINT` defined in the `Dockerfile` (`python -m rtl_coder_agent.cli`).

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd):/workspace" \
  rtl-coder \
  verilog-eval-main/dataset_spec-to-rtl/Prob005_notgate_prompt.txt \
  verilog-eval-main/dataset_spec-to-rtl/Prob005_notgate_test.sv \
  --out /workspace/generated_notgate.sv
```

*   `--env-file .env`: Loads the API key from your `.env` file.
*   `-v "$(pwd):/workspace"`: Mounts the current directory into the container.
*   The positional arguments are the specification file and the testbench file.
*   `--out`: Specifies the output file path *inside the container*.

### Evaluating on the VerilogEval Benchmark

This uses the `evaluate_benchmark.py` script and requires overriding the default Docker entrypoint.

```bash
docker run --rm -it \
  --entrypoint "" \
  --env-file .env \
  -v "$(pwd):/workspace" \
  rtl-coder \
  python evaluate_benchmark.py --output-dir /workspace/benchmark_output --limit 10
```

*   `--entrypoint ""`: Overrides the default entrypoint.
*   `python evaluate_benchmark.py ...`: The command to run inside the container.
*   `--output-dir`: Directory *inside the container* where generated RTL for passing problems will be saved.
*   `--limit 10`: (Optional) Limit the run to the first 10 problems for testing. Remove to run the full benchmark.

The script will output progress and final pass@k scores.

## Project Structure

```
├── Dockerfile
├── requirements.txt
├── .env.example          # Example environment variables
├── evaluate_benchmark.py # Script to run benchmark evaluation
├── rtl_coder_agent/      # Core agent source code
│   ├── __init__.py
│   ├── agents/           # Individual agent roles (orchestrator, generator, etc.)
│   ├── cli.py            # Command-line interface
│   ├── config.py         # Configuration loading
│   ├── claude.py         # Claude API client
│   ├── embedder.py       # Vector DB / FAISS embedder
│   └── telemetry.py      # Run logging
├── verilog-eval-main/    # VerilogEval benchmark dataset (submodule or copy)
│   └── dataset_spec-to-rtl/
├── run_logs/             # Output directory for detailed run logs (.jsonl)
├── benchmark_output/     # Default output directory for generated files from evaluate_benchmark.py
└── faiss_index/          # Default directory for the FAISS vector index
```

## Dependencies

*   **Python 3.11+**
*   **Docker** (Recommended for running)
*   **System Tools (Handled by Dockerfile):**
    *   `iverilog` (Icarus Verilog Simulator)
    *   `vvp` (Icarus Verilog Runtime)
    *   `verilator` (For linting - future use)
    *   `yosys` (For synthesis - future use)
*   **Python Packages:** See `requirements.txt` (includes `anthropic`, `faiss-cpu`, `numpy`, `python-dotenv`).

## Configuration

The agent requires the following environment variable:

*   `SONNAT_API_KEY`: Your API key for the Anthropic (Claude) API.

Optional variables (with defaults):

*   `VECTOR_DB_PATH`: Path to the FAISS index file (default: `./faiss_index`).
*   `RUN_LOG_DIR`: Directory for `.jsonl` run logs (default: `./run_logs`).

Load these by creating a `.env` file in the project root or setting them directly in your environment/Docker command. 