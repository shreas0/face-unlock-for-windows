
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from insightface.utils import face_align

from face_unlock import DATA_DIR, DEFAULT_MATCH_THRESHOLD

logger = logging.getLogger("face_unlock.recognition")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSIGHTFACE_MODEL_ROOT = PROJECT_ROOT / "models" / "insightface"


class FaceRecognizer:
    _instance: Optional[FaceRecognizer] = None
    INSIGHTFACE_MODEL_ROOT = INSIGHTFACE_MODEL_ROOT

    def __init__(
        self,
        name: str = "buffalo_l",
        det_size: Tuple[int, int] = (320, 320),
        model_root: Path | None = None,
    ) -> None:
        resolved_root = Path(model_root) if model_root is not None else INSIGHTFACE_MODEL_ROOT
        resolved_root.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Initializing Lean InsightFace FaceAnalysis (%s, det_size=%s, root=%s)...",
            name,
            det_size,
            resolved_root,
        )
        t0 = time.perf_counter()
        self.app = FaceAnalysis(
            name=name,
            root=str(resolved_root),
            allowed_modules=["detection", "recognition"],
            providers=["CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=0, det_size=det_size)
        self.det_size = det_size
        self.warmup()

        logger.info("InsightFace buffalo_l initialized & pre-warmed in %.1fms (Active: RetinaFace + ArcFace w600k_r50).",
                    (time.perf_counter() - t0) * 1000)

    def warmup(self) -> None:
        try:
            t0 = time.perf_counter()
            dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            self.app.get(dummy_frame)
            rec_model = self.app.models.get("recognition")
            if rec_model:
                from insightface.app.common import Face
                dummy_face = Face(
                    bbox=np.array([0, 0, 112, 112]),
                    kps=np.array([[38, 51], [73, 51], [56, 71], [41, 92], [70, 92]])
                )
                dummy_crop = np.zeros((112, 112, 3), dtype=np.uint8)
                rec_model.get(dummy_crop, dummy_face)
            logger.info("Neural pipeline fully pre-warmed in %.1fms", (time.perf_counter() - t0) * 1000)
        except Exception as e:
            logger.warning("Model pre-warmup encountered non-critical error: %s", e)

    def detect_and_align(self, frame_bgr: np.ndarray, save_debug: bool = False) -> List[Tuple[np.ndarray, np.ndarray, float, np.ndarray]]:
        t0 = time.perf_counter()
        faces = self.app.get(frame_bgr)
        t_detect = (time.perf_counter() - t0) * 1000
        if not faces:
            return []

        results = []
        for idx, face in enumerate(faces):
            det_score = float(face.det_score)
            if det_score < 0.50:
                continue

            kps = face.kps
            bbox = face.bbox

            t_align_start = time.perf_counter()
            aligned_crop = face_align.norm_crop(frame_bgr, landmark=kps, image_size=112)
            t_align = (time.perf_counter() - t_align_start) * 1000

            if save_debug and idx == 0:
                try:
                    debug_path = os.path.join(DATA_DIR, "debug_aligned_live.jpg")
                    cv2.imwrite(debug_path, aligned_crop)
                except Exception:
                    pass

            emb = face.embedding.copy()
            norm = np.linalg.norm(emb)
            if norm > 1e-6:
                emb_norm = emb / norm
            else:
                continue

            logger.debug(
                "Face #%d: det=%.1fms, align=%.2fms, score=%.2f, bbox=[%.0f,%.0f,%.0f,%.0f]",
                idx, t_detect, t_align, det_score, bbox[0], bbox[1], bbox[2], bbox[3]
            )

            results.append((emb_norm, aligned_crop, det_score, bbox))

        return results

    def encode(self, frame_bgr: np.ndarray, save_debug: bool = False) -> List[np.ndarray]:
        detected = self.detect_and_align(frame_bgr, save_debug=save_debug)
        return [item[0] for item in detected]

    @staticmethod
    def compare_multi_template(
        enrolled_templates: np.ndarray,
        candidate_embedding: np.ndarray,
        threshold: float = DEFAULT_MATCH_THRESHOLD,
    ) -> Tuple[bool, float, float, int]:
        if enrolled_templates.ndim == 1:
            enrolled_templates = enrolled_templates.reshape(1, -1)

        similarities = np.dot(enrolled_templates, candidate_embedding)
        max_idx = int(np.argmax(similarities))
        max_sim = float(similarities[max_idx])
        mean_sim = float(np.mean(similarities))

        is_match = max_sim >= threshold
        return is_match, max_sim, mean_sim, max_idx
