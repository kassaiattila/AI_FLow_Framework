"""CubixEDU platform configuration with exact selectors from pilot."""

from __future__ import annotations

from skills.cubix_course_capture.platforms.base import PlatformConfig, SelectorSet

__all__ = ["CUBIXEDU_CONFIG"]

CUBIXEDU_CONFIG = PlatformConfig(
    name="cubixedu",
    display_name="Cubix EDU",
    base_url="https://cubixedu.com",
    login_url="https://cubixedu.com/bejelentkezes",
    cookie_consent=SelectorSet(
        selectors={
            "accept_button": ".cky-consent-container .cky-btn-accept",
        }
    ),
    login=SelectorSet(
        selectors={
            "email_field": "input#UserEmail",
            "password_field": "input#UserPassword",
            "remember_me": "input#UserLogedMeIn",
            "login_button": "input#loginBtn",
        }
    ),
    structure=SelectorSet(
        selectors={
            "chapter_container": "li.thematic-open.title-container",
            "chapter_number": "div.chapter-number",
            "chapter_name": "div.chapter-name",
            "lesson_link": "a.lesson",
        }
    ),
    video=SelectorSet(
        selectors={
            "player_container": "div#movie.jwplayer",
            "play_button": "div#movie .jw-icon-display",
            "fullscreen_button": "div#movie .jw-icon-fullscreen",
            "video_element": "video",
            "duration_text": ".jw-text-duration",
        }
    ),
    scan_structure_js="""
() => {
    const weeks = [];
    const chapters = document.querySelectorAll('li.thematic-open.title-container');

    chapters.forEach((chapter, chapterIdx) => {
        const numberEl = chapter.querySelector('div.chapter-number');
        const nameEl = chapter.querySelector('div.chapter-name');
        const chapterNumber = numberEl ? numberEl.textContent.trim() : '';
        const chapterName = nameEl ? nameEl.textContent.trim() : '';

        // Find the lesson container that follows this chapter header
        const container = chapter.closest('li[id]');
        const containerId = container ? container.id : '';
        const lessonContainer = containerId
            ? document.querySelector('#' + CSS.escape(containerId) + ' + li, #' + CSS.escape(containerId) + ' ul')
            : chapter.parentElement;

        const lessonLinks = lessonContainer
            ? lessonContainer.querySelectorAll('a.lesson')
            : [];

        const lessons = [];
        lessonLinks.forEach((link, lessonIdx) => {
            const titleEl = link.querySelector('.lesson-title') || link;
            const title = titleEl.textContent.trim();
            const url = link.href || '';
            const slug = url.split('/').filter(Boolean).pop() || '';
            const hasVideo = !!link.querySelector('.icon-video, .fa-video, .lesson-video');
            const durationEl = link.querySelector('.lesson-duration, .duration');
            const duration = durationEl ? durationEl.textContent.trim() : '';

            lessons.push({
                index: lessonIdx,
                title: title,
                url: url,
                slug: slug,
                has_video: hasVideo,
                has_download: !!link.querySelector('.icon-download, .fa-download'),
                duration: duration,
                duration_seconds: 0,
                lesson_id: link.dataset.lessonId || '',
                video_url: '',
                downloadable_materials: []
            });
        });

        weeks.push({
            index: chapterIdx,
            title: chapterName,
            number: chapterNumber,
            lesson_count: lessons.length,
            lessons: lessons
        });
    });

    return JSON.stringify(weeks);
}
""",
    get_video_info_js="""
() => {
    const player = document.querySelector('div#movie.jwplayer');
    if (!player) return JSON.stringify({has_video: false});

    const video = player.querySelector('video');
    const durationEl = document.querySelector('.jw-text-duration');
    const sourceEl = video ? video.querySelector('source') : null;

    return JSON.stringify({
        has_video: !!video,
        video_src: sourceEl ? sourceEl.src : (video ? video.src : ''),
        duration_text: durationEl ? durationEl.textContent.trim() : '',
        duration_seconds: video ? (video.duration || 0) : 0,
        player_id: player.id || 'movie',
        ready: video ? (video.readyState >= 2) : false
    });
}
""",
)
