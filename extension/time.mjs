export function formatTime(seconds) {
  const milliseconds = Math.max(0, Math.round(seconds * 1000));
  const value = Math.floor(milliseconds / 1000);
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor(value / 60) % 60;
  const tail = `${String(value % 60).padStart(2, '0')}.${String(milliseconds % 1000).padStart(3, '0')}`;
  return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${tail}` : `${minutes}:${tail}`;
}

export function nudgeTime(seconds, delta, minimum, maximum) {
  // Work in integer milliseconds so repeated nudges do not accumulate floating-point drift.
  const next = Math.round(seconds * 1000) + Math.round(delta * 1000);
  return Math.max(Math.round(minimum * 1000), Math.min(Math.round(maximum * 1000), next)) / 1000;
}

export function parseTime(text) {
  const value = text.trim();
  if (!/^\d+(?::\d{1,2}){0,2}(?:\.\d{1,3})?$/.test(value)) return NaN;
  const parts = value.split(':').map(Number);
  if (parts.slice(1).some((part) => part >= 60)) return NaN;
  return parts.reduce((total, part) => total * 60 + part, 0);
}

export function clipRange(startText, endText, duration) {
  const start = parseTime(startText), end = parseTime(endText);
  if (!Number.isFinite(start) || !Number.isFinite(end)) throw new Error('Enter times as 0:01.456, 1:02:30.000 or seconds.');
  if (start < 0 || start >= end) throw new Error('The end must be after the start.');
  if (end > duration + 0.1) throw new Error('The clip extends past the end of the video.');
  return { start, end };
}
