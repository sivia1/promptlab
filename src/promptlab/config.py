"""Central configuration.

Everything that can vary between machines (model names, paths, ports) lives here
and is read from the environment, never hard-coded at a call site. API keys are
handled separately by the KeyStore (Settings page + env fallback), not here.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = three parents up from this file (src/promptlab/config.py -> repo).
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings, populated from environment variables and an optional .env."""

    model_config = SettingsConfigDict(
        env_prefix="PROMPTLAB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Inference defaults (a run can override per experiment) ---
    llm_timeout_seconds: float = 60.0
    default_temperature: float = 0.0
    default_max_tokens: int = 1024

    # --- Key storage ---
    # Off by default: a freshly deployed instance cannot persist a pasted key to
    # server-side disk at all, so there is nothing there for another visitor to
    # reuse or leak. Flip this on only when self-hosting for yourself alone (the
    # UI then also offers "save on this server" as well as BYOK-per-request).
    allow_stored_keys: bool = False

    # --- Judge (the fixed, neutral referee) ---
    # One model scores every candidate answer so cross-model comparison is fair.
    # It must not be one of the models under test's own provider grading itself.
    judge_provider: str = "groq"
    judge_model: str = "llama-3.3-70b-versatile"

    # --- Paths ---
    keystore_path: Path = Field(default=REPO_ROOT / ".promptlab_keys.json")
    db_path: Path = Field(default=REPO_ROOT / "promptlab.db")
    experiments_dir: Path = Field(default=REPO_ROOT / "experiments")
    exports_dir: Path = Field(default=REPO_ROOT / "exports")

    # --- API server ---
    # Port 8100 (not the common 8000) to avoid clashing with other local dev
    # servers that habitually take 8000.
    api_host: str = "127.0.0.1"
    api_port: int = 8100
    # Origins allowed to call the API from a browser (the Vite dev server on 5174).
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5174", "http://127.0.0.1:5174"]
    )


def load_settings() -> Settings:
    """Factory so tests can build isolated Settings without import-time side effects."""
    return Settings()
