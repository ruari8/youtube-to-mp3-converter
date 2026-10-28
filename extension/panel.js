import { formatTime, parseTime, clipRange, nudgeTime } from './time.mjs';

const $ = (id) => document.getElementById(id);
let video = null;
let tabId = null;
let ready = false;
let job = null;
let syncing = false;
let submitting = false;
const mode = () => document.querySelector('input[name=mode]:checked').value;
const format = () => document.querySelector('input[name=format]:checked').value;

function showError(message = '') {
  $('error').hidden = !message;
  $('error').textContent = message;
}

async function request(message) {
  const response = await chrome.runtime.sendMessage(message);
  if (response?.error) throw new Error(response.error);
  return response;
}

async function player(action, extra = {}) {
  if (tabId === null) throw new Error('Open a YouTube video first.');
  const message = { target: 'yt2mp3-player', action, ...extra };
  let result;
  try {
    result = await chrome.tabs.sendMessage(tabId, message);
  } catch {
    // Also works on tabs that were open before the extension was loaded/reloaded.
    await chrome.scripting.executeScript({ target: { tabId }, files: ['youtube.js'] });
    result = await chrome.tabs.sendMessage(tabId, message);
  }
  if (result?.error) throw new Error(result.error);
  return result;
}

function updateControls() {
  const isClip = mode() === 'clip';
  $('controls').disabled = !video;
  $('clip-controls').hidden = !isClip;
  $('full-note').hidden = isClip;
  $('trim-note').hidden = !isClip;
  $('quality-row').hidden = format() !== 'mp3';
  $('subtitles-row').hidden = format() !== 'mp4';
  $('format-note').textContent = {
    mp3: 'A small file that plays almost anywhere.',
    flac: 'Larger audio files. FLAC preserves the decoded source; it cannot restore lost quality.',
    mp4: 'Video with audio, at the best available source quality.',
  }[format()];
  $('destination').textContent = `Saves to Downloads / YouTube_${format().toUpperCase()}`;
  $('download').disabled = !ready || !video || job?.status === 'working' || submitting;
  $('download').textContent = job?.status === 'working' || submitting ? 'Working on your download…' : isClip ? '↓ Download clip' : '↓ Download full video';
  const start = parseTime($('start').value), end = parseTime($('end').value);
  $('selection-length').textContent = end > start ? formatTime(end - start) : 'Choose times';
  if (Number.isFinite(start)) $('start-range').value = start;
  if (Number.isFinite(end)) $('end-range').value = end;
}

async function syncVideo() {
  if (syncing) return;
  syncing = true;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !/^https:\/\/(www|m)\.youtube\.com\//.test(tab.url || '')) {
      throw new Error('Open a YouTube video to get started.');
    }
    const previousTab = tabId;
    tabId = tab.id;
    const snapshot = await player('snapshot');
    const changed = !video || snapshot.id !== video.id || previousTab !== tabId;
    video = snapshot;
    $('video-title').textContent = video.title;
    $('video-meta').textContent = `${formatTime(video.duration)} · YouTube`;
    $('playhead').textContent = `At ${formatTime(video.currentTime)}`;
    const duration = Math.floor(video.duration * 1000) / 1000;
    $('start-range').max = Math.max(0, duration - 0.001);
    $('end-range').max = duration;
    if (changed) {
      const start = Math.min(video.currentTime, Math.max(0, duration - 0.001));
      $('start').value = formatTime(start);
      $('end').value = formatTime(Math.min(start + 30, duration));
      showError();
    }
  } catch (error) {
    video = null;
    $('video-title').textContent = 'Choose a video';
    $('video-meta').textContent = error.message;
  } finally {
    syncing = false;
    updateControls();
  }
}

async function checkHelper() {
  $('connection').textContent = 'Connecting to your Mac…';
  try {
    const response = await request({ action: 'ping' });
    ready = response.status === 'ready';
    $('connection').textContent = response.message;
    $('helper-error').textContent = ready ? '' : response.message;
  } catch (error) {
    ready = false;
    $('connection').textContent = 'Local helper is not connected';
    $('helper-error').textContent = error.message;
  }
  $('connection-dot').classList.toggle('ready', ready);
  $('setup').hidden = ready;
  updateControls();
}

