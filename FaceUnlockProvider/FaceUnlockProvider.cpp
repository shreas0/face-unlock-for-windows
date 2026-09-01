#include "FaceUnlockProvider.h"
static long g_cRef = 0;
HINSTANCE g_hInst = NULL;
CFaceProvider::CFaceProvider() :
    _cRef(1),
    _cpus(CPUS_INVALID),
    _pEvents(NULL),
    _upAdviseContext(0),
    _pCredential(NULL)
{
    InterlockedIncrement(&g_cRef);
}
CFaceProvider::~CFaceProvider()
{
    if (_pCredential)
    {
        _pCredential->Release();
    }
    if (_pEvents)
    {
        _pEvents->Release();
    }
    InterlockedDecrement(&g_cRef);
}
void CFaceProvider::NotifyCredentialsChanged()
{
    if (_pEvents)
    {
        _pEvents->CredentialsChanged(_upAdviseContext);
    }
}
IFACEMETHODIMP CFaceProvider::QueryInterface(REFIID riid, void** ppv)
{
    static const QITAB qit[] = {
        QITABENT(CFaceProvider, ICredentialProvider),
        { 0 },
    };
    return QISearch(this, qit, riid, ppv);
}
IFACEMETHODIMP_(ULONG) CFaceProvider::AddRef()
{
    return InterlockedIncrement(&_cRef);
}
IFACEMETHODIMP_(ULONG) CFaceProvider::Release()
{
    ULONG cRef = InterlockedDecrement(&_cRef);
    if (cRef == 0)
    {
        delete this;
    }
    return cRef;
}
IFACEMETHODIMP CFaceProvider::SetUsageScenario(
    CREDENTIAL_PROVIDER_USAGE_SCENARIO cpus,
    DWORD dwFlags
)
{
    if (cpus == CPUS_LOGON || cpus == CPUS_UNLOCK_WORKSTATION)
    {
        _cpus = cpus;
        return S_OK;
    }
    return E_NOTIMPL;
}
IFACEMETHODIMP CFaceProvider::SetSerialization(const CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* pcpcs)
{
    return E_NOTIMPL;
}
IFACEMETHODIMP CFaceProvider::Advise(ICredentialProviderEvents* pEvents, UINT_PTR upAdviseContext)
{
    if (_pEvents)
    {
        _pEvents->Release();
    }
    _pEvents = pEvents;
    if (_pEvents)
    {
        _pEvents->AddRef();
    }
    _upAdviseContext = upAdviseContext;
    return S_OK;
}
IFACEMETHODIMP CFaceProvider::UnAdvise()
{
    if (_pEvents)
    {
        _pEvents->Release();
        _pEvents = NULL;
    }
    _upAdviseContext = 0;
    return S_OK;
}
IFACEMETHODIMP CFaceProvider::GetFieldDescriptorCount(DWORD* pdwCount)
{
    if (!pdwCount) return E_POINTER;
    *pdwCount = FCFI_NUM_FIELDS;
    return S_OK;
}
IFACEMETHODIMP CFaceProvider::GetFieldDescriptorAt(DWORD dwIndex, CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR** ppcpfd)
{
    if (!ppcpfd || dwIndex >= FCFI_NUM_FIELDS)
    {
        return E_INVALIDARG;
    }
    static const CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR s_rgcpfd[] = {
        { FCFI_TILEIMAGE,     CPFT_TILE_IMAGE,    (LPWSTR)L"Tile Image" },
        { FCFI_TITLE,         CPFT_LARGE_TEXT,    (LPWSTR)L"Face Unlock" },
        { FCFI_SUBTITLE,      CPFT_SMALL_TEXT,    (LPWSTR)L"Subtitle" },
        { FCFI_STATUS,        CPFT_SMALL_TEXT,    (LPWSTR)L"Status" }
    };
    CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR* pcpfd = (CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR*)CoTaskMemAlloc(sizeof(CREDENTIAL_PROVIDER_FIELD_DESCRIPTOR));
    if (!pcpfd)
    {
        return E_OUTOFMEMORY;
    }
    pcpfd->dwFieldID = s_rgcpfd[dwIndex].dwFieldID;
    pcpfd->cpft = s_rgcpfd[dwIndex].cpft;
    SHStrDupW(s_rgcpfd[dwIndex].pszLabel, &pcpfd->pszLabel);
    *ppcpfd = pcpfd;
    return S_OK;
}
IFACEMETHODIMP CFaceProvider::GetCredentialCount(
    DWORD* pdwCount,
    DWORD* pdwDefault,
    BOOL* pbAutoLogonWithDefault
)
{
    if (!pdwCount || !pdwDefault || !pbAutoLogonWithDefault)
    {
        return E_POINTER;
    }
    *pdwCount = 1;
    if (_pCredential && _pCredential->IsMatchSucceeded())
    {
        *pdwDefault = 0;
        *pbAutoLogonWithDefault = TRUE;
    }
    else
    {
        *pdwDefault = CREDENTIAL_PROVIDER_NO_DEFAULT; 
        *pbAutoLogonWithDefault = FALSE;
    }
    return S_OK;
}
IFACEMETHODIMP CFaceProvider::GetCredentialAt(
    DWORD dwIndex,
    ICredentialProviderCredential** ppcpc
)
{
    if (!ppcpc || dwIndex != 0)
    {
        return E_INVALIDARG;
    }
    if (!_pCredential)
    {
        _pCredential = new (std::nothrow) CFaceCredential(this);
    }
    if (_pCredential)
    {
        _pCredential->AddRef();
        *ppcpc = _pCredential;
        return S_OK;
    }
    return E_OUTOFMEMORY;
}
class CClassFactory : public IClassFactory
{
public:
    IFACEMETHODIMP QueryInterface(REFIID riid, void** ppv)
    {
        static const QITAB qit[] = {
            QITABENT(CClassFactory, IClassFactory),
            { 0 },
        };
        return QISearch(this, qit, riid, ppv);
    }
    IFACEMETHODIMP_(ULONG) AddRef() { return InterlockedIncrement(&_cRef); }
    IFACEMETHODIMP_(ULONG) Release()
    {
        ULONG cRef = InterlockedDecrement(&_cRef);
        if (cRef == 0) delete this;
        return cRef;
    }
    IFACEMETHODIMP CreateInstance(IUnknown* pUnkOuter, REFIID riid, void** ppv)
    {
        if (pUnkOuter != NULL) return CLASS_E_NOAGGREGATION;
        CFaceProvider* pProvider = new (std::nothrow) CFaceProvider();
        if (!pProvider) return E_OUTOFMEMORY;
        HRESULT hr = pProvider->QueryInterface(riid, ppv);
        pProvider->Release();
        return hr;
    }
    IFACEMETHODIMP LockServer(BOOL bLock)
    {
        if (bLock) InterlockedIncrement(&g_cRef);
        else InterlockedDecrement(&g_cRef);
        return S_OK;
    }
    CClassFactory() : _cRef(1) {}
private:
    long _cRef;
};
BOOL WINAPI DllMain(HINSTANCE hInst, DWORD dwReason, LPVOID)
{
    if (dwReason == DLL_PROCESS_ATTACH)
    {
        g_hInst = hInst;
        DisableThreadLibraryCalls(hInst);
    }
    return TRUE;
}
STDAPI DllGetClassObject(REFCLSID rclsid, REFIID riid, void** ppv)
{
    if (IsEqualCLSID(rclsid, CLSID_FaceUnlockProvider))
    {
        CClassFactory* pFactory = new (std::nothrow) CClassFactory();
        if (!pFactory) return E_OUTOFMEMORY;
        HRESULT hr = pFactory->QueryInterface(riid, ppv);
        pFactory->Release();
        return hr;
    }
    return CLASS_E_CLASSNOTAVAILABLE;
}
STDAPI DllCanUnloadNow()
{
    return (g_cRef == 0) ? S_OK : S_FALSE;
}
