
from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import threading
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004

MAPVK_VK_TO_VSC = 0

VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_BACK = 0x08
VK_SHIFT = 0x10

DESKTOP_WRITEOBJECTS = 0x0080
DESKTOP_SWITCHDESKTOP = 0x0100
DESKTOP_READOBJECTS = 0x0001
DESKTOP_ALL_ACCESS = (
    0x000F0000 |
    DESKTOP_READOBJECTS |
    0x0002 |
    0x0004 |
    0x0008 |
    0x0010 |
    0x0020 |
    0x0040 |
    DESKTOP_WRITEOBJECTS |
    DESKTOP_SWITCHDESKTOP
)

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT)]
    _anonymous_ = ("_union",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_union", _INPUT_UNION),
    ]


_SendInput = _user32.SendInput
_SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(_INPUT), ctypes.c_int]
_SendInput.restype = ctypes.c_uint


def _press_vk_and_scan(vk: int, delay: float = 0.03) -> None:
    scan = _user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    _user32.keybd_event(vk, scan, 0, 0)
    time.sleep(delay)
    _user32.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)
    time.sleep(delay)


def _type_character(char: str, delay: float = 0.04) -> None:
    vkey_scan = _user32.VkKeyScanW(ord(char))

    if vkey_scan != -1:
        vk = vkey_scan & 0xFF
        shift_state = (vkey_scan >> 8) & 0xFF
        scan = _user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)

        need_shift = bool(shift_state & 1)
        if need_shift:
            _user32.keybd_event(VK_SHIFT, 0x2A, 0, 0)
            time.sleep(0.01)

        _user32.keybd_event(vk, scan, 0, 0)
        time.sleep(delay)
        _user32.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)
        time.sleep(delay)

        if need_shift:
            time.sleep(0.01)
            _user32.keybd_event(VK_SHIFT, 0x2A, KEYEVENTF_KEYUP, 0)
    else:
        code = ord(char)
        inp_down = _INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.ki.wVk = 0
        inp_down.ki.wScan = code
        inp_down.ki.dwFlags = KEYEVENTF_UNICODE
        _SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(_INPUT))
        time.sleep(delay)

        inp_up = _INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.ki.wVk = 0
        inp_up.ki.wScan = code
        inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        _SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(_INPUT))
        time.sleep(delay)


def _worker_unlock_sequence(password: str, result_holder: list) -> None:
    hdesk = None
    old_desk = None
    try:
        logger.info("=== SECURE DESKTOP UNLOCK SEQUENCE ===")

        old_desk = _user32.GetThreadDesktop(_kernel32.GetCurrentThreadId())
        hdesk = _user32.OpenInputDesktop(0, False, DESKTOP_ALL_ACCESS)
        if not hdesk:
            hdesk = _user32.OpenInputDesktop(
                0, False, DESKTOP_WRITEOBJECTS | DESKTOP_SWITCHDESKTOP | DESKTOP_READOBJECTS
            )

        if not hdesk:
            err = ctypes.get_last_error()
            logger.error(
                "DESKTOP ATTACH FAILED: Cannot open active input desktop (error=%d). "
                "Ensure watcher is running as SYSTEM or Administrator.",
                err,
            )
            result_holder.append(False)
            return

        attached = _user32.SetThreadDesktop(hdesk)
        if not attached:
            err = ctypes.get_last_error()
            logger.error("DESKTOP ATTACH FAILED: SetThreadDesktop returned 0 (error=%d)", err)
            result_holder.append(False)
            return

        logger.info("✓ Attached worker thread to Secure Desktop (handle=%d)", hdesk)

        logger.info("Step 1/4: Waking lock screen cover (pressing Space)...")
        _press_vk_and_scan(VK_SPACE, delay=0.05)
        time.sleep(1.0)

        logger.info("Step 2/4: Ensuring clean input focus in LogonUI...")
        for _ in range(4):
            _press_vk_and_scan(VK_BACK, delay=0.03)
        time.sleep(0.1)

        logger.info("Step 3/4: Typing credentials (%d characters)...", len(password))
        for ch in password:
            _type_character(ch, delay=0.04)

        time.sleep(0.15)
        logger.info("Step 4/4: Submitting credential (Enter)...")
        _press_vk_and_scan(VK_RETURN, delay=0.05)

        logger.info("✓ Unlock sequence submitted to Secure Desktop!")
        result_holder.append(True)

    except Exception:
        logger.exception("Unexpected error during Secure Desktop unlock sequence")
        result_holder.append(False)
    finally:
        if old_desk and hdesk:
            _user32.SetThreadDesktop(old_desk)
        if hdesk:
            _user32.CloseDesktop(hdesk)


def type_password_and_enter(password: str) -> bool:
    result_holder: list = []
    worker = threading.Thread(
        target=_worker_unlock_sequence,
        args=(password, result_holder),
        name="SecureDesktopUnlockThread",
    )
    worker.start()
    worker.join(timeout=8.0)

    return bool(result_holder and result_holder[0])
