"""Summary: Token encoding utilities for OAuth credentials.

Importance: Keeps tokens obscured when stored locally in the MVP.
Alternatives: Use a dedicated secrets manager or strong encryption library.
"""

from __future__ import annotations

import base64
import hashlib


class TokenCodec:
    """Summary: Minimal token encoder/decoder.

    Importance: Provides a lightweight obfuscation layer for local secrets.
    Alternatives: Use a proper encryption library with key management.
    """

    def __init__(self, secret: str) -> None:
        """Summary: Initialize with a secret used to derive a keystream.

        Importance: Keeps token encoding consistent per deployment.
        Alternatives: Generate per-token secrets and store securely.
        """

        self._secret = secret.encode("utf-8")

    def encode(self, plaintext: str) -> str:
        """Summary: Encode plaintext into an obfuscated string.

        Importance: Avoids storing raw tokens in SQLite.
        Alternatives: Store tokens in a vault.
        """

        raw = plaintext.encode("utf-8")
        key = _keystream(self._secret, len(raw))
        obfuscated = bytes([b ^ k for b, k in zip(raw, key)])
        return base64.urlsafe_b64encode(obfuscated).decode("utf-8")

    def decode(self, payload: str) -> str:
        """Summary: Decode an obfuscated string back to plaintext.

        Importance: Allows using stored tokens for provider calls.
        Alternatives: Skip decoding and require re-authentication.
        """

        raw = base64.urlsafe_b64decode(payload.encode("utf-8"))
        key = _keystream(self._secret, len(raw))
        plaintext = bytes([b ^ k for b, k in zip(raw, key)])
        return plaintext.decode("utf-8")


def _keystream(secret: bytes, length: int) -> bytes:
    """Summary: Derive a deterministic keystream from a secret.

    Importance: Keeps encoding reversible without external dependencies.
    Alternatives: Use a proper stream cipher.
    """

    output = b""
    counter = 0
    while len(output) < length:
        counter_bytes = counter.to_bytes(4, "big")
        output += hashlib.sha256(secret + counter_bytes).digest()
        counter += 1
    return output[:length]
