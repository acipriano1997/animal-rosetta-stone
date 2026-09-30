"""D0019 provenance-safe identifier helpers for PR0005/RDC-004."""
from __future__ import annotations

import hashlib
import hmac


def pseudonymize_source_id(raw_id: str, secret: bytes) -> str:
    value = str(raw_id).strip()
    if not value:
        raise ValueError("Source identity is missing")
    if not secret:
        raise ValueError("Runtime pseudonymization secret is required")
    return hmac.new(secret, ("D0019|" + value).encode(), hashlib.sha256).hexdigest()


def unordered_dyad_id(initiator_pseudonym: str, recipient_pseudonym: str) -> str:
    a, b = str(initiator_pseudonym).strip(), str(recipient_pseudonym).strip()
    if not a or not b:
        raise ValueError("Both pseudonymized identities are required")
    if a == b:
        raise ValueError("Initiator and recipient cannot be the same identity")
    left, right = sorted((a, b))
    return hashlib.sha256(("D0019_DYAD|" + left + "|" + right).encode()).hexdigest()


def canonical_event_id(
    *,
    source_sha256: str,
    sheet: str,
    original_row: int,
) -> str:
    checksum = str(source_sha256).lower().strip()
    if len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
        raise ValueError("Exact 64-character source SHA-256 is required")
    if sheet != "Rawdata":
        raise ValueError("D0019 canonical event IDs are bound to the Rawdata sheet")
    if int(original_row) < 2:
        raise ValueError("Original Excel data row must be >= 2")
    payload = f"D0019|{checksum}|{sheet}|row:{int(original_row)}"
    return hashlib.sha256(payload.encode()).hexdigest()
