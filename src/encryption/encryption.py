"""
Simple encryption codec for Temporal that encrypts only SensitiveData-wrapped objects.
"""
import os
from typing import Iterable, List
from cryptography.fernet import Fernet
from dataclasses import replace
from temporalio.api.common.v1 import Payload
from temporalio.converter import PayloadCodec, default, DataConverter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define a unique encoding for our encrypted payload
ENCRYPTED_FIELD_ENCODING = b"json/sensitive-encrypted"

class EncryptionCodec(PayloadCodec):
    """Codec that selectively encrypts payloads wrapped in a custom class."""

    def __init__(self):
        # Load key from environment variable
        key_str = os.getenv('TEMPORAL_ENCRYPTION_KEY')
        if not key_str:
            raise ValueError(
                "TEMPORAL_ENCRYPTION_KEY environment variable not set. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        self.cipher = Fernet(key_str.encode('utf-8'))
        # Use the default converter to handle the serialization of wrapped data
        self.default_converter = default()

    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        """Encrypt all payloads"""
        return [
            Payload(
                metadata={
                    "encoding": b"binary/encrypted",
                },
                data=self.cipher.encrypt(p.SerializeToString()),
            )
            for p in payloads
        ]
    
    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        """Decrypt encrypted payloads"""
        ret: List[Payload] = []
        for p in payloads:
            if p.metadata.get("encoding", b"").decode() != "binary/encrypted":
                ret.append(p)
                continue
            ret.append(Payload.FromString(self.cipher.decrypt(p.data)))
        return ret
        
def create_encrypted_data_converter() -> DataConverter:
    """Creates a DataConverter with the custom EncryptionCodec."""
    return replace(
        default(),
        payload_codec=EncryptionCodec(),
    )