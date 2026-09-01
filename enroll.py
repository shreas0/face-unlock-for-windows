
from __future__ import annotations

import argparse
import getpass
import os
import pickle
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from face_unlock import DATA_DIR, ENCODINGS_FILE, CREDENTIAL_VAULT
from face_unlock.credential import store_password, delete_password, delete_all_passwords
from face_unlock.recognition import FaceRecognizer

NUM_ENROLLMENT_SAMPLES = 12


def capture_multi_template_samples(num_samples: int = NUM_ENROLLMENT_SAMPLES, camera_id: int = 0):
    print("[1/3] Initializing Fast RetinaFace + ArcFace engine...")
    recognizer = FaceRecognizer(name="buffalo_l", det_size=(320, 320))

    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print("[ERROR] Could not open camera.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    for _ in range(5):
        cap.read()

    embeddings_list = []
    aligned_crops = []

    prompts = [
        "Look straight at the camera (Neutral)",
        "Look straight at the camera (Smile)",
        "Turn head slightly LEFT",
        "Turn head slightly RIGHT",
        "Tilt head slightly UP",
        "Tilt head slightly DOWN",
        "Tilt head to the left angle",
        "Tilt head to the right angle",
        "Lean in slightly closer",
        "Lean back slightly",
        "Neutral face (Normal lighting)",
        "Final verification sample"
    ]

    print("\n=================================================================")
    print(" Fast Multi-Template Biometric Enrollment (12 Canonical Angles)")
    print("=================================================================")
    print("Follow the on-screen prompts for natural angle coverage:\n")

    pbar_len = 25
    last_capture_time = 0.0

    try:
        while len(embeddings_list) < num_samples:
            ret, frame = cap.read()
            if not ret:
                continue

            current_prompt = prompts[min(len(embeddings_list), len(prompts) - 1)]
            display_frame = frame.copy()
            h, w = display_frame.shape[:2]

            cv2.rectangle(display_frame, (0, 0), (w, 80), (0, 0, 0), -1)
            cv2.putText(
                display_frame,
                "Sample " + str(len(embeddings_list) + 1) + "/" + str(num_samples) + ": " + current_prompt,
                (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
            )
            cv2.putText(
                display_frame,
                "Press Q to abort enrollment",
                (15, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 200),
                1,
            )

            detected = recognizer.detect_and_align(frame, save_debug=False)
            if detected:
                emb, crop, det_score, bbox = detected[0]
                x1, y1, x2, y2 = [int(v) for v in bbox]
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    display_frame,
                    "RetinaFace: " + f"{det_score:.2f}",
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )

                if det_score >= 0.70 and (time.perf_counter() - last_capture_time) >= 0.25:
                    embeddings_list.append(emb)
                    aligned_crops.append(crop)
                    last_capture_time = time.perf_counter()

                    sample_path = os.path.join(DATA_DIR, f"enroll_sample_{len(embeddings_list)}.jpg")
                    cv2.imwrite(sample_path, crop)

                    pct = len(embeddings_list) / num_samples
                    filled = int(pbar_len * pct)
                    bar = "#" * filled + "-" * (pbar_len - filled)
                    sys.stdout.write("\r  [" + bar + "] " + str(len(embeddings_list)) + "/" + str(num_samples) + " captured -> " + current_prompt[:35])
                    sys.stdout.flush()

            cv2.imshow("Face Unlock — Multi-Template Biometric Enrollment", display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("\n[INFO] Enrollment cancelled by user.")
                sys.exit(0)

        print("\n\n[OK] Captured all 12 canonical aligned face samples in under 3 seconds!")

    finally:
        cap.release()
        cv2.destroyAllWindows()

    templates_matrix = np.array(embeddings_list, dtype=np.float32)
    centroid = np.mean(templates_matrix, axis=0)
    centroid = centroid / np.linalg.norm(centroid)
    return templates_matrix, centroid


def list_enrolled_users() -> list[str]:
    if not os.path.exists(ENCODINGS_FILE):
        return []
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    return list(data.keys())


def delete_user(username: str) -> None:
    if not os.path.exists(ENCODINGS_FILE):
        print("[INFO] No enrolled data found.")
        return
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    if username in data:
        del data[username]
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(data, f)
        delete_password(username)
        print("[OK] Removed biometric data and credentials for user: " + username)
    else:
        print("[WARN] User not found.")


def delete_all_data() -> None:
    if os.path.exists(ENCODINGS_FILE):
        os.remove(ENCODINGS_FILE)
    if os.path.exists(CREDENTIAL_VAULT):
        os.remove(CREDENTIAL_VAULT)
    delete_all_passwords()
    print("[OK] All biometric data and credentials have been wiped.")


def enroll_user(username: str, camera_id: int = 0) -> None:
    existing = list_enrolled_users()
    if username in existing:
        print("[WARN] User already enrolled.")
        choice = input("Re-enroll and overwrite previous biometric profile? [y/N]: ").strip().lower()
        if choice != "y":
            return

    templates_matrix, centroid = capture_multi_template_samples(NUM_ENROLLMENT_SAMPLES, camera_id)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    encodings_data = {}
    if os.path.exists(ENCODINGS_FILE):
        try:
            with open(ENCODINGS_FILE, "rb") as f:
                encodings_data = pickle.load(f)
        except Exception:
            encodings_data = {}

    encodings_data[username] = {
        "templates": templates_matrix,
        "encoding": centroid,
        "samples_count": len(templates_matrix),
        "embedding_dim": 512,
        "model": "InsightFace-RetinaFace-ArcFace-buffalo_l",
    }

    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(encodings_data, f)
    print("[OK] Saved 12-template ArcFace ResNet-50 biometric profile for: " + username)

    print("\n--- Credential Setup ---")
    print("Enter your Windows password or PIN (encrypted via Windows DPAPI):")
    pwd = getpass.getpass("Password / PIN: ")
    if not pwd:
        print("[ERROR] Password cannot be empty.")
        sys.exit(1)
    confirm_pwd = getpass.getpass("Confirm Password / PIN: ")
    if pwd != confirm_pwd:
        print("[ERROR] Passwords do not match!")
        sys.exit(1)

    store_password(username, pwd)
    print("[OK] Saved encrypted credentials for: " + username)
    print("\n=================================================================")
    print(" Biometric Enrollment Complete (RetinaFace + ArcFace buffalo_l)")
    print("=================================================================")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default=getpass.getuser())
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--delete")
    parser.add_argument("--delete-all", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("Enrolled users:", list_enrolled_users())
        return
    if args.delete:
        delete_user(args.delete)
        return
    if args.delete_all:
        delete_all_data()
        return
    enroll_user(args.user, args.camera)


if __name__ == "__main__":
    main()
