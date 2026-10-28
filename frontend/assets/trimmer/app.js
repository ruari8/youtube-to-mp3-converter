/* Sound cut: browser-owned audio, selection, playback and exports. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const fixedLibrary = document.documentElement.dataset.library === 'fixed';
  const shared = document.documentElement.dataset.shared === 'true';
  const video = $('source-video');
  const minimumCut = 0.02;
  const state = { tracks: [], active: null, buffer: null, peaks: null, start: 0, end: 0,
    cursor: 0, viewStart: 0, viewEnd: 1, context: null, playing: null, playVersion: 0, loadVersion: 0, exporting: false };
  const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
  const time = (n, precise = false) => {
    const rounded = precise ? Math.round(n * 100) / 100 : Math.floor(n);
    return `${Math.floor(rounded / 60)}:${(rounded % 60).toFixed(precise ? 2 : 0).padStart(precise ? 5 : 2, '0')}`;
  };
  const slug = text => text.replace(/\.[a-z0-9]{2,5}$/i, '').replace(/[^a-z0-9_-]+/gi, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'my-sound';
  const storageKey = track => `sound-cut:v1:${track.id}`;
  function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
  function savedCut(track) {
    try { return JSON.parse(localStorage.getItem(storageKey(track))) || null; } catch { return null; }
  }
  function saveCut() {
    if (!state.buffer) return;
    const cut = { start: state.start, end: state.end, filename: $('filename').value };
    state.active.cut = cut;
    try { localStorage.setItem(storageKey(state.active), JSON.stringify(cut)); } catch { /* Private/file browsers may disable storage. */ }
  }
  function audioContext() {
    if (!state.context) state.context = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
    return state.context;
  }
  function renderLibrary() {
    $('track-count').textContent = state.tracks.length;
    $('track-list').replaceChildren(...state.tracks.map((track, index) => {
      const button = document.createElement('button');
      button.className = `track${track === state.active ? ' active' : ''}`;
      button.setAttribute('aria-pressed', String(track === state.active));
      const icon = document.createElement('span'); icon.className = 'track-icon'; icon.textContent = '≋';
      const copy = document.createElement('span'); copy.className = 'track-copy';
      const name = document.createElement('span'); name.className = 'track-name'; name.textContent = track.name;
      const detail = document.createElement('span'); detail.className = 'track-detail';
      detail.textContent = `${track.category || 'Your audio'}${track.duration ? ` · ${time(track.duration)}` : ''}`;
      const number = document.createElement('span'); number.className = 'track-index'; number.textContent = String(index + 1).padStart(2, '0');
      copy.append(name, detail); button.append(icon, copy, number);
      button.addEventListener('click', () => loadTrack(track));
      return button;
    }));
  }
  async function loadTrack(track) {
    if (shared) showTab('editor');
    saveCut(); stop();
    video.pause(); video.removeAttribute('src'); video.load();
    $('video-preview').hidden = !track.videoUrl;
    if (track.videoUrl) { video.src = track.videoUrl; video.load(); }
    const version = ++state.loadVersion;
    state.active = track; state.buffer = null; state.peaks = null;
    $('controls').disabled = true; $('empty-wave').hidden = false;
    $('track-title').textContent = track.name;
    $('track-kind').textContent = track.category || 'YOUR AUDIO';
    $('track-info').textContent = 'Opening the full-length audio…';
    $('track-number').textContent = String(state.tracks.indexOf(track) + 1).padStart(2, '0');
    status('Preparing waveform…'); renderLibrary(); draw();
    try {
      let bytes;
      if (track.file) bytes = await track.file.arrayBuffer();
      else if (track.data) {
        const binary = atob(track.data); const array = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i);
        bytes = array.buffer;
      } else {
        const response = await fetch(track.url);
        if (response.redirected && new URL(response.url).pathname === '/login') { location.href = '/login'; return; }
        if (!response.ok) throw new Error('The source audio is missing. Use Add audio files to open it.');
        bytes = await response.arrayBuffer();
      }
      if (version !== state.loadVersion) return;
      const buffer = await audioContext().decodeAudioData(bytes);
      if (version !== state.loadVersion) return;
      if (buffer.duration < minimumCut) throw new Error('This audio is too short to trim.');
      state.buffer = buffer; track.duration = buffer.duration;
      const data = buffer.getChannelData(0), block = 256;
      state.peaks = new Float32Array(Math.ceil(data.length / block));
      for (let i = 0; i < data.length; i++) state.peaks[Math.floor(i / block)] = Math.max(state.peaks[Math.floor(i / block)], Math.abs(data[i]));
      const cut = track.cut || savedCut(track) || track.presets?.[0] || { start: 0, end: buffer.duration };
      state.start = clamp(Number.isFinite(cut.start) ? cut.start : 0, 0, buffer.duration - minimumCut);
      state.end = clamp(Number.isFinite(cut.end) ? cut.end : buffer.duration, state.start + minimumCut, buffer.duration);
      state.cursor = state.start;
      syncVideo(true);
      $('filename').value = typeof cut.filename === 'string' ? cut.filename : slug(track.name);
      $('controls').disabled = false; $('empty-wave').hidden = true; $('export').disabled = state.exporting;
      $('full-duration').textContent = time(buffer.duration, true);
      $('transport-duration').textContent = time(buffer.duration);
      $('track-info').textContent = `${track.videoUrl ? 'Full MP4 video' : 'Full-length audio'} · ${time(buffer.duration)} · ${buffer.numberOfChannels === 1 ? 'Mono' : 'Stereo'} · Original volume`;
      $('presets').replaceChildren();
      if (track.presets?.length) {
        const label = document.createElement('span'); label.textContent = 'Original cuts:'; $('presets').append(label);
        for (const preset of track.presets) {
          const button = document.createElement('button');
          button.textContent = `${preset.label || 'Requested cut'} · ${time(preset.start)}–${time(preset.end)}`;
          button.addEventListener('click', () => { setSelection(preset.start, preset.end); seek(state.start); fitSelection(); });
          $('presets').append(button);
        }
      }
      fitSelection(); update(); renderLibrary();
      status('Ready. Drag the handles, then play your cut to check the edges.');
    } catch (error) {
      if (version !== state.loadVersion) return;
      status(`Couldn't open this audio. ${error.message || 'Try an MP3 or WAV file.'}`, true);
      $('track-info').textContent = 'Select another track or add a supported audio file.';
    }
  }
  function setSelection(start, end) {
    if (!state.buffer || !Number.isFinite(start) || !Number.isFinite(end)) return;
    stop();
    state.start = clamp(start, 0, state.buffer.duration - minimumCut);
    state.end = clamp(end, state.start + minimumCut, state.buffer.duration);
    update(); saveCut();
  }
  function setBoundary(which, value) {
    if (!state.buffer || !Number.isFinite(value)) { update(); return; }
    if (which === 'start') setSelection(clamp(value, 0, state.end - minimumCut), state.end);
    else setSelection(state.start, clamp(value, state.start + minimumCut, state.buffer.duration));
    seek(state[which]);
    if (state[which] < state.viewStart || state[which] > state.viewEnd) fitSelection();
  }
  function setView(start, width) {
    if (!state.buffer) return;
    width = clamp(width, Math.min(0.25, state.buffer.duration), state.buffer.duration);
    state.viewStart = clamp(start, 0, state.buffer.duration - width);
    state.viewEnd = state.viewStart + width;
    $('pan').max = Math.max(0, state.buffer.duration - width);
    $('pan').value = state.viewStart; $('pan').disabled = width >= state.buffer.duration;
    draw();
  }
  function fitSelection() {
    const length = state.end - state.start;
    const padding = Math.max(1, length * 0.6);
    setView(state.start - padding, length + padding * 2);
  }
  function zoom(factor) {
    const width = (state.viewEnd - state.viewStart) * factor;
    const center = (state.viewEnd + state.viewStart) / 2;
    setView(center - width / 2, width);
  }
  function update() {
    if (!state.buffer) return;
    $('start').value = state.start.toFixed(2); $('end').value = state.end.toFixed(2);
    $('start').max = (state.end - minimumCut).toFixed(4);
    $('end').min = (state.start + minimumCut).toFixed(4); $('end').max = state.buffer.duration;
    $('cut-length').replaceChildren(document.createTextNode((state.end - state.start).toFixed(2)));
    const unit = document.createElement('small'); unit.textContent = 's'; $('cut-length').append(unit);
    $('selection-summary').textContent = `${time(state.start, true)} → ${time(state.end, true)}`;
    $('playhead').textContent = time(state.cursor, true);
    for (const [which, bound, min, max] of [['start', state.start, 0, state.end - minimumCut], ['end', state.end, state.start + minimumCut, state.buffer.duration]]) {
      const handle = $(`${which}-handle`);
      handle.setAttribute('aria-valuenow', bound.toFixed(2));
      handle.setAttribute('aria-valuemin', min.toFixed(2)); handle.setAttribute('aria-valuemax', max.toFixed(2));
      handle.setAttribute('aria-valuetext', `${bound.toFixed(2)} seconds`);
    }
    draw();
  }
  function canvasContext(canvas) {
    const width = canvas.clientWidth, height = canvas.clientHeight, scale = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(width * scale) || canvas.height !== Math.round(height * scale)) {
      canvas.width = Math.round(width * scale); canvas.height = Math.round(height * scale);
    }
    const ctx = canvas.getContext('2d'); ctx.setTransform(scale, 0, 0, scale, 0, 0); ctx.clearRect(0, 0, width, height);
    return { ctx, width, height };
  }
  function paint(canvas, from, to, overview = false) {
    const { ctx, width, height } = canvasContext(canvas);
    if (!state.buffer || !width) return;
    const x = value => (value - from) / (to - from) * width;
    const center = overview ? height / 2 : 87, amplitude = overview ? height * .38 : 59;
    ctx.fillStyle = overview ? '#f3d7bb' : '#f3944921';
    ctx.fillRect(x(state.start), 0, x(state.end) - x(state.start), overview ? height : height - 26);
    ctx.strokeStyle = overview ? '#dae0d3' : '#ffffff0e'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, center); ctx.lineTo(width, center); ctx.stroke();
    const rate = state.buffer.sampleRate / 256;
    for (let pixel = 0; pixel < width; pixel += 3) {
      const at = from + pixel / width * (to - from);
      const first = Math.floor(at * rate), last = Math.ceil((from + (pixel + 3) / width * (to - from)) * rate);
      let peak = 0;
      for (let i = first; i <= Math.min(last, state.peaks.length - 1); i++) peak = Math.max(peak, state.peaks[i] || 0);
      const size = Math.max(1, peak * amplitude);
      ctx.fillStyle = at >= state.start && at <= state.end ? (overview ? '#c45c27' : '#f3ad70') : (overview ? '#8ca185' : '#648577');
      ctx.fillRect(pixel, center - size, 1.6, size * 2);
    }
    if (overview) {
      ctx.strokeStyle = '#466656'; ctx.lineWidth = 1.5;
      ctx.strokeRect(x(state.viewStart) + 1, 1, Math.max(2, x(state.viewEnd) - x(state.viewStart) - 2), height - 2);
    } else {
      ctx.font = '10px ui-monospace, monospace'; ctx.fillStyle = '#9bb0a4';
      for (let i = 0; i <= 5; i++) {
        ctx.textAlign = i === 0 ? 'left' : i === 5 ? 'right' : 'center';
        ctx.fillText(time(from + (to - from) * i / 5, to - from < 20), clamp(width * i / 5, 8, width - 8), height - 9);
      }
    }
    if (state.cursor >= from && state.cursor <= to) {
      ctx.fillStyle = overview ? '#203b32' : '#f8fff3'; ctx.fillRect(x(state.cursor), overview ? 0 : 25, 1.5, overview ? height : height - 52);
    }
  }
  function draw() {
    paint($('waveform'), state.viewStart, state.viewEnd);
    paint($('overview'), 0, state.buffer?.duration || 1, true);
    for (const which of ['start', 'end']) {
      const handle = $(`${which}-handle`), value = state[which];
      handle.hidden = !state.buffer || value < state.viewStart - .001 || value > state.viewEnd + .001;
      handle.style.left = `${(value - state.viewStart) / (state.viewEnd - state.viewStart) * 100}%`;
    }
  }
  function currentCursor() {
    if (!state.playing) return state.cursor;
    const play = state.playing;
    const elapsed = Math.max(0, state.context.currentTime - play.began);
    return play.loop ? play.from + elapsed % (play.to - play.from) : Math.min(play.to, play.from + elapsed);
  }
  function syncVideo(force = false) {
    if (!state.active?.videoUrl || video.readyState < 1) return;
    const at = Math.min(state.cursor, video.duration);
    if (force || Math.abs(video.currentTime - at) > .15) video.currentTime = at;
  }
  video.addEventListener('loadedmetadata', () => syncVideo(true));
  video.addEventListener('click', () => play(false));
  video.addEventListener('error', () => {
    if (state.active?.videoUrl && video.getAttribute('src')) status('Video preview could not load. The audio controls still work. Reload the page if your session has expired.', true);
  });
  function stop() {
    state.playVersion++;
    if (!state.playing) { video.pause(); return; }
    state.cursor = currentCursor();
    const source = state.playing.source; state.playing = null;
    source.onended = null; source.stop(); source.disconnect();
    video.pause(); syncVideo(true);
    $('preview').textContent = '▶ Play cut'; $('play-full').textContent = 'Play from cursor';
    $('playhead').textContent = time(state.cursor, true); draw();
  }
  async function play(selection) {
    if (!state.buffer) return;
    if (state.playing) { stop(); return; }
    const version = state.loadVersion;
    const playVersion = ++state.playVersion;
    try {
      const context = audioContext(); await context.resume();
      if (version !== state.loadVersion || playVersion !== state.playVersion || !state.buffer || state.playing) return;
      document.querySelectorAll('.export-item audio').forEach(audio => audio.pause());
      const from = selection ? state.start : (state.cursor >= state.buffer.duration - .01 ? 0 : state.cursor);
      const to = selection ? state.end : state.buffer.duration;
      const loop = selection && $('loop').checked;
      const source = context.createBufferSource(); source.buffer = state.buffer; source.connect(context.destination);
      source.loop = loop; source.loopStart = from; source.loopEnd = to;
      state.cursor = from; syncVideo(true);
      if (state.active.videoUrl) {
        try { await video.play(); } catch { /* Audio can still preview if the video fails to load. */ }
        if (version !== state.loadVersion || playVersion !== state.playVersion || !state.buffer || state.playing) { source.disconnect(); return; }
      }
      state.playing = { source, from, to, loop, began: context.currentTime };
      source.onended = () => {
        if (state.playing?.source !== source) return;
        state.cursor = to; state.playing = null; source.disconnect();
        video.pause(); syncVideo(true);
        $('preview').textContent = '▶ Play cut'; $('play-full').textContent = 'Play from cursor'; update();
      };
      if (loop) source.start(0, from); else source.start(0, from, to - from);
      $(selection ? 'preview' : 'play-full').textContent = 'Ⅱ Pause';
      function tick() {
        if (state.playing?.source !== source) return;
        state.cursor = currentCursor(); syncVideo(); $('playhead').textContent = time(state.cursor, true); draw(); requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    } catch (error) { stop(); status(`Playback failed: ${error.message}`, true); }
  }
  function seek(position) {
    if (!state.buffer) return;
    stop(); state.cursor = clamp(position, 0, state.buffer.duration); syncVideo(true); update();
  }
  for (const which of ['start', 'end']) {
    const handle = $(`${which}-handle`);
    handle.addEventListener('pointerdown', event => { event.preventDefault(); handle.setPointerCapture(event.pointerId); });
    handle.addEventListener('pointermove', event => {
      if (!handle.hasPointerCapture(event.pointerId)) return;
      const box = $('waveform').getBoundingClientRect();
      const value = state.viewStart + clamp((event.clientX - box.left) / box.width, 0, 1) * (state.viewEnd - state.viewStart);
      setBoundary(which, value);
    });
    handle.addEventListener('pointerup', event => { if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId); });
    handle.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault(); event.stopPropagation();
      setBoundary(which, state[which] + (event.key === 'ArrowLeft' ? -1 : 1) * (event.shiftKey ? .5 : .05));
    });
    $(which).addEventListener('change', () => setBoundary(which, $(which).valueAsNumber));
    $(`set-${which}`).addEventListener('click', () => setBoundary(which, currentCursor()));
  }
  $('waveform').addEventListener('pointerdown', event => {
    const box = event.currentTarget.getBoundingClientRect();
    seek(state.viewStart + (event.clientX - box.left) / box.width * (state.viewEnd - state.viewStart));
  });
  $('overview').addEventListener('pointerdown', event => {
    if (!state.buffer) return;
    const box = event.currentTarget.getBoundingClientRect(), position = (event.clientX - box.left) / box.width * state.buffer.duration;
    const width = state.viewEnd - state.viewStart; seek(position); setView(position - width / 2, width);
  });
  $('pan').addEventListener('input', () => setView(Number($('pan').value), state.viewEnd - state.viewStart));
  $('zoom-in').addEventListener('click', () => zoom(.6)); $('zoom-out').addEventListener('click', () => zoom(1.7));
  $('fit-selection').addEventListener('click', fitSelection);
  $('show-all').addEventListener('click', () => setView(0, state.buffer.duration));
  $('preview').addEventListener('click', () => play(true)); $('play-full').addEventListener('click', () => play(false));
  $('loop').addEventListener('change', stop);
  $('reset').addEventListener('click', () => { setSelection(0, state.buffer.duration); seek(0); fitSelection(); });
  $('filename').addEventListener('input', saveCut);
  document.querySelectorAll('[data-nudge]').forEach(button => button.addEventListener('click', () => {
    const [which, delta] = button.dataset.nudge.split(':'); setBoundary(which, state[which] + Number(delta));
  }));
  document.addEventListener('keydown', event => {
    if (shared && !$('board-panel').hidden) return;
    if (!state.buffer || event.ctrlKey || event.metaKey || event.altKey || /INPUT|SELECT|TEXTAREA|BUTTON|A/.test(document.activeElement.tagName)) return;
    if (event.code === 'Space') { event.preventDefault(); play(true); }
    else if (event.key.toLowerCase() === 'i') setBoundary('start', currentCursor());
    else if (event.key.toLowerCase() === 'o') setBoundary('end', currentCursor());
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); seek(currentCursor() + (event.key === 'ArrowLeft' ? -1 : 1) * (event.shiftKey ? 1 : .1)); }
  });
  async function addFiles(files) {
    if (fixedLibrary) return;
    const added = Array.from(files).filter(file => file.type.startsWith('audio/') || /\.(mp3|wav|m4a|aac|ogg|flac|aiff|opus|webm)$/i.test(file.name)).map(file => ({
      id: `file:${file.name}:${file.size}:${file.lastModified}`, name: file.name.replace(/\.[^.]+$/, ''), file, category: 'Added by you', presets: []
    }));
    if (!added.length) { status('Choose an audio file such as MP3, WAV or M4A.', true); return; }
    state.tracks.push(...added); renderLibrary(); await loadTrack(added[0]);
  }
  $('import').addEventListener('click', () => $('files').click());
  $('files').addEventListener('change', () => { addFiles($('files').files); $('files').value = ''; });
  let dragDepth = 0;
  window.addEventListener('dragenter', event => { if (!fixedLibrary && Array.from(event.dataTransfer.types).includes('Files')) { event.preventDefault(); dragDepth++; $('drop-overlay').hidden = false; } });
  window.addEventListener('dragover', event => { event.preventDefault(); });
  window.addEventListener('dragleave', () => { if (--dragDepth <= 0) { dragDepth = 0; $('drop-overlay').hidden = true; } });
  window.addEventListener('drop', event => { event.preventDefault(); dragDepth = 0; $('drop-overlay').hidden = true; addFiles(event.dataTransfer.files); });
  new ResizeObserver(draw).observe($('timeline'));

  // The encoder is serialized into a worker so long exports never block trimming.
  function encoderWorker() {
    self.onmessage = ({ data }) => {
      try {
        const { channels, sampleRate, format } = data;
        const length = channels[0].length;
        const pcm = channels.map(channel => {
          const result = new Int16Array(channel.length);
          for (let i = 0; i < channel.length; i++) { const n = Math.max(-1, Math.min(1, channel[i])); result[i] = Math.round(n * (n < 0 ? 32768 : 32767)); }
          return result;
        });
        let blob;
        if (format === 'wav') {
          const buffer = new ArrayBuffer(44 + length * channels.length * 2), view = new DataView(buffer);
          const write = (offset, text) => { for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i)); };
          write(0, 'RIFF'); view.setUint32(4, buffer.byteLength - 8, true); write(8, 'WAVE'); write(12, 'fmt ');
          view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, channels.length, true);
          view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * channels.length * 2, true);
          view.setUint16(32, channels.length * 2, true); view.setUint16(34, 16, true); write(36, 'data'); view.setUint32(40, buffer.byteLength - 44, true);
          let offset = 44;
          for (let i = 0; i < length; i++) for (const channel of pcm) { view.setInt16(offset, channel[i], true); offset += 2; }
          blob = new Blob([buffer], { type: 'audio/wav' });
        } else {
          const encoder = new lamejs.Mp3Encoder(channels.length, sampleRate, 320), chunks = [];
          for (let i = 0; i < length; i += 1152) {
            const chunk = encoder.encodeBuffer(pcm[0].subarray(i, i + 1152), pcm[1]?.subarray(i, i + 1152));
            if (chunk.length) chunks.push(chunk);
            if (i % (1152 * 40) === 0) self.postMessage({ progress: i / length });
          }
          const tail = encoder.flush(); if (tail.length) chunks.push(tail);
          blob = new Blob(chunks, { type: 'audio/mpeg' });
        }
        self.postMessage({ blob });
      } catch (error) { self.postMessage({ error: error.message }); }
    };
  }
  async function exportCut() {
    if (!state.buffer || state.exporting) return;
    stop(); saveCut();
    const format = $('format').value, buffer = state.buffer;
    const startSample = Math.round(state.start * buffer.sampleRate), endSample = Math.round(state.end * buffer.sampleRate);
    const seconds = (endSample - startSample) / buffer.sampleRate;
    const filename = `${slug($('filename').value || state.active.name)}_${state.start.toFixed(2)}-${state.end.toFixed(2)}.${format}`;
    const channels = Array.from({ length: Math.min(2, buffer.numberOfChannels) }, (_, i) => buffer.getChannelData(i).slice(startSample, endSample));
    state.exporting = true; $('export').disabled = true; $('export').textContent = 'Preparing…';
    let worker, workerUrl;
    try {
      workerUrl = URL.createObjectURL(new Blob([`${lamejs.toString()}\nlamejs();\n(${encoderWorker.toString()})();`], { type: 'text/javascript' }));
      worker = new Worker(workerUrl);
      const blob = await new Promise((resolve, reject) => {
        worker.onerror = event => reject(new Error(event.message || 'Audio export failed.'));
        worker.onmessage = ({ data }) => {
          if (data.error) reject(new Error(data.error));
          else if (data.blob) resolve(data.blob);
          else $('export').textContent = `Encoding ${Math.round(data.progress * 100)}%`;
        };
        worker.postMessage({ channels, sampleRate: buffer.sampleRate, format }, channels.map(channel => channel.buffer));
      });
      const url = URL.createObjectURL(blob), row = document.createElement('div'); row.className = 'export-item';
      const copy = document.createElement('div'); copy.className = 'export-copy';
      const title = document.createElement('strong'); title.textContent = filename;
      const detail = document.createElement('small'); detail.textContent = `${seconds.toFixed(2)} seconds · ${(blob.size / 1024).toFixed(0)} KB · ${format.toUpperCase()}`;
      copy.append(title, detail);
      const audio = document.createElement('audio'); audio.controls = true; audio.src = url; audio.preload = 'metadata';
      audio.addEventListener('play', () => { stop(); document.querySelectorAll('.export-item audio').forEach(other => { if (other !== audio) other.pause(); }); });
      const link = document.createElement('a'); link.href = url; link.download = filename; link.textContent = 'Download';
      row.append(copy, audio, link); $('export-list').prepend(row); $('exports').hidden = false;
      link.click(); status(`Created ${filename}. Your cut is also available below.`);
    } catch (error) { status(`Couldn't export: ${error.message}`, true); }
    finally { worker?.terminate(); if (workerUrl) URL.revokeObjectURL(workerUrl); state.exporting = false; $('export').disabled = false; $('export').textContent = fixedLibrary ? '↓ Download MP3' : '↓ Download cut'; }
  }
  $('export').addEventListener('click', exportCut);
  // Shared clips are permanent MP3s on the server; playback stays in this browser.
  let board = [], activeTab = 'editor', importing = null, saving = false;
  const padAudio = new Map();
  let importPollTimer = null;
  async function api(path, method = 'GET', body) {
    const response = await fetch(`/api/${path}`, {method, headers: body ? {'Content-Type':'application/json'} : {}, body: body ? JSON.stringify(body) : undefined});
    if (response.status === 401) { location.href = '/login'; throw new Error('Please sign in again.'); }
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || 'Could not complete the request.');
    return value;
  }
  function stopBoard() {
    for (const audio of padAudio.values()) { audio.pause(); audio.currentTime = 0; }
    padAudio.clear();
    $('board-grid').querySelectorAll('.sound-pad').forEach(button => { button.classList.remove('playing'); button.setAttribute('aria-pressed','false'); });
  }
  function showTab(tab) {
    stop(); stopBoard(); activeTab = tab;
    document.body.dataset.tab = tab;
    document.querySelectorAll('.export-item audio').forEach(audio => audio.pause());
    for (const name of ['editor', 'board']) {
      $(`${name}-panel`).hidden = name !== tab;
      $(`tab-${name}`).setAttribute('aria-selected', String(name === tab));
      $(`tab-${name}`).tabIndex = name === tab ? 0 : -1;
    }
    if (tab === 'board') refreshBoard().catch(error => { $('board-status').textContent = error.message; });
    else requestAnimationFrame(draw);
  }
  async function refreshLibrary() {
    const tracks = await api('library');
    state.tracks = tracks.map(track => state.tracks.find(old => old.id === track.id) || track);
    renderLibrary();
  }
  async function refreshBoard() {
    board = await api('board'); renderBoard();
  }
  function renderBoard() {
    $('board-count').textContent = board.length;
    const query = $('board-search').value.toLowerCase().trim();
    const visible = board.filter(clip => `${clip.name} ${clip.sourceName}`.toLowerCase().includes(query));
    $('board-empty').hidden = visible.length > 0;
    $('board-empty').textContent = board.length ? 'No matching sounds. Try another search.' : 'No sounds here yet. Save a cut in the Editor to add one.';
    $('board-grid').replaceChildren(...visible.map((clip, index) => {
      const card = document.createElement('article'); card.className = 'sound-card';
      const pad = document.createElement('button'); pad.className = 'sound-pad'; pad.dataset.clipId = clip.id;
      pad.setAttribute('aria-label', `Play ${clip.name}`); pad.setAttribute('aria-pressed', String(padAudio.has(clip.id)));
      pad.classList.toggle('playing', padAudio.has(clip.id));
      const top = document.createElement('span'); top.className = 'pad-top';
      const icon = document.createElement('span'); icon.className = 'pad-icon'; icon.textContent = '▶';
      const key = document.createElement('kbd'); key.textContent = index < 9 ? index + 1 : '♪'; top.append(icon,key);
      const name = document.createElement('strong'); name.textContent = clip.name;
      const detail = document.createElement('small'); detail.textContent = `${clip.duration.toFixed(2)}s · ${clip.sourceName}`;
      pad.append(top,name,detail); pad.addEventListener('click', () => togglePad(clip));
      const actions = document.createElement('div'); actions.className = 'pad-actions';
      const edit = document.createElement('button'); edit.textContent = 'Edit cut'; edit.setAttribute('aria-label', `Edit ${clip.name}`);
      edit.addEventListener('click', async () => {
        try {
          await refreshLibrary();
          const track = state.tracks.find(t => t.id === clip.trackId);
          if (!track) throw new Error('The original video is unavailable.');
          await loadTrack(track);
          if (state.active !== track || !state.buffer) return;
          setSelection(clip.start,clip.end); $('filename').value = clip.name; saveCut(); seek(state.start); fitSelection();
        } catch (error) { $('board-status').textContent = error.message; }
      });
      const link = document.createElement('a'); link.href = clip.url; link.download = `${slug(clip.name)}.mp3`; link.textContent = '↓ MP3'; link.setAttribute('aria-label', `Download ${clip.name} as MP3`);
      const remove = document.createElement('button'); remove.textContent = '×'; remove.setAttribute('aria-label', `Remove ${clip.name}`);
      remove.addEventListener('click', async () => {
        remove.disabled = true;
        try {
          await api(`board/${clip.id}`, 'DELETE'); stopBoard(); await refreshBoard();
          $('board-status').replaceChildren(document.createTextNode(`Removed “${clip.name}”. `));
          const undo = document.createElement('button'); undo.textContent = 'Undo';
          undo.addEventListener('click', async () => { try { await api(`board/${clip.id}/restore`,'POST'); await refreshBoard(); $('board-status').textContent = 'Sound restored.'; } catch (error) { $('board-status').textContent = error.message; } });
          $('board-status').append(undo);
        } catch (error) { $('board-status').textContent = error.message; remove.disabled = false; }
      });
      actions.append(edit,link,remove); card.append(pad,actions); return card;
    }));
  }
  async function togglePad(clip) {
    if (padAudio.has(clip.id)) { const audio = padAudio.get(clip.id); audio.pause(); padAudio.delete(clip.id); renderBoard(); return; }
    const audio = new Audio(clip.url); audio.volume = Number($('board-volume').value); padAudio.set(clip.id,audio); renderBoard();
    audio.addEventListener('ended', () => { if (padAudio.get(clip.id) === audio) padAudio.delete(clip.id); renderBoard(); });
    try { await audio.play(); }
    catch { if (padAudio.get(clip.id) === audio) padAudio.delete(clip.id); renderBoard(); $('board-status').textContent = 'Could not play this sound. Reload if your sign-in has expired.'; }
  }
  async function pollImports() {
    clearTimeout(importPollTimer);
    try {
      const connection = await api('connection');
      $('import-connection').textContent = connection.requiresMac ? (connection.available ? 'Mac connected · Ready to import from any device.' : 'Mac offline · New imports will wait. Saved sounds still work.') : 'Ready to import.';
      const jobs = await api('imports');
      $('import-jobs').replaceChildren(...jobs.slice(0,3).map(job => {
        const row = document.createElement('div'); row.className = `import-job ${job.status}`;
        row.textContent = job.message;
        if (job.status === 'complete') {
          const open = document.createElement('button'); open.type = 'button'; open.textContent = 'Open video';
          open.addEventListener('click', async () => { try { await refreshLibrary(); await loadTrack(state.tracks.find(t => t.id === job.track_id)); } catch (error) { $('import-status').textContent = error.message; } }); row.append(open);
        }
        return row;
      }));
      const own = jobs.find(job => job.id === importing);
      if (own && ['complete','failed'].includes(own.status)) {
        importing = null;
        $('import-status').textContent = own.status === 'complete' ? 'Video ready. Choose your cut in the Editor.' : 'The import did not finish. Paste the link again to retry.';
        if (own.status === 'complete') { await refreshLibrary(); await loadTrack(state.tracks.find(t => t.id === own.track_id)); }
      }
      importPollTimer = setTimeout(pollImports, jobs.some(job => ['queued','downloading'].includes(job.status)) ? 3000 : 20000);
    } catch (error) { $('import-status').textContent = error.message; }
  }
  if (shared) {
    for (const id of ['app-tabs','youtube-form','save-board-row']) $(id).hidden = false;
    for (const tab of ['editor','board']) {
      $(`tab-${tab}`).addEventListener('click', () => showTab(tab));
      $(`tab-${tab}`).addEventListener('keydown', event => { if (['ArrowLeft','ArrowRight'].includes(event.key)) { event.preventDefault(); const other = tab === 'editor' ? 'board' : 'editor'; showTab(other); $(`tab-${other}`).focus(); } });
    }
    $('board-search').addEventListener('input',renderBoard);
    $('board-stop').addEventListener('click',stopBoard);
    $('board-volume').addEventListener('input', () => { for (const audio of padAudio.values()) audio.volume = Number($('board-volume').value); });
    document.addEventListener('keydown', event => {
      if (activeTab !== 'board') return;
      if (event.key === 'Escape') { event.preventDefault(); stopBoard(); return; }
      if (event.repeat || event.ctrlKey || event.metaKey || event.altKey || /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
      if (/^[1-9]$/.test(event.key)) { const pad = $('board-grid').querySelectorAll('.sound-pad')[Number(event.key)-1]; if (pad) { event.preventDefault(); pad.click(); } }
    });
    $('youtube-form').addEventListener('submit', async event => {
      event.preventDefault(); $('youtube-add').disabled = true; $('import-status').textContent = 'Checking link…';
      try {
        const result = await api('imports','POST',{url:$('youtube-url').value});
        $('youtube-url').value = '';
        if (result.track) { await refreshLibrary(); await loadTrack(state.tracks.find(t => t.id === result.track.id)); $('import-status').textContent = 'This video is already in your library. Opened it for you.'; }
        else { importing = result.job.id; $('import-status').textContent = 'You can keep editing while the video downloads.'; pollImports(); }
      } catch (error) { $('import-status').textContent = error.message; }
      finally { $('youtube-add').disabled = false; }
    });
    $('save-board').addEventListener('click', async () => {
      if (saving || !state.buffer) return;
      stop(); saveCut(); saving = true; $('save-board').disabled = true; $('save-board-status').textContent = 'Saving your MP3…';
      try {
        const clip = await api('board','POST',{trackId:state.active.id,start:state.start,end:state.end,name:$('filename').value.trim() || state.active.name});
        await refreshBoard(); $('save-board-status').textContent = `“${clip.name}” is on the Soundboard. Everyone can play or download it.`;
      } catch (error) { $('save-board-status').textContent = error.message; }
      finally { saving = false; $('save-board').disabled = false; }
    });
  }
  async function init() {
    try {
      const bundled = JSON.parse($('bundled-library').textContent);
      if (shared) { state.tracks = await api('library'); await refreshBoard(); pollImports(); }
      else if (bundled) state.tracks = bundled;
      else {
        const response = await fetch('/api/audio-library');
        if (!response.ok) throw new Error('The built-in library is unavailable.');
        state.tracks = await response.json();
      }
      renderLibrary();
      if (state.tracks.length) await loadTrack(state.tracks[0]);
      else status('Add audio files to start trimming.');
    } catch { status(shared ? 'Could not load the shared library. Reload the page to try again.' : 'Add audio files to start trimming.', shared); renderLibrary(); }
  }
  init();
})();
