"""Single point of access for config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and return the YAML config as a plain dict."""
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
