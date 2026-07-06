"""API-specific configuration."""

from __future__ import annotations

import os

# CORS origins allowed to call the API (frontend dev server + optional overrides).
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "API_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

# Path to the LLM routing config, used when constructing the pipeline.
LLM_CONFIG_PATH: str = os.getenv("LLM_CONFIG_PATH", "configs/llm.yaml")
