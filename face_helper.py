
from __future__ import annotations

import logging
import os
import pickle
import sys
import multiprocessing
import time
if hasattr(multiprocessing, "set_executable"):
    multiprocessing.set_executable(sys.executable)
try:
    import os as _os
    _os.environ.setdefault('PYTHONEXECUTABLE', sys.executable)
except Exception:
    pass
try:
    import multiprocessing.spawn as _ms
    if hasattr(_ms, 'get_executable'):
        _ms.get_executable = lambda: sys.executable
except Exception:
    pass
try:
    if hasattr(sys, '_base_executable'):
        try:
            sys._base_executable = sys.executable
        except Exception:
            pass
except Exception:
    pass
try:
    proj_root = os.path.dirname(os.path.abspath(__file__))
    diag_dir = os.path.join(proj_root, "data")
    os.makedirs(diag_dir, exist_ok=True)
    diag_path = os.path.join(diag_dir, "startup_executables.log")
    with open(diag_path, "a", encoding="utf-8") as f:
        f.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"sys.executable: {sys.executable}\n")
        f.write(f"sys._base_executable: {getattr(sys, '_base_executable', '')}\n")
        try:
            get_exec = multiprocessing.get_executable()
        except Exception:
            get_exec = "<no multiprocessing.get_executable>"
        f.write(f"multiprocessing.get_executable(): {get_exec}\n\n")
except Exception:
    pass

import subprocess
import inspect
import traceback
try:
    _diag_spawn_calls = os.path.join(diag_dir, "spawn_calls.log")
    _orig_popen = subprocess.Popen
    def _logged_popen(*a, **kw):
        try:
            with open(_diag_spawn_calls, "a", encoding="utf-8") as sf:
                sf.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                sf.write("Popen args: " + repr(a) + "\n")
                sf.write("Popen kwargs: " + repr(kw) + "\n")
                sf.write('Stack:\n')
                sf.write(''.join(traceback.format_stack()))
                sf.write('\n')
        except Exception:
            pass
        return _orig_popen(*a, **kw)
    subprocess.Popen = _logged_popen
    _orig_run = subprocess.run
    def _logged_run(*a, **kw):
        try:
            with open(_diag_spawn_calls, "a", encoding="utf-8") as sf:
                sf.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                sf.write("run args: " + repr(a) + "\n")
                sf.write("run kwargs: " + repr(kw) + "\n")
                sf.write('Stack:\n')
                sf.write(''.join(traceback.format_stack()))
                sf.write('\n')
        except Exception:
            pass
        return _orig_run(*a, **kw)
    subprocess.run = _logged_run
    _orig_call = subprocess.call
    def _logged_call(*a, **kw):
        try:
            with open(_diag_spawn_calls, "a", encoding="utf-8") as sf:
                sf.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                sf.write("call args: " + repr(a) + "\n")
                sf.write("call kwargs: " + repr(kw) + "\n")
                sf.write('Stack:\n')
                sf.write(''.join(traceback.format_stack()))
                sf.write('\n')
        except Exception:
            pass
        return _orig_call(*a, **kw)
    subprocess.call = _logged_call
except Exception:
    pass

import threading
try:
    _diag_spawn = os.path.join(diag_dir, "spawn_trace.log")
    _orig_start = multiprocessing.Process.start
    def _log_and_start(self, *a, **kw):
        try:
            import traceback
            with open(_diag_spawn, "a", encoding="utf-8") as sf:
                sf.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                sf.write(f"Process.start called: name={getattr(self,'name',None)}, target={getattr(self,'_target',None)}\n")
                sf.write(''.join(traceback.format_stack()))
                sf.write("\n")
        except Exception:
            pass
        return _orig_start(self, *a, **kw)
    multiprocessing.Process.start = _log_and_start
    _orig_init = multiprocessing.Process.__init__
    def _log_init(self, *a, **kw):
        try:
            import traceback
            with open(_diag_spawn, "a", encoding="utf-8") as sf:
                sf.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                sf.write(f"Process.__init__ called: args={a}, kwargs={kw}\n")
                sf.write(''.join(traceback.format_stack()))
                sf.write("\n")
        except Exception:
            pass
        return _orig_init(self, *a, **kw)
    multiprocessing.Process.__init__ = _log_init
