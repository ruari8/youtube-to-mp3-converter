import test from 'node:test';
import assert from 'node:assert/strict';
import { formatTime, parseTime, clipRange, nudgeTime } from '../extension/time.mjs';

test('timestamps support long videos and subsecond cuts', () => {
  assert.equal(parseTime('1:02:03.5'), 3723.5);
  assert.equal(parseTime('90'), 90);
  assert.equal(formatTime(3723), '1:02:03.000');
  assert.deepEqual(clipRange('1:30', '2:00', 180), { start: 90, end: 120 });
});

test('millisecond formatting preserves cuts and carries across minute and hour boundaries', () => {
  for (const seconds of [0, 1.456, 59.999, 60.001, 3599.999, 3600.001]) {
    assert.equal(parseTime(formatTime(seconds)), seconds);
  }
  assert.equal(formatTime(1.456), '0:01.456');
  assert.equal(formatTime(59.9996), '1:00.000');
  assert.equal(formatTime(3599.9996), '1:00:00.000');
  assert.deepEqual(clipRange('0:01.456', '0:02.789', 4.551), { start: 1.456, end: 2.789 });
});

test('fine nudges are repeatable and stop at clip boundaries', () => {
  let position = 1.456;
  for (let i = 0; i < 100; i++) position = nudgeTime(position, 0.001, 0, 5);
  assert.equal(position, 1.556);
  assert.equal(nudgeTime(position, -0.01, 0, 5), 1.546);
  assert.equal(nudgeTime(0, -0.1, 0, 5), 0);
  assert.equal(nudgeTime(1.999, 0.01, 0, 1.999), 1.999);
  assert.equal(nudgeTime(4.54, 0.1, 1.457, 4.551), 4.551);
});

test('invalid ranges cannot become a download', () => {
  for (const value of ['', '-1', '1:99', '1:2:3:4', 'Infinity', '1.5:20']) {
    assert.ok(Number.isNaN(parseTime(value)), value);
  }
  assert.throws(() => clipRange('2:00', '1:00', 180));
  assert.throws(() => clipRange('0:00', '4:00', 180));
});
