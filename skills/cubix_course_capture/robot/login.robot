*** Settings ***
Library    Browser
Library    OperatingSystem

*** Variables ***
${LOGIN_URL}       https://cubixedu.com/bejelentkezes
${COURSE_URL}      ${EMPTY}
${CUBIX_EMAIL}     ${EMPTY}
${CUBIX_PASSWORD}  ${EMPTY}
${OUTPUT_DIR}      output

*** Keywords ***
Accept Cookie Popup If Present
    [Documentation]    CookieYes cookie popup elfogadasa, ha megjelenik.
    ${banner_visible}=    Run Keyword And Ignore Error
    ...    Wait For Elements State    css=.cky-consent-container .cky-btn-accept    visible    timeout=8s
    IF    '${banner_visible}[0]' == 'PASS'
        Click    css=.cky-consent-container .cky-btn-accept
        Log    Cookie popup elfogadva.
        Sleep    1s
    END

Cubix Login
    [Documentation]    Bejelentkezes a Cubix EDU oldalra.
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
    ${post_url}=    Get Url
    Log    Login OK -> ${post_url}

*** Tasks ***
Login_If_Needed
    [Documentation]    Bejelentkezes a Cubix EDU oldalra es kurzusoldal megnyitasa.
    New Browser    chromium    headless=false
    New Context    viewport={'width': 1920, 'height': 1080}

    # Eloszor megprobaljuk a kurzusoldalt - ha atiranyit loginra, bejelentkezunk
    New Page    ${COURSE_URL}
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
        # Navigalas a kurzusoldalra login utan
        Go To    ${COURSE_URL}
        Wait For Load State    networkidle    timeout=15s
        Sleep    2s
    END

    ${final_url}=    Get Url
    Log    Kurzusoldal: ${final_url}

    # Session storage mentese
    ${storage}=    Save Storage State
    Create File    ${OUTPUT_DIR}${/}metadata${/}auth_state.json    ${storage}    encoding=utf-8

    Close Browser