except Exception:
    pass


import cv2
import numpy as np
import pywintypes
import win32api
import win32event
import winerror
import win32file
import win32pipe
import win32security
import ntsecuritycon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from face_unlock import (
    CREDENTIAL_VAULT, ENCODINGS_FILE, DATA_DIR, LOG_FORMAT, LOG_LEVEL,
    DEFAULT_MATCH_THRESHOLD
)
from face_unlock.recognition import FaceRecognizer
from face_unlock.liveness import LivenessChecker
from face_unlock.credential import get_password, store_password, _encrypt_dpapi

logger = logging.getLogger("face_helper")

PIPE_NAME = r"\\.\pipe\FaceUnlockPipe"
BUFFER_SIZE = 8192
SINGLETON_MUTEX_NAME = r"Global\FaceUnlockHelperSingleton"


def get_security_attributes() -> win32security.SECURITY_ATTRIBUTES:
    sd = win32security.SECURITY_DESCRIPTOR()
    dacl = win32security.ACL()
    everyone_sid = win32security.CreateWellKnownSid(win32security.WinWorldSid)
    system_sid = win32security.CreateWellKnownSid(win32security.WinLocalSystemSid)
    auth_users_sid = win32security.CreateWellKnownSid(win32security.WinAuthenticatedUserSid)

    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, ntsecuritycon.GENERIC_ALL, everyone_sid)
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, ntsecuritycon.GENERIC_ALL, system_sid)
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, ntsecuritycon.GENERIC_ALL, auth_users_sid)

    sd.SetSecurityDescriptorDacl(1, dacl, 0)
    sa = win32security.SECURITY_ATTRIBUTES()
    sa.SECURITY_DESCRIPTOR = sd
    sa.bInheritHandle = 0
    return sa


def load_enrolled_user() -> tuple[str, np.ndarray]:
    if not os.path.exists(ENCODINGS_FILE):
        raise FileNotFoundError(f"Enrollment file not found at {ENCODINGS_FILE}. Run enroll.py first.")

    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)

    if not data:
        raise ValueError("No enrolled users found in vault.")

    user = list(data.keys())[0]
    user_info = data[user]
    if "templates" in user_info:
        templates = user_info["templates"]
    else:
        templates = user_info["encoding"].reshape(1, -1)

    logger.info("Loaded enrolled user '%s': %d template(s) in ensemble.", user, len(templates))
    return user, templates


def _send_pipe(h_pipe, message: str) -> None:
    try:
        data = message.encode("utf-8")
        win32file.WriteFile(h_pipe, data)
    except Exception as e:
        logger.warning("Pipe write error: %s", e)

def perform_face_scan(
    recognizer: FaceRecognizer,
    liveness: LivenessChecker,
    enrolled_templates: np.ndarray,
    h_pipe,
    camera_id: int = 0,
) -> bool:
    cap = None
    try:
        t_start_total = time.perf_counter()
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            logger.error("Camera %d inaccessible", camera_id)
            _send_pipe(h_pipe, "STATUS:Camera unavailable - Use PIN\n")
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        _send_pipe(h_pipe, "STATUS:Looking for enrolled face...\n")

        liveness.reset()
        face_confirmed = False
        frame_count = 0
        consecutive_read_failures = 0

        while True:
            t_fstart = time.perf_counter()
            ret, frame = cap.read()
            t_cap = (time.perf_counter() - t_fstart) * 1000

            if not ret:
                consecutive_read_failures += 1
                if consecutive_read_failures >= 30:
                    logger.error("Camera hardware stalled or disconnected.")
                    _send_pipe(h_pipe, "STATUS:Camera disconnected - Use PIN\n")
                    return False
                time.sleep(0.01)
                continue

            consecutive_read_failures = 0
            frame_count += 1

            if not face_confirmed:
                t_rec_start = time.perf_counter()
                detected = recognizer.detect_and_align(frame, save_debug=False)
                t_rec = (time.perf_counter() - t_rec_start) * 1000

                if detected:
                    live_emb, aligned_crop, det_score, bbox = detected[0]
                    is_match, max_sim, mean_sim, best_idx = recognizer.compare_multi_template(
                        enrolled_templates, live_emb, DEFAULT_MATCH_THRESHOLD
                    )

                    logger.info(
                        "[Frame #%d @ +%.0fms] Cap=%.1fms, Rec=%.1fms | Det=%.2f, MaxSim=%.4f (Tmpl #%d), Match=%s",
                        frame_count, (time.perf_counter() - t_start_total) * 1000, t_cap, t_rec, det_score, max_sim, best_idx, is_match
                    )

                    if is_match:
                        face_confirmed = True
                        try:
                            cv2.imwrite(os.path.join(DATA_DIR, "debug_aligned_live.jpg"), aligned_crop)
                        except Exception:
                            pass
                        logger.info("[OK] Face identity verified (MaxSim=%.4f)! Please blink to confirm...", max_sim)
                        _send_pipe(h_pipe, "STATUS:Face verified! Please blink to unlock...\n")

            if face_confirmed:
                is_closing, blink_score = liveness.update(frame)
                if liveness.is_alive():
                    total_ms = (time.perf_counter() - t_start_total) * 1000
                    logger.info("[OK] Genuine face + blink confirmed in %.1fms total time (%d frames)! Unlocking.", total_ms, frame_count)
                    _send_pipe(h_pipe, "STATUS:Face verified! Unlocking...\n")
                    return True

    except Exception:
        logger.exception("Error during biometric scan")
        return False
    finally:
        if cap is not None:
            cap.release()


