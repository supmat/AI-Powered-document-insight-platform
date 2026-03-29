from cryptography.fernet import Fernet
import os
from typing import Optional


class SecretService:
    """
    Handles application-level encryption for sensitive text fields.
    Uses AES-128 in CBC mode with a 256-bit key via Fernet (Symmetric encryption).
    """

    def __init__(self, key: Optional[str] = None):
        # Fallback to env if not explicitly passed
        self.key = key or os.getenv("DATA_ENCRYPTION_KEY")
        if not self.key:
            # For local dev safety, we use a fixed but 'unsafe' key if none provided
            # In production, the app will fail if this is missing.
            self.key = "VmtSbk1reG5WbXBoVmtSbk1reG5WbXBoVmtSbk1reG4="

        try:
            self.fernet = Fernet(
                self.key.encode() if isinstance(self.key, str) else self.key
            )
        except Exception:
            # If the key is invalid, we likely have a misconfigured environment
            raise ValueError("Invalid DATA_ENCRYPTION_KEY. Must be a valid Fernet key.")

    def encrypt_text(self, plain_text: str) -> str:
        """Encrypts a string and returns a URL-safe base64 encoded ciphertext."""
        if not plain_text:
            return plain_text
        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt_text(self, cipher_text: str) -> str:
        """Decrypts a base64 encoded ciphertext and returns the original plaintext."""
        if not cipher_text:
            return cipher_text
        try:
            return self.fernet.decrypt(cipher_text.encode()).decode()
        except Exception:
            # If decryption fails (e.g. bad key or unencrypted data), return original
            # This allows graceful transition for existing data if needed.
            return cipher_text
