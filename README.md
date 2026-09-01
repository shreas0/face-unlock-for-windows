# Native Windows Credential Provider Face Unlock

A native C++ Windows Credential Provider (COM In-Process DLL) and Python MediaPipe face-recognition service that provides real biometric face unlocking on the Windows 11 lock screen (**Secure Desktop / LogonUI**), with **zero keystroke injection**.

---

## 🏛️ Architecture

```
+------------------------------------------------------------------------------------+
|                         Windows Secure Desktop (LogonUI.exe)                       |
|                                                                                    |
|   +--------------------------+                 +-------------------------------+   |
|   | Microsoft Standard PIN   |                 | FaceUnlockProvider.dll (Tile) |   |
|   | & Password Tiles         |                 |   (ICredentialProvider)       |   |
|   | (Always safe fallback)   |                 +---------------+---------------+   |
|   +--------------------------+                                 |                   |
+----------------------------------------------------------------|-------------------+
                                                                 | Named Pipe IPC
                                                                 | (\\.\pipe\FaceUnlockPipe)
                                                                 v
+----------------------------------------------------------------+-------------------+
|                        Background Service (Session 0 or User)                      |
|                                                                                    |
|   +----------------------------------------------------------------------------+   |
|   | face_helper.py (MediaPipe Face Mesh + Neural Blendshape Blink Detector)    |   |
|   | - Lazily opens standard RGB webcam on request                              |   |
|   | - Compares facial geometry against data/encodings.pkl                      |   |
|   | - Verifies genuine blink liveness (anti-photo spoofing)                    |   |
|   | - Delivers DPAPI-encrypted token to DLL upon verified match                |   |
|   +----------------------------------------------------------------------------+   |
+------------------------------------------------------------------------------------+
                                                                 |
                                                                 | GetSerialization()
                                                                 v
                                         +-------------------------------------------+
                                         | LSA Authentication Package                |
                                         | (KERB_INTERACTIVE_LOGON / MSV1_0)         |
                                         | -> Native Windows Session Unlock!         |
                                         +-------------------------------------------+
```

---

## ⚠️ Critical Safety & Recovery Information

> [!IMPORTANT]
> **Safety First — Coexistence with PIN/Password:**
> `FaceUnlockProvider` registers as an **additional tile** alongside your normal Windows PIN and password tiles. It **never** replaces, hides, or modifies Microsoft's built-in credential providers. You can always click your PIN or Password tile to sign in normally.

> [!CAUTION]
> **Safe Testing Precautions:**
> Before testing on the lock screen for the first time:
> 1. Ensure you know your Windows account password or PIN.
> 2. Keep the `emergency_remove.reg` script handy (e.g. on a USB drive or your desktop).
> 3. If you ever need to disable the provider offline, boot into **Windows Safe Mode** or **Recovery Environment Command Prompt** and run:
>    ```cmd
>    reg import C:\Users\shres\FaceUnlock\emergency_remove.reg
>    ```

---

## 🛠️ Prerequisites & Build

### 1. Requirements
- **Windows 11** (64-bit)
- **Python 3.10+** (with `opencv-python`, `mediapipe`, `numpy`, `keyring`, `pywin32`)
- **Visual Studio 2022** (Community Edition or Build Tools) with **"Desktop development with C++"** workload.

### 2. Build the C++ DLL
Open a Developer Command Prompt (or run the provided build script):

```powershell
cd C:\Users\shres\FaceUnlock\FaceUnlockProvider
.\build_provider.bat
```

*Or compile via CMake:*
```powershell
cmake -B build -A x64
cmake --build build --config Release
```

The output file is **`FaceUnlockProvider.dll`** (64-bit).

---

## 🚀 Setup & Execution Guide

### Step 1: Enroll Your Face & Password
```powershell
cd C:\Users\shres\FaceUnlock
python download_models.py
python enroll.py
```
- `download_models.py` performs a one-time download of InsightFace `buffalo_l` model files
  into a deterministic project-local cache:
  `C:\Users\shres\FaceUnlock\models\insightface\models\buffalo_l`
- This prevents network fetch attempts when `face_helper.py` runs during lock/boot.
- Captures 7–10 face samples.
- Encrypts your Windows PIN or Password via **Windows DPAPI** (`data/vault.enc`).

### Step 2: Test the Named Pipe IPC
Start the face helper daemon in one terminal:
```powershell
python face_helper.py
```
In a second terminal, run the pipe client tester:
```powershell
python test_pipe.py
```
*(Verify that the helper connects, activates the camera, verifies your blink, and reports success)*.

### Step 3: Register the Credential Provider
Open PowerShell **as Administrator** and run:
```powershell
powershell -ExecutionPolicy Bypass -File register_provider.ps1
```
This installs `FaceUnlockProvider.dll` to `C:\Windows\System32\` and registers its COM GUID (`{E7A2A9B8-4384-48C8-8547-074C46A2C59D}`).

### Step 4: Lock & Unlock!
1. Ensure `python face_helper.py` is running (or registered via Task Scheduler).
2. Lock your computer (<kbd>Win</kbd> + <kbd>L</kbd>).
3. On the lock screen, select the **Face Unlock** tile.
4. Look at the camera and blink.
5. Windows will natively authenticate and unlock into your desktop!

---

## 🧹 Uninstallation

To completely remove the Credential Provider:
```powershell
# In Administrator PowerShell:
powershell -ExecutionPolicy Bypass -File unregister_provider.ps1

# To delete stored face data and credentials:
python enroll.py --delete-all
```
