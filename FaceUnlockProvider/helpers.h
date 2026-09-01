#pragma once
#include <windows.h>
#include <credentialprovider.h>
#include <wincred.h>
HRESULT CreateKerberosLogonSerialization(
    const WCHAR* domain,
    const WCHAR* username,
    const WCHAR* password,
    CREDENTIAL_PROVIDER_CREDENTIAL_SERIALIZATION* pcpcs
);
HRESULT DecryptDPAPIPassword(
    const BYTE* pEncryptedData,
    DWORD cbEncryptedData,
    WCHAR* pszOutPassword,
    DWORD cchOutMax
);
void SecureClearString(WCHAR* psz);
