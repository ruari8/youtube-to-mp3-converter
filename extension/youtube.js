(() => {
  if (globalThis.yt2mp3Loaded) return;
  globalThis.yt2mp3Loaded = true;
  let stopPreview = () => {};

  chrome.runtime.onMessage.addListener((message, _sender, reply) => {
    if (message.target !== 'yt2mp3-player') return;
    const video = document.querySelector('video.html5-main-video') || document.querySelector('video');
    const url = new URL(location.href);
    const id = url.pathname === '/watch' ? url.searchParams.get('v') : url.pathname.match(/^\/(?:shorts|live)\/([^/]+)/)?.[1];
    if (!video || !/^[\w-]{11}$/.test(id || '')) {
      reply({ error: 'Open a YouTube video to get started.' });
      return;
    }
    if (document.querySelector('.ad-showing')) {
      reply({ error: 'Wait for the advert to finish, then choose your clip.' });
      return;
    }
    if (!Number.isFinite(video.duration) || video.duration <= 0) {
      reply({ error: 'Wait for the video to load. Live streams cannot be clipped until they finish.' });
      return;
    }
    if (message.action === 'preview') {
      stopPreview();
      if (!(Number.isFinite(message.start) && Number.isFinite(message.end) && 0 <= message.start && message.start < message.end && message.end <= video.duration + 0.1)) {
        reply({ error: 'Choose a valid clip within this video.' });
        return;
      }
      const finish = () => {
        if (video.currentTime >= message.end || location.href !== url.href) {
          video.pause();
          stopPreview();
        }
      };
      const timer = setInterval(finish, 50);
      stopPreview = () => { clearInterval(timer); stopPreview = () => {}; };
      video.currentTime = message.start;
      video.play().then(() => reply({ ok: true }), (error) => {
        stopPreview();
        reply({ error: error.message });
      });
      return true;
    }
    if (message.action === 'stop') {
      stopPreview();
      video.pause();
    }
    reply({
      url: `https://www.youtube.com/watch?v=${id}`, id, duration: video.duration, currentTime: video.currentTime,
      title: document.querySelector('ytd-watch-metadata h1')?.textContent.trim() || document.title.replace(/ - YouTube$/, ''),
    });
  });
})();
