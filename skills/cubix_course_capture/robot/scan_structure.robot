*** Settings ***
Library    Browser
Library    OperatingSystem
Library    Collections
Library    String

*** Variables ***
${COURSE_URL}      ${EMPTY}
${LOGIN_URL}       https://cubixedu.com/bejelentkezes
${CUBIX_EMAIL}     ${EMPTY}
${CUBIX_PASSWORD}  ${EMPTY}
${OUTPUT_DIR}      output

*** Keywords ***
Accept Cookie Popup If Present
    [Documentation]    CookieYes cookie popup elfogadasa.
    ${banner_visible}=    Run Keyword And Ignore Error
    ...    Wait For Elements State    css=.cky-consent-container .cky-btn-accept    visible    timeout=8s
    IF    '${banner_visible}[0]' == 'PASS'
        Click    css=.cky-consent-container .cky-btn-accept
        Log    Cookie popup elfogadva.
        Sleep    1s
    END

Cubix Login
    [Documentation]    Bejelentkezes.
    New Page    ${LOGIN_URL}
    Wait For Load State    networkidle    timeout=15s
    Sleep    2s
    Accept Cookie Popup If Present
    Fill Text    css=input#UserEmail    ${CUBIX_EMAIL}
    Fill Text    css=input#UserPassword    ${CUBIX_PASSWORD}
    Check Checkbox    css=input#UserLogedMeIn
    Click    css=input#loginBtn
    Wait For Load State    networkidle    timeout=30s
    Sleep    3s

*** Tasks ***
Scan_Weekly_Structure
    [Documentation]    Kurzusoldalon vegigmegy es kinyeri a chapter+lecke strukturat.
    New Browser    chromium    headless=false
    New Context    viewport={'width': 1920, 'height': 1080}
    Cubix Login

    # Kurzusoldal megnyitasa
    Go To    ${COURSE_URL}
    Wait For Load State    networkidle    timeout=15s
    Sleep    3s

    # Varjuk a chapter szekciok megjeleneset
    Wait For Elements State    css=li.thematic-open.title-container >> nth=0    visible    timeout=15s

    # JavaScript fajl beolvasasa es futtatasa
    ${js_path}=    Set Variable    ${CURDIR}${/}js${/}scan_structure.js
    ${js_code}=    Get File    ${js_path}    encoding=utf-8
    ${structure}=    Evaluate Javascript    ${None}    ${js_code}

    # Struktura mentese JSON-be
    ${json_str}=    Evaluate    json.dumps($structure, ensure_ascii=False, indent=2)
    Create Directory    ${OUTPUT_DIR}${/}metadata
    Create File    ${OUTPUT_DIR}${/}metadata${/}course_structure.json    ${json_str}    encoding=utf-8

    Log    Struktura mentve: ${OUTPUT_DIR}/metadata/course_structure.json

    Close Browser
