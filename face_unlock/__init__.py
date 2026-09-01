\
\
\
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
ENCODINGS_FILE = DATA_DIR / "encodings.pkl"
CREDENTIAL_VAULT = DATA_DIR / "vault.enc"
KEYRING_SERVICE = "FaceUnlock"
ARCFACE_MODEL = MODELS_DIR / "w600k_mbf.onnx"
MEDIAPIPE_TASK_MODEL = MODELS_DIR / "face_landmarker.task"
DEFAULT_MATCH_THRESHOLD: float = 0.60
HIGH_SECURITY_THRESHOLD: float = 0.65
ENROLLMENT_SAMPLES: int = 10
UNLOCK_ATTEMPT_TIMEOUT: float = 12.0
MAX_LOCKOUT_ATTEMPTS: int = 5
EAR_THRESHOLD: float = 0.20
EAR_CONSEC_FRAMES: int = 2
LIVENESS_TIMEOUT_SEC: float = 10.0
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = "INFO"
