"""Server-side API-key store.

Backs the Settings page's optional "save on this server" mode and the judge's
own key. Two sources, and the stored file wins when both are present:

* **Env vars** — always readable. The twelve-factor way to configure a
  single-operator instance (e.g. the judge's own key).
* **A gitignored JSON file** — only readable/writable at all when
  ``allow_stored_keys`` is true (``Settings.allow_stored_keys``, off by
  default). When it's false, this store behaves as if the file doesn't exist,
  *even if one is sitting on disk* — a stale file from an earlier local run
  can't come back to life just because it wasn't deleted. This is what keeps a
  freshly deployed, publicly reachable instance from serving whatever key
  happens to be in that file to every visitor.

The primary path for a multi-user deployment is BYOK instead: the caller sends
their own key with each request (``RunConfig.api_key``) and it is never
persisted here at all — see ``runner.py``.

The API never returns a raw key (only a masked form), and keys are never
logged.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

# Providers that can hold a key, and the env var checked as a fallback.
_ENV_FALLBACK = {
    "openai": "PROMPTLAB_OPENAI_API_KEY",
    "anthropic": "PROMPTLAB_ANTHROPIC_API_KEY",
    "gemini": "PROMPTLAB_GEMINI_API_KEY",
    "groq": "PROMPTLAB_GROQ_API_KEY",
    "openrouter": "PROMPTLAB_OPENROUTER_API_KEY",
}


def mask(key: str) -> str:
    """A safe-to-display form of a key: last 4 chars only."""
    if not key:
        return ""
    tail = key[-4:] if len(key) >= 4 else key
    return f"…{tail}"


class KeyStore:
    """Reads/writes provider keys from a JSON file, falling back to env vars.

    ``allow_stored`` gates the file entirely, not just writes: when false, the
    file is never read either, so a stale file left over from an earlier
    (permissive) run can't silently supply keys to a now-locked-down instance.
    """

    def __init__(self, path: Path, *, allow_stored: bool = True):
        self.path = Path(path)
        self.allow_stored = allow_stored
        self._data: dict[str, str] = {}
        if self.allow_stored and self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def get(self, provider: str) -> str:
        """Effective key: the stored file value wins, else the env fallback."""
        stored = self._data.get(provider, "") if self.allow_stored else ""
        if stored:
            return stored
        env_var = _ENV_FALLBACK.get(provider)
        return os.environ.get(env_var, "") if env_var else ""

    def set(self, provider: str, key: str) -> None:
        if not self.allow_stored:
            raise PermissionError("Stored keys are disabled on this deployment.")
        if provider not in _ENV_FALLBACK:
            raise ValueError(f"Unknown provider {provider!r}")
        self._data[provider] = key.strip()
        self._flush()

    def delete(self, provider: str) -> None:
        if not self.allow_stored:
            raise PermissionError("Stored keys are disabled on this deployment.")
        self._data.pop(provider, None)
        self._flush()

    def status(self) -> dict[str, dict]:
        """Per-provider config status for the Settings page (masked, never raw)."""
        out = {}
        for provider in _ENV_FALLBACK:
            key = self.get(provider)
            stored = bool(self._data.get(provider)) if self.allow_stored else False
            out[provider] = {
                "configured": bool(key),
                "masked": mask(key),
                "source": "stored" if stored else ("env" if key else "none"),
            }
        return out

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        # Best-effort tighten permissions so other local users can't read it.
        with contextlib.suppress(OSError):
            self.path.chmod(0o600)
