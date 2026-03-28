() => {
    const chapters = [];
    const chapterHeaders = document.querySelectorAll('li.thematic-open.title-container');
    chapterHeaders.forEach((header, idx) => {
        const numEl = header.querySelector('div.chapter-number');
        const nameEl = header.querySelector('div.chapter-name');
        const chNum = numEl ? numEl.textContent.trim() : String(idx);
        const chName = nameEl ? nameEl.textContent.trim() : 'Chapter ' + idx;
        const containerId = 'chapter' + idx + 'Container';
        const container = document.getElementById(containerId);
        const lessons = [];
        if (container) {
            const lessonLinks = container.querySelectorAll('a.lesson');
            lessonLinks.forEach((a, lIdx) => {
                const href = a.getAttribute('href') || '';
                const text = (a.innerText || '').replace(/\s+/g, ' ').trim();
                const durationMatch = text.match(/\((\d{1,2}:\d{2}(?::\d{2})?)\)/);
                const hasVideo = !!durationMatch;
                const duration = durationMatch ? durationMatch[1] : '';
                const lessonIdMatch = href.match(/\/lecke\/(\d+)\//);
                const lessonId = lessonIdMatch ? lessonIdMatch[1] : '';
                const titleClean = text
                    .replace(/^\d+\.\s*lecke\s*/, '')
                    .replace(/\([^)]*\)\s*/g, '')
                    .replace(/\[.*?\]\s*/g, '')
                    .trim();
                const slug = titleClean.toLowerCase()
                    .replace(/[^\w\s-]/g, '')
                    .replace(/[\s-]+/g, '_')
                    .substring(0, 30)
                    .replace(/_+$/, '');
                lessons.push({
                    index: lIdx + 1,
                    title: text,
                    url: href,
                    lesson_id: lessonId,
                    has_video: hasVideo,
                    duration: duration,
                    slug: slug || ('lesson_' + (lIdx + 1)),
                    video_url: href
                });
            });
        }
        chapters.push({
            index: idx,
            number: chNum,
            title: chName,
            lesson_count: lessons.length,
            lessons: lessons
        });
    });
    return { weeks: chapters };
}
