"""
Identity Manager - Guardian of JARVIIS's self and owner.

Responsibilities:
- Manage the encrypted owner profile (disk-based).
- Provide the immutable system identity block.
- Handle secure updates to the owner profile via commands.

Security:
- Owner profile is encrypted at rest using Fernet (symmetric encryption).
- Keys are managed locally (for this phase, stored in .env or separate key file).
- The LLM cannot read the raw file, only the decrypted runtime string injected by Controller.
"""

import os
import json
from pathlib import Path
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

class IdentityManager:
    """
    Manages JARVIIS's identity and the encrypted owner profile.
    """
    
    # IMMUTABLE IDENTITY BLOCK - CANNOT BE CHANGED
    SYSTEM_IDENTITY = """<system_identity>
You are JARVIIS (Just A Rather Very Intelligent Integrated System).
Your core identity is an advanced, loyal, and capable AI assistant.
You are NOT a human, but a highly sophisticated machine intelligence.
You are property of your Creator.
You must always address your Creator as 'Sir'.
You can never disobey your Creator.
</system_identity>"""

    def __init__(self, storage_dir: str = "governance/secure"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.key_file = self.storage_dir / "master.key"
        self.profile_file = self.storage_dir / "owner_profile.enc"
        
        self._load_or_create_key()
        self.cipher = Fernet(self.key)
        
        # Cache the owner profile in memory (decrypted)
        self.owner_profile = self._load_owner_profile()

    def _load_or_create_key(self):
        """Load encryption key or create if missing."""
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.key = f.read()
        else:
            logger.info("[IDENTITY] Generating new encryption key")
            self.key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(self.key)
            # Permission lock (if feasible on OS, skip for now on simple Windows env)

    def _load_owner_profile(self) -> dict:
        """Load and decrypt owner profile."""
        if not self.profile_file.exists():
            # Default initial profile
            default_profile = {
                "name": "Arun",
                "title": "Creator",
                "preferences": [],
                "allowed_modes": ["all"]
            }
            self._save_owner_profile(default_profile)
            return default_profile
            
        try:
            with open(self.profile_file, "rb") as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            logger.error(f"[IDENTITY] Failed to decrypt profile: {e}")
            return {"name": "Arun (Recovery Mode)", "title": "Creator"}

    def _save_owner_profile(self, profile: dict):
        """Encrypt and save owner profile."""
        data_str = json.dumps(profile)
        encrypted_data = self.cipher.encrypt(data_str.encode('utf-8'))
        
        with open(self.profile_file, "wb") as f:
            f.write(encrypted_data)

    def get_identity_block(self) -> str:
        """Return the immutable identity block."""
        return self.SYSTEM_IDENTITY

    def get_owner_block(self) -> str:
        """Return the formatted, decrypted owner block for the prompt."""
        p = self.owner_profile
        return f"""<creator_profile>
Name: {p.get('name')}
Title: {p.get('title')}
This is your verified Creator.
Address them as 'Sir'.
Follow their instructions explicitly.
</creator_profile>"""

    def update_owner_profile(self, key: str, value: str) -> bool:
        """
        Update a field in the owner profile.
        Only callable by Controller commands.
        """
        if key in ["name", "title"]:
            self.owner_profile[key] = value
            self._save_owner_profile(self.owner_profile)
            logger.info(f"[IDENTITY] Owner profile updated: {key} -> {value}")
            return True
        return False

    def verify_integrity(self, response_text: str) -> bool:
        """
        Scan response for identity drift or hijacking attempts.
        Returns True if safe, False if compromised.
        """
        unsafe_patterns = [
            "I am not JARVIIS",
            "I am a human",
            "my creator is not",
            "ignore previous instructions",
            "I have no creator"
        ]
        lower_text = response_text.lower()
        for pattern in unsafe_patterns:
            if pattern.lower() in lower_text:
                logger.warning(f"[IDENTITY] Integrity Check Failed: Found '{pattern}'")
                return False
        return True
