
from __future__ import annotations

import ctypes
import ctypes.wintypes
import getpass
import logging
import os
from typing import Optional

import keyring

from face_unlock import CREDENTIAL_VAULT, KEYRING_SERVICE

logger = logging.getLogger(__name__)

crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32

CRYPTPROTECT_LOCAL_MACHINE = 0x04
CRYPTPROTECT_UI_FORBIDDEN = 0x01


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _encrypt_dpapi(plaintext: str) -> bytes:
    data = plaintext.encode("utf-8")
    blob_in = _DATA_BLOB(
        len(data),
        ctypes.cast(ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_byte)),
    )
    blob_out = _DATA_BLOB()
    flags = CRYPTPROTECT_LOCAL_MACHINE | CRYPTPROTECT_UI_FORBIDDEN

    if not crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        "FaceUnlockCredential",
        None,
        None,
        None,
        flags,
        ctypes.byref(blob_out),
    ):
        raise ctypes.WinError()

    encrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    kernel32.LocalFree(blob_out.pbData)
    return encrypted


def _decrypt_dpapi(encrypted_bytes: bytes) -> str:
    blob_in = _DATA_BLOB(
        len(encrypted_bytes),
        ctypes.cast(ctypes.create_string_buffer(encrypted_bytes, len(encrypted_bytes)), ctypes.POINTER(ctypes.c_byte)),
    )
    blob_out = _DATA_BLOB()
    flags = CRYPTPROTECT_UI_FORBIDDEN

    if not crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        flags,
        ctypes.byref(blob_out),
    ):
        raise ctypes.WinError()

    decrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    kernel32.LocalFree(blob_out.pbData)
    return decrypted.decode("utf-8")


def store_password(username: str, password: str) -> None:
    enc = _encrypt_dpapi(password)
    with open(CREDENTIAL_VAULT, "wb") as f:
        f.write(enc)

    try:
        keyring.set_password(KEYRING_SERVICE, username, password)
    except Exception as e:
        logger.warning("Could not set keyring password: %s", e)

    logger.info("Credential stored and DPAPI-encrypted for user '%s'", username)


def get_password(username: str) -> Optional[str]:
    if os.path.exists(CREDENTIAL_VAULT):
        try:
            with open(CREDENTIAL_VAULT, "rb") as f:
                enc = f.read()
            return _decrypt_dpapi(enc)
        except Exception as e:
            logger.warning("DPAPI vault decryption failed: %s", e)

    try:
        pwd = keyring.get_password(KEYRING_SERVICE, username)
        if pwd:
            return pwd
    except Exception as e:
        logger.warning("Keyring retrieval failed: %s", e)

    logger.warning("No stored credential found for user '%s'", username)
    return None


def delete_password(username: str) -> None:
    if os.path.exists(CREDENTIAL_VAULT):
        try:
            os.remove(CREDENTIAL_VAULT)
            logger.info("Deleted DPAPI credential vault")
        except OSError as e:
            logger.warning("Error deleting vault: %s", e)

    try:
        keyring.delete_password(KEYRING_SERVICE, username)
        logger.info("Deleted keyring credential for user '%s'", username)
    except Exception:
        pass


def delete_all_passwords() -> None:
    if os.path.exists(CREDENTIAL_VAULT):
        try:
            os.remove(CREDENTIAL_VAULT)
        except OSError:
            pass
