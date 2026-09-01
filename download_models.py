from __future__ import annotations

from face_unlock.recognition import FaceRecognizer


def main() -> None:
    FaceRecognizer(name="buffalo_l", det_size=(320, 320))
    print(
        f"[OK] InsightFace buffalo_l is available at: "
        f"{FaceRecognizer.INSIGHTFACE_MODEL_ROOT}\\models\\buffalo_l"
    )


if __name__ == "__main__":
    main()