READY_FLAG = os.path.join(DATA_DIR, "daemon_ready.flag")
MODEL_MISSING_STATUS = (
    "STATUS:Face model files missing locally — run setup to download them "
    "(offline, no network available)\n"
)


def _buffalo_l_models_present() -> bool:
    model_dir = FaceRecognizer.INSIGHTFACE_MODEL_ROOT if hasattr(FaceRecognizer, "INSIGHTFACE_MODEL_ROOT") else None
    if model_dir is None:
        from face_unlock.recognition import INSIGHTFACE_MODEL_ROOT as _ROOT
        model_dir = _ROOT
    buffalo_dir = os.path.join(str(model_dir), "models", "buffalo_l")
    required_files = ("det_10g.onnx", "w600k_r50.onnx")
    return all(os.path.exists(os.path.join(buffalo_dir, f)) for f in required_files)


def serve_named_pipe():
    sa = get_security_attributes()

    logger.info("==========================================================")
    logger.info(" Face Unlock IPC Server — Pipe-First Initialization")
    logger.info("==========================================================")

    def create_server_pipe():
        return win32pipe.CreateNamedPipe(
            PIPE_NAME,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            win32pipe.PIPE_UNLIMITED_INSTANCES,
            BUFFER_SIZE,
            BUFFER_SIZE,
            0,
            sa,
        )

    try:
        os.remove(READY_FLAG)
    except FileNotFoundError:
        pass

    MODEL_LOAD_WAIT_CAP = 30.0
    state = {
        "recognizer": None,
        "liveness": None,
        "username": None,
        "enrolled_templates": None,
        "models_error": None,
    }
    models_ready = threading.Event()

    def _load_models():
        logger.info("Loading biometric models (RetinaFace + ArcFace + Blink Detector)...")
        t_model_start = time.perf_counter()
        try:
            if not _buffalo_l_models_present():
                state["models_error"] = MODEL_MISSING_STATUS.strip()
                logger.error("InsightFace model files missing at project-local cache.")
                return
            state["recognizer"] = FaceRecognizer(name="buffalo_l", det_size=(320, 320))
            state["liveness"] = LivenessChecker()
            dummy_warmup = np.zeros((480, 640, 3), dtype=np.uint8)
            state["liveness"].update(dummy_warmup)
            state["liveness"].reset()
            state["username"], state["enrolled_templates"] = load_enrolled_user()
            t_model_ms = (time.perf_counter() - t_model_start) * 1000
            logger.info("All biometric models loaded & pre-warmed in %.1fms!", t_model_ms)
        except Exception as e:
            state["models_error"] = str(e)
            logger.exception("Failed loading biometric models")
        finally:
            try:
                try:
                    import traceback, subprocess, json
                    mypid = os.getpid()
                    trace_path = os.path.join(DATA_DIR, "spawn_trace.log")
                    with open(trace_path, "a", encoding="utf-8") as tf:
                        tf.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        matches = []
                        try:
                            import wmi
                            c = wmi.WMI()
                            for p in c.Win32_Process(Name="pythonw.exe"):
                                try:
                                    parent = int(p.ParentProcessId)
                                except Exception:
                                    parent = None
                                if parent == mypid:
                                    matches.append({"pid": int(p.ProcessId), "cmd": getattr(p, "CommandLine", ""), "exe": getattr(p, "ExecutablePath", "")})
                            tf.write("pythonw children: " + json.dumps(matches) + "\n")
                        except Exception:
                            try:
                                out = subprocess.check_output(["wmic", "process", "where", f"ParentProcessId={mypid}", "get", "ProcessId,Name,CommandLine,ExecutablePath", "/FORMAT:LIST"], universal_newlines=True)
                                tf.write("wmic output:\n" + out + "\n")
                            except Exception:
                                tf.write("could not query child processes\n")

                        try:
                            tf.write("Python stacks:\n")
                            for tid, frame in sys._current_frames().items():
                                tf.write(f"--- Thread {tid} ---\n")
                                tf.write(''.join(traceback.format_stack(frame)))
                            tf.write("Loaded modules:\n")
                            tf.write(','.join(list(sys.modules.keys())) + "\n\n")
                        except Exception as e:
                            tf.write("error capturing stacks: " + str(e) + "\n")
                except Exception:
                    pass

                with open(READY_FLAG, "w") as rf:
                    rf.write(f"ready:{time.time():.0f}\n")
                logger.info("Readiness flag written to %s", READY_FLAG)
            except Exception as e:
                logger.warning("Could not write readiness flag: %s", e)
            models_ready.set()

    h_pipe = create_server_pipe()
    threading.Thread(target=_load_models, name="model-loader", daemon=True).start()

    def _monitor_children():
        try:
            import subprocess, traceback
            mypid = os.getpid()
            trace_path = os.path.join(DATA_DIR, "spawn_trace.log")
            end_time = time.time() + 60.0
            seen = set()
            while time.time() < end_time:
                try:
                    out = subprocess.check_output(["wmic", "process", "where", f"ParentProcessId={mypid}", "get", "ProcessId,Name,CommandLine,ExecutablePath", "/FORMAT:LIST"], universal_newlines=True, stderr=subprocess.DEVNULL)
                    if "pythonw.exe" in out:
                        pids = set()
                        for line in out.splitlines():
                            if line.strip().startswith("ProcessId="):
                                try:
                                    pidv = int(line.split("=",1)[1].strip())
                                    pids.add(pidv)
                                except Exception:
                                    pass
                        new = pids - seen
                        if new:
                            seen.update(new)
                            with open(trace_path, "a", encoding="utf-8") as tf:
                                tf.write(f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                                tf.write(f"detected child PIDs: {sorted(list(new))}\n")
                                tf.write("Current stack:\n")
                                for tid, frame in sys._current_frames().items():
                                    tf.write(f"--- Thread {tid} ---\n")
                                    tf.write(''.join(traceback.format_stack(frame)))
                                tf.write("Loaded modules:\n")
                                tf.write(','.join(list(sys.modules.keys())) + "\n\n")
                            try:
                                for cp in new:
                                    subprocess.run(["taskkill", "/PID", str(cp), "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    with open(trace_path, "a", encoding="utf-8") as tf:
                                        tf.write(f"terminated child PID {cp}\n")
                            except Exception:
                                pass
                except Exception:
                    pass
                time.sleep(0.5)
        except Exception:
            pass

    threading.Thread(target=_monitor_children, name="child-monitor", daemon=True).start()

    logger.info("==========================================================")
    logger.info(" IPC Server Listening on %s", PIPE_NAME)
    logger.info(" Mode: Pipe-Ready First, Zero Timeout, Full FPS")
    logger.info("==========================================================")

    while True:
        try:
            if h_pipe is None:
                h_pipe = create_server_pipe()

            logger.info("Waiting for lock screen Credential Provider connection...")
            win32pipe.ConnectNamedPipe(h_pipe, None)
            logger.info(">>> LogonUI Secure Desktop Connected! <<<")

            hr, data = win32file.ReadFile(h_pipe, BUFFER_SIZE)
            if data:
                req = data.decode("utf-8", errors="ignore").strip()
                logger.info("Received request: '%s'", req)

                if req == "SCAN_REQUEST":
                    if not models_ready.is_set():
                        logger.info(
                            "SCAN_REQUEST while models still loading; "
                            "notifying client and waiting (cap %.0fs)...",
                            MODEL_LOAD_WAIT_CAP,
                        )
                        _send_pipe(h_pipe, "STATUS:Loading face engine, please wait...\n")
                        models_ready.wait(timeout=MODEL_LOAD_WAIT_CAP)

                    if not models_ready.is_set():
                        logger.error(
                            "Model loading did not complete within %.0fs; returning MATCH_FAIL.",
                            MODEL_LOAD_WAIT_CAP,
                        )
                        _send_pipe(h_pipe, "STATUS:Face engine still initializing - Use PIN\n")
                        _send_pipe(h_pipe, "MATCH_FAIL\n")
                    elif state["models_error"]:
                        if state["models_error"] == MODEL_MISSING_STATUS.strip():
                            _send_pipe(h_pipe, MODEL_MISSING_STATUS)
                        else:
                            _send_pipe(h_pipe, f"STATUS:Error loading face engine ({state['models_error']})\n")
                    else:
                        match_ok = perform_face_scan(
                            state["recognizer"],
                            state["liveness"],
                            state["enrolled_templates"],
                            h_pipe,
                        )

                        if match_ok:
                            enc_bytes = None
                            if os.path.exists(CREDENTIAL_VAULT):
                                with open(CREDENTIAL_VAULT, "rb") as vf:
                                    enc_bytes = vf.read()
                            else:
                                pwd = get_password(state["username"])
                                if pwd:
                                    enc_bytes = _encrypt_dpapi(pwd)

                            if enc_bytes:
                                hex_payload = enc_bytes.hex()
                                domain = os.environ.get("USERDOMAIN") or os.environ.get("COMPUTERNAME") or ""
                                resp = f"MATCH_SUCCESS:{state['username']}|{domain}|{hex_payload}\n"
                                _send_pipe(h_pipe, resp)
                                logger.info("Authentication payload delivered to Credential Provider. (domain=%s)", domain)
                            else:
                                _send_pipe(h_pipe, "MATCH_FAIL\n")
                        else:
                            _send_pipe(h_pipe, "MATCH_FAIL\n")

            time.sleep(0.1)
            win32file.CloseHandle(h_pipe)
            h_pipe = None
            logger.info("Session finished. Resetting pipe.\n")

        except pywintypes.error as pe:
            if pe.winerror in (109, 232):
                logger.info("Client disconnected.")
            else:
                logger.warning("Named pipe error: %s", pe)
            if h_pipe:
                try:
                    win32file.CloseHandle(h_pipe)
                except Exception:
                    pass
                h_pipe = None
            time.sleep(0.2)
        except KeyboardInterrupt:
            logger.info("Face Helper server stopping.")
            if h_pipe:
                try:
                    win32file.CloseHandle(h_pipe)
                except Exception:
                    pass
            break
        except Exception:
            logger.exception("Unhandled error in IPC server")
            if h_pipe:
                try:
                    win32file.CloseHandle(h_pipe)
                except Exception:
                    pass
                h_pipe = None
            time.sleep(1)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    log_file = os.path.join(DATA_DIR, "face_helper.log")
    handlers = [
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL, handlers=handlers)
    logger.info("Startup exec info: sys.executable=%s, sys._base_executable=%s", sys.executable, getattr(sys, "_base_executable", ""))
    try:
        mutex = win32event.CreateMutex(None, False, SINGLETON_MUTEX_NAME)
    except pywintypes.error as e:
        if e.winerror in (winerror.ERROR_ALREADY_EXISTS, winerror.ERROR_ACCESS_DENIED):
            logger.error("Another face_helper.py instance is already running; exiting.")
            return
        raise
    if win32api.GetLastError() in (winerror.ERROR_ALREADY_EXISTS, winerror.ERROR_ACCESS_DENIED):
        logger.error("Another face_helper.py instance is already running; exiting.")
        return
    try:
        serve_named_pipe()
    finally:
        if mutex:
            try:
                win32event.ReleaseMutex(mutex)
            except Exception:
                pass


if __name__ == "__main__":
    main()
