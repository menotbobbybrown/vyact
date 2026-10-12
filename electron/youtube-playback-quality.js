// Runs inside YouTube embed frames, leaving the iframe and fullscreen owner intact.
function installYouTubeDefaultQuality() {
    if (window.__vyactDefaultQualityInstalled) return;
    window.__vyactDefaultQualityInstalled = true;
    const heights = {tiny: 144, small: 240, medium: 360, large: 480, hd720: 720, hd1080: 1080, hd1440: 1440, hd2160: 2160, highres: 4320};
    let observedPlayer = null;
    let appliedVideo = '';
    let appliedQuality = '';
    let applying = false;
    function applyDefault() {
        if (applying) return;
        const player = document.getElementById('movie_player');
        if (!player || typeof player.getAvailableQualityLevels !== 'function' || typeof player.setPlaybackQualityRange !== 'function') return;
        if (observedPlayer !== player) {
            observedPlayer?.removeEventListener?.('onStateChange', applyDefault);
            observedPlayer = player;
            appliedVideo = '';
            appliedQuality = '';
            player.addEventListener?.('onStateChange', applyDefault);
        }
        if (player.classList.contains('ad-showing')) return;
        try {
            const videoId = player.getVideoData?.()?.video_id;
            if (!videoId) return;
            const levels = (player.getAvailableQualityLevels() || []).filter(level => heights[level]).sort((a, b) => heights[b] - heights[a]);
            const quality = levels.find(level => heights[level] <= 1080) || levels.at(-1);
            if (!quality || (appliedVideo === videoId && appliedQuality === quality)) return;
            applying = true;
            player.setPlaybackQualityRange(quality, quality);
            if (player.getPlaybackQuality?.() !== quality) player.setPlaybackQuality?.(quality);
            appliedVideo = videoId;
            appliedQuality = quality;
        } catch {
            // The next playback event retries a player that is still initializing.
        } finally {
            applying = false;
        }
    }
    document.addEventListener('loadedmetadata', applyDefault, true);
    document.addEventListener('playing', applyDefault, true);
    document.addEventListener('yt-navigate-finish', applyDefault);
    applyDefault();
    // Frame-load can precede creation of the website player; no polling is needed.
    if (!observedPlayer) {
        const observer = new MutationObserver(() => {
            applyDefault();
            if (observedPlayer) observer.disconnect();
        });
        observer.observe(document, {childList: true, subtree: true});
        window.addEventListener('pagehide', () => observer.disconnect(), {once: true});
    }
}

function isYouTubeEmbed(rawUrl) {
    try {
        const url = new URL(rawUrl);
        return url.protocol === 'https:' && ['www.youtube.com', 'www.youtube-nocookie.com'].includes(url.hostname)
            && /^\/embed\/[A-Za-z0-9_-]{11}$/.test(url.pathname);
    } catch {
        return false;
    }
}

function attachYouTubeDefaultQuality(webContents, webFrameMain, onError = () => {}) {
    webContents.on('did-frame-finish-load', (_event, isMainFrame, processId, routingId) => {
        if (isMainFrame) return;
        const frame = webFrameMain.fromId(processId, routingId);
        if (!frame || !isYouTubeEmbed(frame.url)) return;
        frame.executeJavaScript(`(${installYouTubeDefaultQuality.toString()})()`).catch(onError);
    });
}
module.exports = {attachYouTubeDefaultQuality, installYouTubeDefaultQuality, isYouTubeEmbed};
