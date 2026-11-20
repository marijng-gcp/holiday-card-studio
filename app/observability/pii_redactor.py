"""PII redaction pipeline using Google Cloud DLP with deterministic regex fallback."""

from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s\-().]{7,}\d)(?!\w)")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_API_KEY_RE = re.compile(r"\b(?:AIza[0-9A-Za-z\-_]{20,}|sk-[0-9A-Za-z]{16,})\b")


class PIIRedactor:
    """Scrubs sensitive data before logging or persisting session/memory records."""

    def __init__(self, project_id: str = "", enable_cloud_dlp: bool = False) -> None:
        self._project_id = project_id
        self._enable_cloud_dlp = enable_cloud_dlp and bool(project_id)
        self._dlp_client: Any = None

    def _get_dlp_client(self) -> Any:
        if self._dlp_client is None:
            from google.cloud import dlp_v2

            self._dlp_client = dlp_v2.DlpServiceClient()
        return self._dlp_client

    def redact_text(self, text: str) -> str:
        """Redact PII from a string using Cloud DLP (if enabled) and regex scrubbing.

        Args:
            text: Raw text that may contain emails, phone numbers, IPs, or keys.

        Returns:
            Sanitized string with sensitive tokens replaced by placeholders.
        """
        if not text:
            return text

        sanitized = self._regex_redact(text)
        if not self._enable_cloud_dlp:
            return sanitized

        try:
            client = self._get_dlp_client()
            parent = f"projects/{self._project_id}/locations/global"
            inspect_config = {
                "info_types": [
                    {"name": "EMAIL_ADDRESS"},
                    {"name": "PHONE_NUMBER"},
                    {"name": "IP_ADDRESS"},
                    {"name": "CREDIT_CARD_NUMBER"},
                ]
            }
            deidentify_config = {
                "info_type_transformations": {
                    "transformations": [
                        {"primitive_transformation": {"replace_with_info_type_config": {}}}
                    ]
                }
            }
            response = client.deidentify_content(
                request={
                    "parent": parent,
                    "deidentify_config": deidentify_config,
                    "inspect_config": inspect_config,
                    "item": {"value": sanitized},
                }
            )
            return str(response.item.value)
        except Exception:
            return sanitized

    def redact_dict(self, payload: Any) -> Any:
        """Recursively redact PII across nested dicts and lists.

        Args:
            payload: Arbitrary JSON-like structure.

        Returns:
            Deep-copied structure with string values scrubbed.
        """
        if isinstance(payload, str):
            return self.redact_text(payload)
        if isinstance(payload, list):
            return [self.redact_dict(item) for item in payload]
        if isinstance(payload, dict):
            return {k: self.redact_dict(v) for k, v in payload.items()}
        return payload

    @staticmethod
    def _regex_redact(text: str) -> str:
        text = _EMAIL_RE.sub("[EMAIL_REDACTED]", text)
        text = _API_KEY_RE.sub("[SECRET_REDACTED]", text)
        text = _IP_RE.sub("[IP_REDACTED]", text)
        text = _PHONE_RE.sub("[PHONE_REDACTED]", text)
        return text
