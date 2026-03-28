*** Settings ***
Library    Browser
Library    OperatingSystem
Library    Collections

*** Variables ***
${START_URL}       ${EMPTY}
${FALLBACK_URL}    ${EMPTY}
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

*** Tasks ***
Resolve_Course_Page
    [Documentation]    Meghatarozza a tenyleges kurzusoldalt.
    ...                Bejelentkezik ha szukseges, majd menti az URL-t es HTML-t.
    New Browser    chromium    headless=false
    New Context    viewport={'width': 1920, 'height': 1080}
    New Page    ${START_URL}
    Wait For Load State    networkidle    timeout=15s
    Sleep    2s

    ${current_url}=    Get Url
    ${needs_login}=    Evaluate    'bejelentkezes' in '''${current_url}''' or 'login' in '''${current_url}'''

    IF    ${needs_login}
        Accept Cookie Popup If Present
        Fill Text    css=input#UserEmail    ${CUBIX_EMAIL}
        Fill Text    css=input#UserPassword    ${CUBIX_PASSWORD}
        Check Checkbox    css=input#UserLogedMeIn
        Click    css=input#loginBtn
        Wait For Load State    networkidle    timeout=30s
        Sleep    3s
        # Navigalas a kurzusoldalra
        Go To    ${START_URL}
        Wait For Load State    networkidle    timeout=15s
        Sleep    2s
        ${current_url}=    Get Url
    END

    ${title}=    Get Title

    # Ellenorzes: a kurzusoldal betoltodott-e (chapter szekciok letezenek)
    ${has_chapters}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=li.thematic-open.title-container    visible    timeout=10s

    IF    not ${has_chapters}
        Log    Nincs chapter szekciok, fallback URL probalkozas...
        Go To    ${FALLBACK_URL}
        Wait For Load State    networkidle    timeout=15s
        Sleep    2s
        ${current_url}=    Get Url
        ${title}=    Get Title
    END

    # Oldal HTML mentese
    ${html}=    Get Page Source
    Create Directory    ${OUTPUT_DIR}${/}metadata
    Create File    ${OUTPUT_DIR}${/}metadata${/}course_page.html    ${html}    encoding=utf-8

    # Eredmeny mentese JSON-kent
    ${result}=    Create Dictionary    course_url=${current_url}    title=${title}
    ${json_str}=    Evaluate    json.dumps($result, ensure_ascii=False, indent=2)
    Create File    ${OUTPUT_DIR}${/}metadata${/}resolved_url.json    ${json_str}    encoding=utf-8

    Close Browser
