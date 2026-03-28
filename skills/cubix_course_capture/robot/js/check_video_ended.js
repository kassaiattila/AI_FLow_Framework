() => {
    const movieDiv = document.querySelector('div#movie');
    if (!movieDiv) return { ended: false, error: 'No player' };

    const isComplete = movieDiv.className.includes('jw-state-complete');
    const isPaused = movieDiv.className.includes('jw-state-paused');
    const isIdle = movieDiv.className.includes('jw-state-idle');
    const isPlaying = movieDiv.className.includes('jw-state-playing');

    const elapsed = document.querySelector('.jw-text-elapsed');
    const duration = document.querySelector('.jw-text-duration');

    return {
        ended: isComplete,
        paused: isPaused,
        idle: isIdle,
        playing: isPlaying,
        elapsed: elapsed ? elapsed.textContent.trim() : '',
        duration: duration ? duration.textContent.trim() : '',
        state: movieDiv.className.match(/jw-state-(\w+)/)?.[1] || 'unknown'
    };
}
