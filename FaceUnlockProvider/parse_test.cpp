#include <cstdio>
#include <cstring>
#include <string>
#include <iostream>
void parse_payload(char* pPayload) {
    printf("Raw payload: [%s]\n", pPayload);
    char* pUserTok = NULL;
    char* pDomTok = NULL;
    char* pHexTok = NULL;
    char* sep1 = strchr(pPayload, '|');
    if (sep1) {
        *sep1 = '\0';
        pUserTok = pPayload;
        char* rest = sep1 + 1;
        char* sep2 = strchr(rest, '|');
        if (sep2) {
            *sep2 = '\0';
            pDomTok = rest;
            pHexTok = sep2 + 1;
        }
    }
    printf("Parsed: user=%s, domain=%s, hex=%s\n", pUserTok ? pUserTok : "<NULL>", pDomTok ? pDomTok : "<NULL>", pHexTok ? pHexTok : "<NULL>");
}
int main() {
    std::string input = "shres|LOQ|01000000d08c9ddf0115d1118c7a00c04fc297eb0100000063e0e2bd2f0af4448def67947d8e7976040000002a000000460061006300650055006e006c006f0063006b00430072006500640065006e007400690061006c000000106600000001000020000000c2f4e34d8ac64bb49d752ca6c98a3f27a862e66c2dd547e49ae0abc6bc9b7f06000000000e800000000200002000000013395bb5c66826c4a5b3a9a4eb8caac92c7a4c920e666c728d82c143ba642da610000000850b00c4454191afa5cea00cfe23ed19400000009be2ac6925ff13073e0e1d9bb92df93a328b675378b083e161fb75d9530c4e927ad4197542469a6870a826636ca16ee0314fc0834ba2ad05270e3af4333098bb";
    char* buf = strdup(input.c_str());
    parse_payload(buf);
    free(buf);
    return 0;
}
