from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class CredentialError(RuntimeError):
    """Raised when a stored credential cannot be encrypted or decrypted."""


class CredentialManager:
    def __init__(self, key: bytes) -> None:
        try:
            self._fernet = Fernet(key)
        except (ValueError, TypeError) as exc:
            raise CredentialError("credential encryption key is invalid") from exc

    @classmethod
    def from_key(cls, key: bytes) -> CredentialManager:
        return cls(key)

    @classmethod
    def from_file(cls, path: str | Path) -> CredentialManager:
        key_path = Path(path)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if key_path.exists():
            key = key_path.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            fd = os.open(key_path, flags, 0o600)
            try:
                os.write(fd, key)
            finally:
                os.close(fd)
        try:
            key_path.chmod(0o600)
        except OSError:
            pass
        return cls(key)

    def encrypt_secret(self, value: str) -> str:
        if not isinstance(value, str) or not value:
            raise CredentialError("credential must be a non-empty string")
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt_secret(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
            raise CredentialError("stored credential cannot be decrypted") from exc
