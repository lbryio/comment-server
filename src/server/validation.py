import logging
import binascii
import hashlib
import re

import ecdsa
import typing
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives.serialization import load_der_public_key

logger = logging.getLogger(__name__)


def is_valid_channel(channel_id: str, channel_name: str) -> bool:
    return channel_id and claim_id_is_valid(channel_id) and \
           channel_name and channel_name_is_valid(channel_name)


def is_signature_valid(encoded_signature, signature_digest, public_key_bytes) -> bool:
    try:
        public_key = load_der_public_key(public_key_bytes, default_backend())
        public_key.verify(encoded_signature, signature_digest, ec.ECDSA(Prehashed(hashes.SHA256())))
        return True
    except (ValueError, InvalidSignature):
        logger.exception('Signature validation failed')
    return False


def channel_name_is_valid(channel_name: str) -> bool:
    return re.fullmatch(
        '@(?:(?![\x00-\x08\x0b\x0c\x0e-\x1f\x23-\x26'
        '\x2f\x3a\x3d\x3f-\x40\uFFFE-\U0000FFFF]).){1,255}',
        channel_name
    ) is not None


def body_is_valid(comment: str) -> bool:
    return 0 < len(comment) <= 2000


def comment_id_is_valid(comment_id: str) -> bool:
    return re.fullmatch('([a-z0-9]{64}|[A-Z0-9]{64})', comment_id) is not None


def claim_id_is_valid(claim_id: str) -> bool:
    return re.fullmatch('([a-z0-9]{40}|[A-Z0-9]{40})', claim_id) is not None


def is_valid_base_comment(comment: str, claim_id: str, parent_id: str = None, **kwargs) -> bool:
    return comment is not None and body_is_valid(comment) and \
           claim_id is not None and claim_id_is_valid(claim_id) and \
           (parent_id is None or comment_id_is_valid(parent_id))


def is_valid_credential_input(channel_id: str = None, channel_name: str = None,
                              signature: str = None, signing_ts: str = None, **kwargs) -> bool:
    if channel_id or channel_name or signature or signing_ts:
        try:
            assert channel_id and channel_name and signature and signing_ts
            assert is_valid_channel(channel_id, channel_name)
            assert len(signature) == 128
            assert signing_ts.isalnum()

        except Exception:
            return False
    return True


def validate_signature_from_claim(claim: dict, signature: typing.Union[str, bytes],
                                  signing_ts: str, data: str) -> bool:
    try:
        if claim:
            public_key = claim['value']['public_key']
            claim_hash = binascii.unhexlify(claim['claim_id'].encode())[::-1]
            injest = b''.join((signing_ts.encode(), claim_hash, data.encode()))
            return is_signature_valid(
                encoded_signature=get_encoded_signature(signature),
                signature_digest=hashlib.sha256(injest).digest(),
                public_key_bytes=binascii.unhexlify(public_key.encode())
            )
    except:
        return False


def get_encoded_signature(signature: typing.Union[str, bytes]) -> bytes:
    signature = signature.encode() if type(signature) is str else signature
    r = int(signature[:int(len(signature) / 2)], 16)
    s = int(signature[int(len(signature) / 2):], 16)
    return ecdsa.util.sigencode_der(r, s, len(signature) * 4)