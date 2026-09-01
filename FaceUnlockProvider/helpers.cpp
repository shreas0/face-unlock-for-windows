#include "helpers.h"
#include <wincrypt.h>
#include <ntsecapi.h>
#include <strsafe.h>
#pragma comment(lib, "Secur32.lib")
#pragma comment(lib, "Crypt32.lib")
#pragma comment(lib, "Credui.lib")
#define NEGOSSP_NAME_A "Negotiate"
#define MICROSOFT_KERBEROS_NAME_A "Kerberos"
void SecureClearString(WCHAR* psz)
{
    if (psz)
    {
        SecureZeroMemory(psz, wcslen(psz) * sizeof(WCHAR));
    }
}
HRESULT CreateKerberosLogonSerialization(
    const WCHAR* domain,
    const WCHAR* username,
    const WCHAR* password,
    CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* pcpcs
)
{
    if (!pcpcs || !username || !password)
    {
        return E_INVALIDARG;
    }
    ZeroMemory(pcpcs, sizeof(*pcpcs));
    WCHAR szFullUser[512] = { 0 };
    if (domain && wcslen(domain) > 0)
    {
        StringCchPrintfW(szFullUser, ARRAYSIZE(szFullUser), L"%s\\%s", domain, username);
    }
    else
    {
        StringCchCopyW(szFullUser, ARRAYSIZE(szFullUser), username);
    }
    DWORD cbPacked = 0;
    CredPackAuthenticationBufferW(0, szFullUser, (LPWSTR)password, NULL, &cbPacked);
    if (cbPacked == 0)
    {
        CredPackAuthenticationBufferW(0, (LPWSTR)username, (LPWSTR)password, NULL, &cbPacked);
    }
    if (cbPacked == 0)
    {
        return HRESULT_FROM_WIN32(GetLastError());
    }
    BYTE* pBuffer = (BYTE*)CoTaskMemAlloc(cbPacked);
    if (!pBuffer)
    {
        return E_OUTOFMEMORY;
    }
    ZeroMemory(pBuffer, cbPacked);
    BOOL bPacked = CredPackAuthenticationBufferW(0, szFullUser, (LPWSTR)password, pBuffer, &cbPacked);
    if (!bPacked)
    {
        bPacked = CredPackAuthenticationBufferW(0, (LPWSTR)username, (LPWSTR)password, pBuffer, &cbPacked);
    }
    if (!bPacked)
    {
        CoTaskMemFree(pBuffer);
        return HRESULT_FROM_WIN32(GetLastError());
    }
    HANDLE hLsa;
    NTSTATUS status = LsaConnectUntrusted(&hLsa);
    if (status != 0)
    {
        CoTaskMemFree(pBuffer);
        return HRESULT_FROM_NT(status);
    }
    auto LocalProviderLog = [](const char* fmt, ...){
        FILE* f = NULL;
        _wfopen_s(&f, L"C:\\ProgramData\\FaceUnlock_Provider.log", L"a, ccs=UTF-8");
        if (!f) return;
        SYSTEMTIME st; GetLocalTime(&st);
        fwprintf(f, L"[%02d:%02d:%02d.%03d] ", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);
        va_list args; va_start(args, fmt);
        char buf[1024]; vsnprintf_s(buf, sizeof(buf), _TRUNCATE, fmt, args); va_end(args);
        wchar_t wbuf[1024]; MultiByteToWideChar(CP_UTF8, 0, buf, -1, wbuf, ARRAYSIZE(wbuf));
        fwprintf(f, L"%s\n", wbuf);
        fclose(f);
    };
    LSA_STRING pkgName;
    pkgName.Buffer = (PCHAR)NEGOSSP_NAME_A;
    pkgName.Length = (USHORT)strlen(pkgName.Buffer);
    pkgName.MaximumLength = pkgName.Length + 1;
    ULONG authPackageId = 0;
    status = LsaLookupAuthenticationPackage(hLsa, &pkgName, &authPackageId);
    if (status != 0)
    {
        LocalProviderLog("LsaLookupAuthenticationPackage(Negotiate) failed: 0x%08X", status);
        pkgName.Buffer = (PCHAR)MICROSOFT_KERBEROS_NAME_A;
        pkgName.Length = (USHORT)strlen(pkgName.Buffer);
        pkgName.MaximumLength = pkgName.Length + 1;
        status = LsaLookupAuthenticationPackage(hLsa, &pkgName, &authPackageId);
    }
    if (status != 0)
    {
        LocalProviderLog("LsaLookupAuthenticationPackage(Kerberos) also failed: 0x%08X", status);
        LsaClose(hLsa);
        CoTaskMemFree(pBuffer);
        return HRESULT_FROM_NT(status);
    }
    LocalProviderLog("LsaLookupAuthenticationPackage succeeded: authPackageId=%u", authPackageId);
    LsaClose(hLsa);
    pcpcs->ulAuthenticationPackage = authPackageId;
    pcpcs->cbSerialization = cbPacked;
    pcpcs->rgbSerialization = pBuffer;
    {
        const int preview = (int)min(12, (int)cbPacked);
        char previewBuf[64] = {0};
        for (int i = 0; i < preview; ++i)
        {
            char byteHex[4];
            sprintf_s(byteHex, sizeof(byteHex), "%02x", pBuffer[i]);
            strcat_s(previewBuf, sizeof(previewBuf), byteHex);
        }
        LocalProviderLog("Serialization cb=%u preview=%s", (unsigned)cbPacked, previewBuf);
    }
    return S_OK;
}
HRESULT DecryptDPAPIPassword(
    const BYTE* pEncryptedData,
    DWORD cbEncryptedData,
    WCHAR* pszOutPassword,
    DWORD cchOutMax
)
{
    if (!pEncryptedData || cbEncryptedData == 0 || !pszOutPassword || cchOutMax == 0)
    {
        return E_INVALIDARG;
    }
    DATA_BLOB inBlob;
    inBlob.cbData = cbEncryptedData;
    inBlob.pbData = (BYTE*)pEncryptedData;
    DATA_BLOB outBlob;
    ZeroMemory(&outBlob, sizeof(outBlob));
    if (!CryptUnprotectData(&inBlob, NULL, NULL, NULL, NULL, CRYPTPROTECT_LOCAL_MACHINE | CRYPTPROTECT_UI_FORBIDDEN, &outBlob))
    {
        return HRESULT_FROM_WIN32(GetLastError());
    }
    int cchConverted = MultiByteToWideChar(CP_UTF8, 0, (LPCCH)outBlob.pbData, outBlob.cbData, pszOutPassword, cchOutMax - 1);
    if (cchConverted > 0)
    {
        pszOutPassword[cchConverted] = L'\0';
    }
    else
    {
        pszOutPassword[0] = L'\0';
    }
    SecureZeroMemory(outBlob.pbData, outBlob.cbData);
    LocalFree(outBlob.pbData);
    return (cchConverted > 0) ? S_OK : E_FAIL;
}
