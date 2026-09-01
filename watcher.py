
from __future__ import annotations

import argparse
import logging
import os
import pickle
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from face_unlock import (
    ENCODINGS_FILE, LOG_FORMAT, LOG_LEVEL,
    POLL_INTERVAL_SEC, UNLOCK_ATTEMPT_TIMEOUT,
    COOLDOWN_AFTER_SUCCESS_SEC, MAX_LOCKOUT_ATTEMPTS,
)
from face_unlock.recognition import FaceRecognizer
from face_unlock.liveness import LivenessChecker
from face_unlock.lock_detect import is_locked
from face_unlock.credential import get_password
from face_unlock.unlock import type_password_and_enter

logger = logging.getLogger("watcher")


def get_windows_username() -> str:
    return os.environ.get("USERNAME", os.environ.get("USER", "unknown"))


def load_enrolled_data(username: str) -> dict:
    if not os.path.exists(ENCODINGS_FILE):
        raise FileNotFoundError(
            f"No enrollment data found at {ENCODINGS_FILE}. Run enroll.py first."
        )
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)

    if username not in data:
        if len(data) == 1:
            default_user = list(data.keys())[0]
            logger.info("User '%s' not in enrollment, using enrolled user '%s'", username, default_user)
            return data[default_user]
        raise KeyError(f"User '{username}' not enrolled. Enrolled users: {list(data.keys())}")
    return data[username]


def attempt_face_unlock(
    recognizer: FaceRecognizer,
    liveness: LivenessChecker,
    enrolled_encoding: np.ndarray,
    threshold: float,
    username: str,
    camera_id: int = 0,
    timeout: float = UNLOCK_ATTEMPT_TIMEOUT,
) -> bool:
    cap = None
    try:
        logger.info("--- Attempting Face Unlock (timeout=%.0fs) ---", timeout)
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            logger.error("Cannot open camera %d", camera_id)
            return False

        liveness.reset()
        face_matched = False
        best_dist = float("inf")
        start = time.monotonic()

        while (time.monotonic() - start) < timeout:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.03)
                continue

            if not face_matched:
                encs = recognizer.encode(frame)
                for enc in encs:
                    match, dist = recognizer.compare(enc, enrolled_encoding, threshold)
                    best_dist = min(best_dist, dist)
                    if match:
                        face_matched = True
                        logger.info("  ✓ Face Matched! (Distance: %.3f, Threshold: %.3f)", dist, threshold)
                        break

            liveness.update(frame)

            if face_matched and liveness.is_alive():
                logger.info("  ✓ Liveness confirmed (%d blink)! Unlocking PC...", liveness.blink_count)

                cap.release()
                cap = None

                password = get_password(username)
                if password is None:
                    logger.error("No password or DPAPI vault available for '%s'", username)
                    return False

                return type_password_and_enter(password)

            time.sleep(0.02)

        logger.info(
            "Attempt timed out (Face matched: %s, Min dist: %.3f / %.3f, Blinks: %d)",
            face_matched, best_dist, threshold, liveness.blink_count,
        )
        return False

    except Exception:
        logger.exception("Error during face unlock attempt")
        return False
    finally:
        if cap is not None:
            cap.release()


def main_loop(
    username: str,
    camera_id: int = 0,
    threshold: float | None = None,
) -> None:
    enrolled = load_enrolled_data(username)
    enrolled_encoding = enrolled["encoding"]
    logger.info(
        "Loaded enrollment for '%s' (%s samples)",
        username, enrolled.get("num_samples", "?"),
    )

    recognizer = FaceRecognizer()
    liveness = LivenessChecker()

    if threshold is None:
        threshold = recognizer.default_threshold
    logger.info(
        "Config: Threshold=%.2f, Polling=%ds, Lockout Limit=%d attempts",
        threshold, POLL_INTERVAL_SEC, MAX_LOCKOUT_ATTEMPTS,
    )

    if get_password(username) is None:
        logger.error("No password or DPAPI vault found for '%s'. Run enroll.py first.", username)
        sys.exit(1)

    consecutive_attempts = 0
    lockout_safeguard_active = False

    logger.info("=== Face Unlock Watcher Active ===")

    while True:
        try:
            locked = is_locked()

            if locked:
                if lockout_safeguard_active:
                    time.sleep(POLL_INTERVAL_SEC)
                    continue

                consecutive_attempts += 1
                logger.info(
                    ">>> Lock Screen Active — Attempt %d of %d <<<",
                    consecutive_attempts, MAX_LOCKOUT_ATTEMPTS,
                )

                if consecutive_attempts > MAX_LOCKOUT_ATTEMPTS:
                    lockout_safeguard_active = True
                    logger.warning(
                        "==============================================================\n"
                        "[LOCKOUT SAFEGUARD TRIGGERED]\n"
                        "Reached %d consecutive attempts without successful unlock.\n"
                        "Auto-unlock is PAUSED to prevent Windows Account Lockout.\n"
                        "Please unlock Windows MANUALLY with your PIN/Password.\n"
                        "Auto-unlock will automatically resume once logged in.\n"
                        "==============================================================",
                        MAX_LOCKOUT_ATTEMPTS,
                    )
                    time.sleep(POLL_INTERVAL_SEC)
                    continue

                success = attempt_face_unlock(
                    recognizer=recognizer,
                    liveness=liveness,
                    enrolled_encoding=enrolled_encoding,
                    threshold=threshold,
                    username=username,
                    camera_id=camera_id,
                )

                if success:
                    logger.info(">>> Unlocked successfully! <<<")
                    consecutive_attempts = 0
                    time.sleep(COOLDOWN_AFTER_SUCCESS_SEC)
                else:
                    logger.info("Attempt #%d finished.", consecutive_attempts)
                    time.sleep(0.5)

            else:
                if lockout_safeguard_active:
                    logger.info("Manual unlock detected — Lockout safeguard reset.")
                    lockout_safeguard_active = False

                consecutive_attempts = 0
                time.sleep(POLL_INTERVAL_SEC)

        except Exception:
            logger.exception("Unhandled error in main loop — continuing")
            time.sleep(POLL_INTERVAL_SEC)


def main() -> None:
    parser = argparse.ArgumentParser(description="Face Unlock Watcher Daemon")
    parser.add_argument("--username", default=None)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else LOG_LEVEL
    logging.basicConfig(format=LOG_FORMAT, level=level)

    username = args.username or get_windows_username()
    logger.info("Starting Face Unlock watcher for user: %s", username)

    main_loop(
        username=username,
        camera_id=args.camera,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
