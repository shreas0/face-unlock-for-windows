#include "FaceUnlockProvider.h"
#include "helpers.h"
#include <strsafe.h>
#include <stdio.h>
#include <sddl.h>
void ProviderLog(const WCHAR* format, ...)
{
    WCHAR szBuffer[1024];
    va_list args;
    va_start(args, format);
    StringCchVPrintfW(szBuffer, ARRAYSIZE(szBuffer), format, args);
    va_end(args);
    OutputDebugStringW(szBuffer);
    FILE* f = NULL;
    _wfopen_s(&f, L"C:\\ProgramData\\FaceUnlock_Provider.log", L"a, ccs=UTF-8");
    if (f)
    {
        SYSTEMTIME st;
        GetLocalTime(&st);
        fwprintf(f, L"[%02d:%02d:%02d.%03d] %s\n", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds, szBuffer);
        fclose(f);
    }
}
CFaceCredential::CFaceCredential(CFaceProvider* pProvider) :
    _cRef(1),
    _pProvider(pProvider),
    _pEvents(NULL),
    _bSelected(FALSE),
    _bMatchSucceeded(FALSE),
    _hWorkerThread(NULL),
    _hStopEvent(NULL),
    _dwHelperPID(0)
{
    _szStatus[0] = L'\0';
    _szUsername[0] = L'\0';
    _szDomain[0] = L'\0';
    _szPassword[0] = L'\0';
    StringCchCopyW(_szStatus, ARRAYSIZE(_szStatus), L"Looking for face... Look at camera");
    ProviderLog(L"CFaceCredential created.");
}
CFaceCredential::~CFaceCredential()
{
    ProviderLog(L"CFaceCredential destroyed.");
    if (_hStopEvent)
    {
        SetEvent(_hStopEvent);
    }
    if (_hWorkerThread)
    {
        WaitForSingleObject(_hWorkerThread, 2000);
        CloseHandle(_hWorkerThread);
    }
    if (_hStopEvent)
    {
        CloseHandle(_hStopEvent);
    }
    SecureClearString(_szPassword);
    if (_pEvents)
    {
        _pEvents->Release();
    }
}
IFACEMETHODIMP CFaceCredential::QueryInterface(REFIID riid, void** ppv)
{
    static const QITAB qit[] = {
        QITABENT(CFaceCredential, ICredentialProviderCredential),
        QITABENT(CFaceCredential, ICredentialProviderCredential2),
        { 0 },
    };
    return QISearch(this, qit, riid, ppv);
}
IFACEMETHODIMP_(ULONG) CFaceCredential::AddRef()
{
    return InterlockedIncrement(&_cRef);
}
IFACEMETHODIMP_(ULONG) CFaceCredential::Release()
{
    ULONG cRef = InterlockedDecrement(&_cRef);
    if (cRef == 0)
    {
        delete this;
    }
    return cRef;
}
IFACEMETHODIMP CFaceCredential::Advise(ICredentialProviderCredentialEvents* pEvents)
{
    ProviderLog(L"CFaceCredential::Advise called.");
    if (_pEvents)
    {
        _pEvents->Release();
    }
    _pEvents = pEvents;
    if (_pEvents)
    {
        _pEvents->AddRef();
    }
    if (!_hWorkerThread)
    {
        _hStopEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
        _hWorkerThread = CreateThread(NULL, 0, _PipeListenerThread, this, 0, NULL);
        ProviderLog(L"Launched PipeListenerThread from Advise.");
    }
    return S_OK;
}
IFACEMETHODIMP CFaceCredential::UnAdvise()
{
    ProviderLog(L"CFaceCredential::UnAdvise called.");
    if (_pEvents)
    {
        _pEvents->Release();
        _pEvents = NULL;
    }
    return S_OK;
}
IFACEMETHODIMP CFaceCredential::SetSelected(BOOL* pbAutoLogon)
{
    ProviderLog(L"CFaceCredential::SetSelected called.");
    _bSelected = TRUE;
    *pbAutoLogon = _bMatchSucceeded; 
    if (!_hWorkerThread)
    {
        _hStopEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
        _hWorkerThread = CreateThread(NULL, 0, _PipeListenerThread, this, 0, NULL);
        ProviderLog(L"Launched PipeListenerThread from SetSelected.");
    }
    return S_OK;
}
IFACEMETHODIMP CFaceCredential::SetDeselected()
{
    ProviderLog(L"CFaceCredential::SetDeselected called.");
    _bSelected = FALSE;
    return S_OK;
}
IFACEMETHODIMP CFaceCredential::GetFieldState(
    DWORD dwFieldID,
    CREDENTIAL_PROVIDER_FIELD_STATE* pcpfs,
    CREDENTIAL_PROVIDER_FIELD_INTERACTIVE_STATE* pcpfis
)
{
    if (!pcpfs || !pcpfis)
    {
        return E_POINTER;
    }
    switch (dwFieldID)
    {
    case FCFI_TILEIMAGE:
    case FCFI_TITLE:
    case FCFI_SUBTITLE:
    case FCFI_STATUS:
        *pcpfs = CPFS_DISPLAY_IN_BOTH;
        *pcpfis = CPFIS_NONE;
        break;
    default:
        *pcpfs = CPFS_HIDDEN;
        *pcpfis = CPFIS_NONE;
        return E_INVALIDARG;
    }
    return S_OK;
}
IFACEMETHODIMP CFaceCredential::GetStringValue(DWORD dwFieldID, LPWSTR* ppsz)
{
    if (!ppsz)
    {
        return E_POINTER;
    }
    LPCWSTR pszText = L"";
    switch (dwFieldID)
    {
    case FCFI_TITLE:
        pszText = L"Face Unlock";
        break;
    case FCFI_SUBTITLE:
        pszText = L"Look at camera & blink to auto-unlock";
        break;
    case FCFI_STATUS:
        pszText = _szStatus;
        break;
    default:
        return E_INVALIDARG;
    }
    return SHStrDupW(pszText, ppsz);
}
IFACEMETHODIMP CFaceCredential::GetBitmapValue(DWORD dwFieldID, HBITMAP* phbmp)
{
    if (!phbmp)
    {
        return E_POINTER;
    }
    *phbmp = NULL;
    return E_NOTIMPL;
}
IFACEMETHODIMP CFaceCredential::GetCheckboxValue(DWORD, BOOL*, LPWSTR*) { return E_NOTIMPL; }
IFACEMETHODIMP CFaceCredential::GetSubmitButtonValue(DWORD dwFieldID, DWORD* pdwAdjacentTo)
{
    return E_NOTIMPL;
}
IFACEMETHODIMP CFaceCredential::GetComboBoxValueCount(DWORD, DWORD*, DWORD*) { return E_NOTIMPL; }
IFACEMETHODIMP CFaceCredential::GetComboBoxValueAt(DWORD, DWORD, LPWSTR*) { return E_NOTIMPL; }
IFACEMETHODIMP CFaceCredential::SetStringValue(DWORD, LPCWSTR) { return E_NOTIMPL; }
IFACEMETHODIMP CFaceCredential::SetCheckboxValue(DWORD, BOOL) { return E_NOTIMPL; }
IFACEMETHODIMP CFaceCredential::SetComboBoxSelectedValue(DWORD, DWORD) { return E_NOTIMPL; }
IFACEMETHODIMP CFaceCredential::CommandLinkClicked(DWORD) { return E_NOTIMPL; }
IFACEMETHODIMP CFaceCredential::GetSerialization(
    CREDENTIAL_PROVIDER_GET_SERIALIZATION_RESPONSE* pcpgsr,
    CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* pcpcs,
    LPWSTR* ppszOptionalStatusText,
    CREDENTIAL_PROVIDER_STATUS_ICON* pcpsiOptionalStatusIcon
)
{
    ProviderLog(L"GetSerialization called. MatchSucceeded=%d", _bMatchSucceeded);
    if (!pcpgsr || !pcpcs)
    {
        return E_POINTER;
    }
    *pcpgsr = CPGSR_NO_CREDENTIAL_FINISHED;
    ZeroMemory(pcpcs, sizeof(*pcpcs));
    if (_bMatchSucceeded && wcslen(_szPassword) > 0)
    {
        ProviderLog(L"Packing credentials via CredPackAuthenticationBufferW for user '%s'...", _szUsername);
        HRESULT hr = CreateKerberosLogonSerialization(_szDomain, _szUsername, _szPassword, pcpcs);
        SecureClearString(_szPassword);
        if (SUCCEEDED(hr))
        {
            ProviderLog(L"CredPack succeeded. Auto-logging on with CPGSR_RETURN_CREDENTIAL_FINISHED (size=%d, pkg=%u)", pcpcs->cbSerialization, pcpcs->ulAuthenticationPackage);
            *pcpgsr = CPGSR_RETURN_CREDENTIAL_FINISHED;
            return S_OK;
        }
        else
        {
            ProviderLog(L"CreateKerberosLogonSerialization failed: hr=0x%08X", hr);
        }
    }
    return S_OK;
}
IFACEMETHODIMP CFaceCredential::ReportResult(
    NTSTATUS ntsStatus,
    NTSTATUS ntsSubstatus,
    LPWSTR* ppszOptionalStatusText,
    CREDENTIAL_PROVIDER_STATUS_ICON* pcpsiOptionalStatusIcon
)
{
    ProviderLog(L"ReportResult called: status=0x%08X, substatus=0x%08X", ntsStatus, ntsSubstatus);
    if (ppszOptionalStatusText)
    {
        *ppszOptionalStatusText = NULL;
    }
    if (pcpsiOptionalStatusIcon)
    {
        *pcpsiOptionalStatusIcon = CPSI_NONE;
    }
    SecureClearString(_szPassword);
    _bMatchSucceeded = FALSE;
    return S_OK;
}
IFACEMETHODIMP CFaceCredential::GetUserSid(LPWSTR* ppszSid)
{
    if (!ppszSid) return E_POINTER;
    *ppszSid = NULL;
    const WCHAR* pszTargetUser = (wcslen(_szUsername) > 0) ? _szUsername : L"shres";
    BYTE sidBuffer[SECURITY_MAX_SID_SIZE];
    DWORD cbSid = sizeof(sidBuffer);
    WCHAR szDomain[256];
    DWORD cchDomain = ARRAYSIZE(szDomain);
    SID_NAME_USE snu;
    if (LookupAccountNameW(NULL, pszTargetUser, (PSID)sidBuffer, &cbSid, szDomain, &cchDomain, &snu))
    {
        LPWSTR pszSidString = NULL;
        if (ConvertSidToStringSidW((PSID)sidBuffer, &pszSidString))
        {
            HRESULT hr = SHStrDupW(pszSidString, ppszSid);
            LocalFree(pszSidString);
            ProviderLog(L"GetUserSid successfully returned SID for user '%s': %s", pszTargetUser, *ppszSid ? *ppszSid : L"<null>");
            return hr;
        }
    }
    DWORD dwErr = GetLastError();
    ProviderLog(L"GetUserSid failed to lookup SID for user '%s' (err=%d)", pszTargetUser, dwErr);
    return HRESULT_FROM_WIN32(dwErr);
}
void CFaceCredential::UpdateStatus(const WCHAR* statusText)
{
    StringCchCopyW(_szStatus, ARRAYSIZE(_szStatus), statusText);
    ProviderLog(L"Status updated: %s", _szStatus);
    if (_pEvents)
    {
        _pEvents->SetFieldString(this, FCFI_STATUS, _szStatus);
        _pEvents->SetFieldState(this, FCFI_STATUS, CPFS_DISPLAY_IN_BOTH);
    }
}
void CFaceCredential::TriggerFaceMatchSuccess(const WCHAR* username, const WCHAR* domain, const WCHAR* password)
{
    ProviderLog(L"TriggerFaceMatchSuccess called for '%s'", username);
    StringCchCopyW(_szUsername, ARRAYSIZE(_szUsername), username ? username : L"");
    StringCchCopyW(_szDomain, ARRAYSIZE(_szDomain), domain ? domain : L"");
    StringCchCopyW(_szPassword, ARRAYSIZE(_szPassword), password ? password : L"");
    _bMatchSucceeded = TRUE;
    UpdateStatus(L"Face verified! Auto-logging in...");
    if (_pProvider)
    {
        _pProvider->NotifyCredentialsChanged();
    }
}
DWORD WINAPI CFaceCredential::_PipeListenerThread(LPVOID lpParam)
{
    CFaceCredential* pThis = (CFaceCredential*)lpParam;
    pThis->_RunPipeSession();
    return 0;
}
static DWORD AutoLaunchHelperProcess()
{
    ProviderLog(L"Attempting on-demand auto-launch of face_helper.py...");
    WCHAR szPythonPath[512] = { 0 };
    WCHAR szInstallDir[512] = { 0 };
    DWORD dwType = 0;
    DWORD cbData = sizeof(szPythonPath);
    HKEY hKey = NULL;
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, L"SOFTWARE\\FaceUnlock", 0, KEY_READ, &hKey) == ERROR_SUCCESS)
    {
        cbData = sizeof(szPythonPath);
        RegQueryValueExW(hKey, L"PythonPath", NULL, &dwType, (BYTE*)szPythonPath, &cbData);
        cbData = sizeof(szInstallDir);
        RegQueryValueExW(hKey, L"InstallDir", NULL, &dwType, (BYTE*)szInstallDir, &cbData);
        RegCloseKey(hKey);
    }
    if (wcslen(szInstallDir) == 0)
    {
        StringCchCopyW(szInstallDir, ARRAYSIZE(szInstallDir), L"C:\\Users\\shres\\FaceUnlock");
    }
    WCHAR szScriptPath[512];
    StringCchPrintfW(szScriptPath, ARRAYSIZE(szScriptPath), L"%s\\face_helper.py", szInstallDir);
    if (wcslen(szPythonPath) == 0)
    {
        StringCchCopyW(szPythonPath, ARRAYSIZE(szPythonPath), L"pythonw.exe");
    }
    WCHAR szCmdLine[1024];
    StringCchPrintfW(szCmdLine, ARRAYSIZE(szCmdLine), L"\"%s\" \"%s\"", szPythonPath, szScriptPath);
    ProviderLog(L"Launching process: %s (CWD: %s)", szCmdLine, szInstallDir);
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));
    if (CreateProcessW(NULL, szCmdLine, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, szInstallDir, &si, &pi))
    {
        ProviderLog(L"Successfully spawned face_helper process (PID=%d)", pi.dwProcessId);
        DWORD dwPid = pi.dwProcessId;
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        return dwPid;
    }
    else
    {
        DWORD dwErr = GetLastError();
        ProviderLog(L"CreateProcessW failed with error %d", dwErr);
        return 0;
    }
}
static BOOL IsProcessAlive(DWORD dwPid)
{
    if (dwPid == 0) return FALSE;
    HANDLE hProc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, dwPid);
    if (!hProc) return FALSE;
    DWORD exitCode = 0;
    BOOL result = GetExitCodeProcess(hProc, &exitCode);
    CloseHandle(hProc);
    return (result && exitCode == STILL_ACTIVE);
}
void CFaceCredential::_RunPipeSession()
{
    ProviderLog(L"Pipe worker thread started.");
    const int MAX_RETRIES = 120;
    DWORD dwStartTick = GetTickCount();
    HANDLE hPipe = INVALID_HANDLE_VALUE;
    for (int retry = 0; retry < MAX_RETRIES; retry++)
    {
        if (WaitForSingleObject(_hStopEvent, 0) == WAIT_OBJECT_0)
        {
            return;
        }
        hPipe = CreateFileW(
            FACE_UNLOCK_PIPE_NAME,
            GENERIC_READ | GENERIC_WRITE,
            0,
            NULL,
            OPEN_EXISTING,
            0,
            NULL
        );
        if (hPipe != INVALID_HANDLE_VALUE)
        {
            ProviderLog(L"Connected to FaceUnlockPipe on attempt %d!", retry + 1);
            break;
        }
        DWORD err = GetLastError();
        if (err == ERROR_PIPE_BUSY)
        {
            WaitNamedPipeW(FACE_UNLOCK_PIPE_NAME, 1000);
            continue;
        }
        if (retry == 0)
        {
            UpdateStatus(L"Starting face engine...");
            _dwHelperPID = AutoLaunchHelperProcess();
            Sleep(500);
            continue;
        }
        if (_dwHelperPID != 0 && !IsProcessAlive(_dwHelperPID))
        {
            ProviderLog(L"Helper process PID=%d died. Relaunching...", _dwHelperPID);
            UpdateStatus(L"Face engine crashed — restarting...");
            _dwHelperPID = AutoLaunchHelperProcess();
            Sleep(1000);
            continue;
        }
        DWORD dwElapsedSec = (GetTickCount() - dwStartTick) / 1000;
        if (retry % 4 == 0)  
        {
            WCHAR szWaitStatus[128];
            StringCchPrintfW(szWaitStatus, ARRAYSIZE(szWaitStatus),
                L"Loading face engine... (%ds)", dwElapsedSec);
            UpdateStatus(szWaitStatus);
        }
        if (retry % 10 == 0)
        {
            ProviderLog(L"CreateFileW attempt %d failed (error=%d, elapsed=%ds)", retry + 1, err, dwElapsedSec);
        }
        DWORD dwSleep = (retry < 5) ? 200 : 500;
        Sleep(dwSleep);
    }
    if (hPipe == INVALID_HANDLE_VALUE)
    {
        DWORD dwElapsedSec = (GetTickCount() - dwStartTick) / 1000;
        ProviderLog(L"Could not connect to FaceUnlockPipe after %ds.", dwElapsedSec);
        UpdateStatus(L"Face daemon offline — Use PIN/Password");
        return;
    }
    UpdateStatus(L"Looking for face... Please blink");
    DWORD dwWritten = 0;
    const char szReq[] = "SCAN_REQUEST\n";
    WriteFile(hPipe, szReq, (DWORD)strlen(szReq), &dwWritten, NULL);
    ProviderLog(L"Sent SCAN_REQUEST to pipe.");
    char buffer[4096];
    DWORD dwRead = 0;
    while (WaitForSingleObject(_hStopEvent, 0) != WAIT_OBJECT_0)
    {
        ZeroMemory(buffer, sizeof(buffer));
        BOOL bSuccess = ReadFile(hPipe, buffer, sizeof(buffer) - 1, &dwRead, NULL);
        if (!bSuccess || dwRead == 0)
        {
            ProviderLog(L"ReadFile from pipe ended: success=%d, read=%d, err=%d", bSuccess, dwRead, GetLastError());
            break;
        }
        ProviderLog(L"Received from pipe: %S", buffer);
        if (strncmp(buffer, "STATUS:", 7) == 0)
        {
            WCHAR szStatusW[256];
            MultiByteToWideChar(CP_UTF8, 0, buffer + 7, -1, szStatusW, ARRAYSIZE(szStatusW));
            for (int i = 0; szStatusW[i]; i++) { if (szStatusW[i] == L'\r' || szStatusW[i] == L'\n') szStatusW[i] = L'\0'; }
            UpdateStatus(szStatusW);
        }
        else if (strncmp(buffer, "MATCH_SUCCESS:", 14) == 0)
        {
            char* pPayload = buffer + 14;
            ProviderLog(L"Parsing MATCH_SUCCESS payload raw (len=%u): %S", (unsigned)strlen(pPayload), pPayload);
            if (pPayload)
            {
                char* pUserTok = NULL;
                char* pDomTok = NULL;
                char* pHexTok = NULL;
                char* sep1 = strchr(pPayload, '|');
                if (sep1)
                {
                    *sep1 = '\0';
                    pUserTok = pPayload;
                    char* rest = sep1 + 1;
                    char* sep2 = strchr(rest, '|');
                    if (sep2)
                    {
                        *sep2 = '\0';
                        pDomTok = rest; 
                        pHexTok = sep2 + 1; 
                    }
                }
                if (pUserTok && pHexTok && strlen(pHexTok) > 0)
                {
                    size_t hexLen = strlen(pHexTok);
                    BYTE* pEncData = (BYTE*)malloc(hexLen / 2);
                    if (pEncData)
                    {
                        for (size_t i = 0; i < hexLen; i += 2)
                        {
                            unsigned int byteVal = 0;
                            sscanf_s(pHexTok + i, "%02x", &byteVal);
                            pEncData[i / 2] = (BYTE)byteVal;
                        }
                        WCHAR szDecryptedPass[256];
                        HRESULT hr = DecryptDPAPIPassword(pEncData, (DWORD)(hexLen / 2), szDecryptedPass, ARRAYSIZE(szDecryptedPass));
                        free(pEncData);
                        if (SUCCEEDED(hr))
                        {
                            ProviderLog(L"Decrypted DPAPI password successfully! Auto-submitting logon.");
                            WCHAR szUserW[256], szDomW[256];
                            MultiByteToWideChar(CP_UTF8, 0, pUserTok, -1, szUserW, ARRAYSIZE(szUserW));
                            MultiByteToWideChar(CP_UTF8, 0, pDomTok ? pDomTok : "", -1, szDomW, ARRAYSIZE(szDomW));
                            TriggerFaceMatchSuccess(szUserW, szDomW, szDecryptedPass);
                            CloseHandle(hPipe);
                            return;
                        }
                        else
                        {
                            ProviderLog(L"DecryptDPAPIPassword failed: hr=0x%08X", hr);
                        }
                    }
                }
                else
                {
                    ProviderLog(L"MATCH_SUCCESS parse error: user=%hs, domain=%hs, hex=%hs", pUserTok ? pUserTok : "<null>", pDomTok ? pDomTok : "<null>", (pHexTok ? pHexTok : "<null>"));
                }
            }
        }
        else if (strncmp(buffer, "MATCH_FAIL", 10) == 0)
        {
            ProviderLog(L"Received MATCH_FAIL from pipe.");
            UpdateStatus(L"Face match timed out. Use PIN/Password");
            break;
        }
    }
    CloseHandle(hPipe);
    ProviderLog(L"Pipe worker thread exiting.");
}
