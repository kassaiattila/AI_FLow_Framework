*** Settings ***
Library    Browser
Library    OperatingSystem

*** Variables ***
${LESSON_URL}      ${EMPTY}
${TARGET_DIR}      ${EMPTY}
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
Save_Lesson_Page
    [Documentation]    Leckeoldal HTML mentese bejelentkezes utan.
    New Browser    chromium    headless=false
    New Context    viewport={'width': 1920, 'height': 1080}
    Cubix Login

    Go To    https://cubixedu.com${LESSON_URL}
    Wait For Load State    networkidle    timeout=15s
    Sleep    2s

    ${html}=    Get Page Source
    Create Directory    ${TARGET_DIR}
    Create File    ${TARGET_DIR}${/}page.html    ${html}    encoding=utf-8

    Close Browser

Download_Lesson_Materials
    [Documentation]    Letoltheto anyagok (PDF, prezentacio, stb.) mentese.
    ...                A Cubix EDU leckeoldalakon a jegyzet szekcioban lehetnek
    ...                letoltheto linkek.
    New Browser    chromium    headless=false
    New Context    viewport={'width': 1920, 'height': 1080}    acceptDownloads=true
    Cubix Login

    Go To    https://cubixedu.com${LESSON_URL}
    Wait For Load State    networkidle    timeout=15s
    Sleep    2s

    Create Directory    ${TARGET_DIR}

    # Letoltheto linkek keresese a lecke tartalom teruleten
    ${download_links}=    Run Keyword And Ignore Error
    ...    Get Elements    css=#lessonContent a[href$='.pdf'], #lessonContent a[href$='.pptx'], #lessonContent a[href$='.ppt'], #lessonContent a[href$='.zip'], #lessonContent a[href$='.docx'], #lessonContent a[download]

    IF    '${download_links}[0]' == 'PASS'
        ${link_count}=    Get Length    ${download_links}[1]
        Log    Letoltheto linkek: ${link_count} db

        FOR    ${link}    IN    @{download_links}[1]
            ${download_promise}=    Promise To Wait For Download
            Click    ${link}
            ${download}=    Wait For    ${download_promise}    timeout=30s
            ${filename}=    Set Variable    ${download}[suggestedFilename]
            Move File    ${download}[saveAs]    ${TARGET_DIR}${/}${filename}
            Log    Letoltve: ${filename} -> ${TARGET_DIR}
        END
    ELSE
        Log    Nincs letoltheto anyag ezen a leckeon.
    END

    Close Browser
