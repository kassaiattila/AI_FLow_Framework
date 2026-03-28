*** Settings ***
Library    Browser
Library    OperatingSystem

*** Variables ***
${VIDEO_URL}       ${EMPTY}
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
Open_Video_Lesson
    [Documentation]    Megnyitja a videolecket bongeszobe.
    ...                A Cubix EDU JWPlayer-t hasznal (div#movie).
    ...                A bongeszoet NEM zarja be - az operator rogzit rola.
    New Browser    chromium    headless=false
    New Context    viewport={'width': 1920, 'height': 1080}
    Cubix Login

    # Leckeoldal megnyitasa
    Go To    https://cubixedu.com${VIDEO_URL}
    Wait For Load State    networkidle    timeout=15s
    Sleep    3s

    # JWPlayer video container (div#movie) keresese
    ${has_jwplayer}=    Run Keyword And Return Status
    ...    Wait For Elements State    css=div#movie.jwplayer    visible    timeout=15s

    IF    ${has_jwplayer}
        # Scroll a video containerhez
        Scroll To Element    css=div#movie
        Sleep    1s

        # Video lejatszas inditasa: kattintas a JW play gombra
        ${play_btn}=    Run Keyword And Return Status
        ...    Wait For Elements State    css=div#movie .jw-icon-display    visible    timeout=5s
        IF    ${play_btn}
            Click    css=div#movie .jw-icon-display
            Log    JWPlayer video elinditva.
            Sleep    2s
        END

        # Fullscreen mod
        ${fs_btn}=    Run Keyword And Return Status
        ...    Wait For Elements State    css=div#movie .jw-icon-fullscreen    visible    timeout=3s
        IF    ${fs_btn}
            Click    css=div#movie .jw-icon-fullscreen
            Log    Fullscreen mod bekapcsolva.
            Sleep    1s
        END
    ELSE
        # Fallback: nativ video tag
        ${has_video}=    Run Keyword And Return Status
        ...    Wait For Elements State    css=video    visible    timeout=5s
        IF    ${has_video}
            Scroll To Element    css=video
            Log    Nativ video elem megtalalva.
        ELSE
            Log    FIGYELEM: Video elem nem talalhato az oldalon!    level=WARN
        END
    END

    # FONTOS: Close Browser NEM hivodik - a bongeszo nyitva marad a rogziteshez
