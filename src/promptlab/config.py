"""Central configuration.

Everything that can vary between machines (keys, model names, paths) lives here
and is read from the environment, never hard-coded at a call site. This keeps the
rest of the code pure and dependency-injectable.
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

    # --- LLM (OpenAI-compatible). One client drives OpenAI, Groq, and Gemini's
    # OpenAI-compatible endpoints — the model dropdown just swaps base_url + key. ---
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_temperature: float = 0.0
    llm_timeout_seconds: float = 30.0

    # Extra provider keys, so the UI can offer more than one provider at once
    # without re-editing .env between runs. Empty ones are simply unavailable.
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # --- Judge ---
    # The model PromptLab uses to score candidate answers. Kept separate from the
    # models under test so the judge stays fixed while you vary the prompts.
    judge_model: str = "llama-3.3-70b-versatile"

    # --- Paths ---
    db_path: Path = Field(default=REPO_ROOT / "promptlab.db")
    experiments_dir: Path = Field(default=REPO_ROOT / "experiments")
    exports_dir: Path = Field(default=REPO_ROOT / "exports")

    # --- API server ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    # Origins allowed to call the API from a browser (the Vite dev server).
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    def has_llm(self) -> bool:
        """True when at least one real LLM call is possible."""
        return bool(self.llm_api_key or self.openai_api_key or self.groq_api_key or self.gemini_api_key)


def load_settings() -> Settings:
    """Factory so tests can build isolated Settings without import-time side effects."""
    return Settings()
