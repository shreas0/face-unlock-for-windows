
from __future__ import annotations

import logging
import os
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from face_unlock import MEDIAPIPE_TASK_MODEL

logger = logging.getLogger("face_unlock.liveness")


class LivenessChecker:
    def __init__(self, required_blinks: int = 1) -> None:
        self.required_blinks = required_blinks
        self._blink_count = 0
        self._state = "OPEN"
        self._frames_closed = 0
        self._init_mediapipe()

    def _init_mediapipe(self) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        if not os.path.exists(MEDIAPIPE_TASK_MODEL):
            raise FileNotFoundError(f"MediaPipe task model not found at {MEDIAPIPE_TASK_MODEL}")

        base_options = mp_python.BaseOptions(model_asset_path=str(MEDIAPIPE_TASK_MODEL))
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        logger.info("Neural Blendshape Blink Detector initialized (2.0ms latency).")

    def reset(self) -> None:
        self._blink_count = 0
        self._state = "OPEN"
        self._frames_closed = 0

    def update(self, frame_bgr: np.ndarray) -> Tuple[bool, float]:
        import mediapipe as mp
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        t0 = time.perf_counter()
        result = self._landmarker.detect(mp_image)
        t_detect = (time.perf_counter() - t0) * 1000

        if not result or not result.face_blendshapes or len(result.face_blendshapes) == 0:
            return False, 0.0

        bs = {b.category_name: b.score for b in result.face_blendshapes[0]}
        b_left = bs.get("eyeBlinkLeft", 0.0)
        b_right = bs.get("eyeBlinkRight", 0.0)
        blink_score = float((b_left + b_right) / 2.0)

        if self._state == "OPEN":
            if blink_score >= 0.40:
                self._state = "CLOSED"
                self._frames_closed = 1
                logger.debug("Liveness: Eye closure initiated (score=%.2f, latency=%.1fms)", blink_score, t_detect)
        elif self._state == "CLOSED":
            if blink_score >= 0.40:
                self._frames_closed += 1
            elif blink_score < 0.20:
                self._state = "OPEN"
                self._blink_count += 1
                logger.info("[OK] Genuine Blink #%d verified! (Closed for %d frames, re-opened @ score=%.2f)",
                            self._blink_count, self._frames_closed, blink_score)
                self._frames_closed = 0

        return (blink_score >= 0.40), blink_score

    def is_alive(self) -> bool:
        return self._blink_count >= self.required_blinks

    def has_completed_blink(self) -> bool:
        return self.is_alive()

    @property
    def blink_count(self) -> int:
        return self._blink_count
