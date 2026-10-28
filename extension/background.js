const HOST = 'local.yt2mp3';
let port = null;
let job = null;
const initialized = chrome.storage.local.get('job').then(async (saved) => {
  job = saved.job || null;
  if (job?.status === 'working') {
    job = { ...job, status: 'error', message: 'Chrome closed before the download finished. Please try again.' };
    await chrome.storage.local.set({ job });
  }
});

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

// Serialize writes so the final result cannot be overwritten by an earlier progress event.
let writes = Promise.resolve();
function saveJob(update) {
  job = { ...job, percent: null, ...update };
  const snapshot = { ...job };
  writes = writes.then(() => chrome.storage.local.set({ job: snapshot }));
  return writes;
}

async function handle(message) {
  await initialized;
  if (message.action === 'state') return { job };
  if (message.action === 'ping' || message.action === 'reveal') {
    return chrome.runtime.sendNativeMessage(HOST, message);
  }
  if (message.action !== 'download') throw new Error('Unknown action.');
  if (port) throw new Error('A download is already running.');
  port = chrome.runtime.connectNative(HOST);
  const connection = port;
  job = { status: 'working', title: String(message.title || 'YouTube video'), message: 'Connecting…', format: message.format };
  connection.onMessage.addListener((update) => {
    if (port !== connection) return;
    saveJob(update);
    if (update.status === 'done' || update.status === 'error') {
      port = null;
      connection.disconnect();
    }
  });
  connection.onDisconnect.addListener(() => {
    const error = chrome.runtime.lastError;
    if (port !== connection) return;
    port = null;
    saveJob({ status: 'error', message: error?.message || 'The local helper disconnected. Please try again.' });
  });
  await saveJob(job);
  connection.postMessage(message);
  return { ok: true };
}

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  // Download requests only come from our panel, never from a web page/content script.
  if (sender.id !== chrome.runtime.id || sender.url !== chrome.runtime.getURL('panel.html')) return;
  handle(message).then(reply, (error) => reply({ error: error.message }));
  return true;
});
