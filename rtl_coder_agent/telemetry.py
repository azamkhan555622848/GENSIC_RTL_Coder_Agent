"""Light-weight JSONL run logger."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .config import Config


class RunLogger:
    """Writes structured JSON lines for a single agent run."""

    def __init__(self) -> None:
        cfg = Config.load()
        self.run_id = uuid.uuid4().hex[:8]
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        self.path = cfg.log_dir / f"run_{ts}_{self.run_id}.jsonl"
        self._fh = self.path.open("w", encoding="utf-8")

    # ------------------------------------------------------------------
    def emit(self, event: str, **fields: Any) -> None:  # noqa: D401
        payload: Dict[str, Any] = {
            "time": time.time(),
            "event": event,
            **fields,
        }
        json.dump(payload, self._fh)
        self._fh.write("\n")
        self._fh.flush()

    # ------------------------------------------------------------------
    def close(self) -> None:  # noqa: D401
        self._fh.close() 