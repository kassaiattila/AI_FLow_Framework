() => {
    const movieDiv = document.querySelector('div#movie');
    const videoEl = document.querySelector('div#movie video');
    if (!movieDiv) return { found: false, error: 'No div#movie found' };

    const src = videoEl ? (videoEl.src || videoEl.currentSrc || '') : '';
    const durationEl = document.querySelector('.jw-text-duration');
    const durationText = durationEl ? durationEl.textContent.trim() : '';

    // Parse duration text (MM:SS or HH:MM:SS) to seconds
    let durationSeconds = 0;
    if (durationText) {
        const parts = durationText.split(':').map(Number);
        if (parts.length === 3) {
            durationSeconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
        } else if (parts.length === 2) {
            durationSeconds = parts[0] * 60 + parts[1];
        }
    }

    // Also try to get duration from video element
    if (!durationSeconds && videoEl && videoEl.duration && isFinite(videoEl.duration)) {
        durationSeconds = Math.ceil(videoEl.duration);
    }

    const stateMatch = movieDiv.className.match(/jw-state-(\w+)/);
    const state = stateMatch ? stateMatch[1] : 'unknown';

    return {
        found: true,
        video_src: src,
        duration_text: durationText,
        duration_seconds: durationSeconds,
        state: state,
        has_video_element: !!videoEl,
        movie_classes: movieDiv.className
    };
}
