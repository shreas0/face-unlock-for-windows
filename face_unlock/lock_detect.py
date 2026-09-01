
from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
from typing import Optional

import psutil

logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32


def _is_lock_process_running() -> bool:
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info["name"]
                if name and name.lower() in ("logonui.exe",):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


def _get_foreground_process_name() -> Optional[str]:
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = ctypes.wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return None
        proc = psutil.Process(pid.value)
        return proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        return None


def _is_secure_desktop() -> bool:
    try:
        hdesk = _user32.OpenInputDesktop(0, False, 0x0100)
        if not hdesk:
            return True
        _user32.CloseDesktop(hdesk)
        return False
    except Exception:
        return True


def is_locked() -> bool:
    if _is_lock_process_running():
        logger.debug("Lock detected: LogonUI.exe is running")
        return True

    if _is_secure_desktop():
        logger.debug("Lock detected: secure desktop active")
        return True

    fg = _get_foreground_process_name()
    if fg and fg in ("logonui.exe", "lockapp.exe"):
        logger.debug("Lock detected: foreground process is %s", fg)
        return True

    return False
