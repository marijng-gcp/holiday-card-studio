"""Tests for PII redaction pipeline."""

from __future__ import annotations

from app.observability.pii_redactor import PIIRedactor


def test_pii_redactor_scrubs_emails_phones_ips_and_keys() -> None:
    """Ensure regex fallback redacts all sensitive patterns in text and dicts."""
    redactor = PIIRedactor(enable_cloud_dlp=False)
    payload = {
        "guest_note": "Reach me at alex.smith@example.com or +49 170 1234567",
        "nested": ["IP 192.168.1.42", "key AIzaSyDummyKey1234567890123456"],
    }
    scrubbed = redactor.redact_dict(payload)
    assert "[EMAIL_REDACTED]" in scrubbed["guest_note"]
    assert "[PHONE_REDACTED]" in scrubbed["guest_note"]
    assert "[IP_REDACTED]" in scrubbed["nested"][0]
    assert "[SECRET_REDACTED]" in scrubbed["nested"][1]
    assert "alex.smith@example.com" not in scrubbed["guest_note"]
