"""Utilities to safely log payloads while redacting secrets."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_REDACTION_TEXT = "***REDACTED***"
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[a-z0-9._\-]+")
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "token",
    "secret",
    "password",
    "x-api-key",
)


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redact known secret fields and bearer values."""
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, raw_val in value.items():
            key_str = str(key)
            if _is_sensitive_key(key_str):
                redacted[key_str] = _REDACTION_TEXT
            else:
                redacted[key_str] = redact_sensitive_data(raw_val)
        return redacted

    if isinstance(value, str):
        cleaned = _BEARER_RE.sub(f"Bearer {_REDACTION_TEXT}", value)
        if cleaned.lower().startswith("sk-"):
            return _REDACTION_TEXT
        return cleaned

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_sensitive_data(item) for item in value]

    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)

