#pragma once
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <credentialprovider.h>
#include <ntsecapi.h>
#include <wincrypt.h>
#include <shlwapi.h>
#include <strsafe.h>
#include <new>
#pragma comment(lib, "Shlwapi.lib")
#pragma comment(lib, "Advapi32.lib")
#pragma comment(lib, "Secur32.lib")
#pragma comment(lib, "Crypt32.lib")
#pragma comment(lib, "Credui.lib")
#pragma comment(lib, "Ole32.lib")
#pragma comment(lib, "OleAut32.lib")
static const GUID CLSID_FaceUnlockProvider = 
    { 0xe7a2a9b8, 0x4384, 0x48c8, { 0x85, 0x47, 0x07, 0x4c, 0x46, 0xa2, 0xc5, 0x9d } };
#define FACE_UNLOCK_PIPE_NAME L"\\\\.\\pipe\\FaceUnlockPipe"
enum FACE_CREDENTIAL_FIELD_ID
{
    FCFI_TILEIMAGE = 0,
    FCFI_TITLE = 1,
    FCFI_SUBTITLE = 2,
    FCFI_STATUS = 3,
    FCFI_NUM_FIELDS = 4
};
class CFaceCredential;
class CFaceProvider : public ICredentialProvider
{
public:
    IFACEMETHODIMP QueryInterface(REFIID riid, void** ppv);
    IFACEMETHODIMP_(ULONG) AddRef();
    IFACEMETHODIMP_(ULONG) Release();
    IFACEMETHODIMP SetUsageScenario(CREDENTIAL_PROVIDER_USAGE_SCENARIO cpus, DWORD dwFlags);
    IFACEMETHODIMP SetSerialization(const CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* pcpcs);
    IFACEMETHODIMP Advise(ICredentialProviderEvents* pEvents, UINT_PTR upAdviseContext);
    IFACEMETHODIMP UnAdvise();
    IFACEMETHODIMP GetFieldDescriptorCount(DWORD* pdwCount);
    IFACEMETHODIMP GetFieldDescriptorAt(DWORD dwIndex, CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR** ppcpfd);
    IFACEMETHODIMP GetCredentialCount(DWORD* pdwCount, DWORD* pdwDefault, BOOL* pbAutoLogonWithDefault);
    IFACEMETHODIMP GetCredentialAt(DWORD dwIndex, ICredentialProviderCredential** ppcpc);
    CFaceProvider();
    virtual ~CFaceProvider();
    void NotifyCredentialsChanged();
private:
    long _cRef;
    CREDENTIAL_PROVIDER_USAGE_SCENARIO _cpus;
    ICredentialProviderEvents* _pEvents;
    UINT_PTR _upAdviseContext;
    CFaceCredential* _pCredential;
};
class CFaceCredential : public ICredentialProviderCredential2
{
public:
    IFACEMETHODIMP QueryInterface(REFIID riid, void** ppv);
    IFACEMETHODIMP_(ULONG) AddRef();
    IFACEMETHODIMP_(ULONG) Release();
    IFACEMETHODIMP Advise(ICredentialProviderCredentialEvents* pEvents);
    IFACEMETHODIMP UnAdvise();
    IFACEMETHODIMP SetSelected(BOOL* pbAutoLogon);
    IFACEMETHODIMP SetDeselected();
    IFACEMETHODIMP GetFieldState(DWORD dwFieldID, CREDENTIAL_PROVIDER_FIELD_STATE* pcpfs, CREDENTIAL_PROVIDER_FIELD_INTERACTIVE_STATE* pcpfis);
    IFACEMETHODIMP GetStringValue(DWORD dwFieldID, LPWSTR* ppsz);
    IFACEMETHODIMP GetBitmapValue(DWORD dwFieldID, HBITMAP* phbmp);
    IFACEMETHODIMP GetCheckboxValue(DWORD dwFieldID, BOOL* pbChecked, LPWSTR* ppszLabel);
    IFACEMETHODIMP GetSubmitButtonValue(DWORD dwFieldID, DWORD* pdwAdjacentTo);
    IFACEMETHODIMP GetComboBoxValueCount(DWORD dwFieldID, DWORD* pcItems, DWORD* pdwSelectedItem);
    IFACEMETHODIMP GetComboBoxValueAt(DWORD dwFieldID, DWORD dwItem, LPWSTR* ppszItem);
    IFACEMETHODIMP SetStringValue(DWORD dwFieldID, LPCWSTR psz);
    IFACEMETHODIMP SetCheckboxValue(DWORD dwFieldID, BOOL bChecked);
    IFACEMETHODIMP SetComboBoxSelectedValue(DWORD dwFieldID, DWORD dwSelectedItem);
    IFACEMETHODIMP CommandLinkClicked(DWORD dwFieldID);
    IFACEMETHODIMP GetSerialization(CREDENTIAL_PROVIDER_GET_SERIALIZATION_RESPONSE* pcpgsr, CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* pcpcs, LPWSTR* ppszOptionalStatusText, CREDENTIAL_PROVIDER_STATUS_ICON* pcpsiOptionalStatusIcon);
    IFACEMETHODIMP ReportResult(NTSTATUS ntsStatus, NTSTATUS ntsSubstatus, LPWSTR* ppszOptionalStatusText, CREDENTIAL_PROVIDER_STATUS_ICON* pcpsiOptionalStatusIcon);
    IFACEMETHODIMP GetUserSid(LPWSTR* ppszSid);
    CFaceCredential(CFaceProvider* pProvider);
    virtual ~CFaceCredential();
    void TriggerFaceMatchSuccess(const WCHAR* username, const WCHAR* domain, const WCHAR* password);
    void UpdateStatus(const WCHAR* statusText);
    BOOL IsMatchSucceeded() const { return _bMatchSucceeded; }
private:
    long _cRef;
    CFaceProvider* _pProvider;
    ICredentialProviderCredentialEvents* _pEvents;
    BOOL _bSelected;
    BOOL _bMatchSucceeded;
    WCHAR _szStatus[256];
    WCHAR _szUsername[256];
    WCHAR _szDomain[256];
    WCHAR _szPassword[256];
    HANDLE _hWorkerThread;
    HANDLE _hStopEvent;
    DWORD _dwHelperPID;
    static DWORD WINAPI _PipeListenerThread(LPVOID lpParam);
    void _RunPipeSession();
};
