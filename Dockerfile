# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

# -----------------------------------------------------------------------------
# System deps
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates git curl \
    verilator iverilog yosys \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Working directory & Python deps
# -----------------------------------------------------------------------------
WORKDIR /workspace
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# -----------------------------------------------------------------------------
# Copy source
# -----------------------------------------------------------------------------
COPY . /workspace

# -----------------------------------------------------------------------------
# Default command
# -----------------------------------------------------------------------------
ENTRYPOINT ["python", "-m", "rtl_coder_agent.cli"] 