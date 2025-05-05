"""Runtime configuration management for RTL Coder Agent."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

# attempt to load .env using python-dotenv if available
try:
    import dotenv

    _SEARCH_PATHS: List[Path] = [
        Path.cwd(),  # current working dir
        Path(__file__).parent,  # rtl_coder_agent/
        Path(__file__).parent / "agents",  # rtl_coder_agent/agents/
    ]

    for p in _SEARCH_PATHS:
        env_path = p / ".env"
        if env_path.exists():
            dotenv.load_dotenv(env_path, override=False)
            break
except ModuleNotFoundError:  # pragma: no cover
    # python-dotenv optional; ignore if not installed
    pass

@dataclass
class Config:
    """Centralised runtime config pulled from environment variables."""

    # Anthropic LLM creds
    sonnet_api_key: str

    # Vector DB
    vector_db_path: Path

    # Telemetry
    log_dir: Path

    # ------------------------------------------------------------------
    @classmethod
    def load(cls) -> "Config":
        env = os.environ
        sonnet_key = env.get("SONNAT_API_KEY")
        if not sonnet_key:
            raise RuntimeError("SONNAT_API_KEY not set in environment")

        vector_db_path = Path(env.get("VECTOR_DB_PATH", "./faiss_index"))
        log_dir = Path(env.get("RUN_LOG_DIR", "./run_logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        vector_db_path.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            sonnet_api_key=sonnet_key,
            vector_db_path=vector_db_path,
            log_dir=log_dir,
        ) 