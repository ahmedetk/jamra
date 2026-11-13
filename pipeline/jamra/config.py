"""Load config.yaml and secrets. Code written with an SI coding assistant (Claude Code)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@lru_cache
def load() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


def path(key: str) -> Path:
    p = Path(load()["paths"][key])
    return p if p.is_absolute() else (ROOT / p).resolve()


def secret(name: str) -> str:
    """Read a secret from the environment (CI) or the local secrets file."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    f = path("secrets")
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name:
                return v.strip()
    return ""
