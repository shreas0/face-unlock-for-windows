
import time
import win32file
import win32pipe

PIPE_NAME = r"\\.\pipe\FaceUnlockPipe"

def test_pipe_connection():
    print(f"Connecting to {PIPE_NAME}...")
    try:
        handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        print("[OK] Connected to Face Unlock Named Pipe server!")

        req = b"SCAN_REQUEST\n"
        win32file.WriteFile(handle, req)
        print("Sent SCAN_REQUEST. Waiting for face match & blink...")

        while True:
            result, data = win32file.ReadFile(handle, 4096)
            if data:
                text = data.decode("utf-8", errors="ignore").strip()
                print(f"  [FROM SERVER] {text}")
                if "MATCH_SUCCESS" in text or "MATCH_FAIL" in text:
                    break

        win32file.CloseHandle(handle)
        print("[OK] IPC Test session closed successfully.")

    except Exception as e:
        print(f"[FAIL] Pipe connection failed: {e}")
        print("Make sure 'python face_helper.py' is running in another window!")

if __name__ == "__main__":
    test_pipe_connection()