function renderJob(next) {
  job = next;
  $('job').hidden = !job;
  if (!job) return;
  $('job-label').textContent = job.status === 'done' ? 'SAVED' : job.status === 'error' ? 'COULD NOT SAVE' : 'DOWNLOADING';
  $('job-title').textContent = job.title;
  $('job-message').textContent = job.message + (Number.isFinite(job.percent) ? ` ${job.percent}%` : '');
  $('progress').hidden = job.status !== 'working';
  if (Number.isFinite(job.percent)) $('progress').value = job.percent;
  else $('progress').removeAttribute('value');
  $('reveal').hidden = job.status !== 'done';
  $('filename').hidden = job.status !== 'done';
  $('filename').textContent = job.filename || '';
  updateControls();
}

const safely = (fn) => async () => {
  try { showError(); await fn(); } catch (error) { showError(error.message); }
};

function setBoundary(boundary, value) {
  const start = parseTime($('start').value), end = parseTime($('end').value);
  if (![start, end, value].every(Number.isFinite)) throw new Error('Enter valid start and end times first.');
  const duration = Math.floor(video.duration * 1000) / 1000;
  const minimum = boundary === 'start' ? 0 : Math.min(start + 0.001, duration);
  const maximum = boundary === 'start' ? Math.max(0, Math.min(end, duration) - 0.001) : duration;
  $(boundary).value = formatTime(nudgeTime(value, 0, minimum, maximum));
  updateControls();
}

function nudge(boundary, direction, step = Number($('nudge-step').value)) {
  setBoundary(boundary, nudgeTime(parseTime($(boundary).value), direction * step, 0, video.duration));
}

document.querySelectorAll('[data-boundary]').forEach((button) => {
  button.addEventListener('click', safely(() => nudge(button.dataset.boundary, Number(button.dataset.direction))));
});

for (const boundary of ['start', 'end']) {
  $(boundary).addEventListener('input', updateControls);
  $(boundary).addEventListener('blur', () => {
    const value = parseTime($(boundary).value);
    if (Number.isFinite(value)) $(boundary).value = formatTime(value);
  });
  $(boundary).addEventListener('keydown', (event) => {
    if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    const step = event.altKey ? 0.001 : event.shiftKey ? 0.1 : Number($('nudge-step').value);
    safely(() => nudge(boundary, event.key === 'ArrowUp' ? 1 : -1, step))();
  });
  $(`${boundary}-range`).addEventListener('input', safely(() => setBoundary(boundary, Number($(`${boundary}-range`).value))));
  $(`${boundary}-now`).addEventListener('click', safely(async () => {
    const current = await player('snapshot');
    if (current.id !== video?.id) { await syncVideo(); return; }
    $(boundary).value = formatTime(Math.min(current.currentTime, Math.floor(current.duration * 1000) / 1000));
    updateControls();
  }));
}

$('preview').addEventListener('click', safely(async () => {
  await player('preview', clipRange($('start').value, $('end').value, video.duration));
}));
$('stop-preview').addEventListener('click', safely(() => player('stop')));
$('reconnect').addEventListener('click', checkHelper);
$('reveal').addEventListener('click', safely(async () => {
  const result = await request({ action: 'reveal', path: job.path });
  if (result.status === 'error') throw new Error(result.message);
}));

$('download-form').addEventListener('change', () => {
  updateControls();
  chrome.storage.local.set({ preferences: { format: format(), quality: $('quality').value, nudgeStep: $('nudge-step').value, subtitles: $('subtitles').checked } });
});
$('download-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!video || submitting || job?.status === 'working') return;
  try {
    showError();
    const clip = mode() === 'clip' ? clipRange($('start').value, $('end').value, video.duration) : null;
    submitting = true;
    updateControls();
    await request({ action: 'download', url: video.url, title: video.title, format: format(), quality: $('quality').value, clip, subtitles: format() === 'mp4' && $('subtitles').checked });
    renderJob((await request({ action: 'state' })).job);
  } catch (error) {
    showError(error.message);
  } finally {
    submitting = false;
    updateControls();
  }
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.job) renderJob(changes.job.newValue);
});
chrome.tabs.onActivated.addListener(syncVideo);
chrome.tabs.onUpdated.addListener((id) => { if (id === tabId) syncVideo(); });

const { preferences } = await chrome.storage.local.get('preferences');
if (['mp3', 'mp4', 'flac'].includes(preferences?.format)) document.querySelector(`input[name=format][value=${preferences.format}]`).checked = true;
if (['128', '192', '256', '320'].includes(preferences?.quality)) $('quality').value = preferences.quality;
if (['0.001', '0.01', '0.1'].includes(preferences?.nudgeStep)) $('nudge-step').value = preferences.nudgeStep;
$('subtitles').checked = preferences?.subtitles === true;
renderJob((await request({ action: 'state' })).job);
await Promise.all([syncVideo(), checkHelper()]);
setInterval(syncVideo, 1000);
