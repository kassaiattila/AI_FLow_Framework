() => {
    // Collect ALL video lessons across ALL chapters in strict sequential order
    const allVideoLessons = [];
    const chapterHeaders = document.querySelectorAll('li.thematic-open.title-container');

    chapterHeaders.forEach((header, chIdx) => {
        const numEl = header.querySelector('div.chapter-number');
        const nameEl = header.querySelector('div.chapter-name');
        const chNum = numEl ? numEl.textContent.trim() : String(chIdx);
        const chName = nameEl ? nameEl.textContent.trim() : 'Chapter ' + chIdx;

        const containerId = 'chapter' + chIdx + 'Container';
        const container = document.getElementById(containerId);
        if (!container) return;

        const lessonLinks = container.querySelectorAll('a.lesson');
        lessonLinks.forEach((a, lIdx) => {
            const href = a.getAttribute('href') || '';
            const text = (a.innerText || '').replace(/\s+/g, ' ').trim();
            const durationMatch = text.match(/\((\d{1,2}:\d{2}(?::\d{2})?)\)/);
            const hasVideo = !!durationMatch;

            if (!hasVideo) return; // Skip non-video lessons

            const duration = durationMatch[1];
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

            // Parse duration to seconds
            const parts = duration.split(':').map(Number);
            let durationSeconds = 0;
            if (parts.length === 3) {
                durationSeconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
            } else if (parts.length === 2) {
                durationSeconds = parts[0] * 60 + parts[1];
            }

            allVideoLessons.push({
                global_index: allVideoLessons.length + 1,
                chapter_index: chIdx,
                chapter_number: chNum,
                chapter_name: chName,
                lesson_index: lIdx + 1,
                title: titleClean || ('Lesson ' + (lIdx + 1)),
                full_title: text,
                url: href,
                lesson_id: lessonId,
                duration: duration,
                duration_seconds: durationSeconds,
                slug: slug || ('lesson_' + (lIdx + 1))
            });
        });
    });

    return { total: allVideoLessons.length, lessons: allVideoLessons };
}
