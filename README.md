# yt2mp3

A small local media downloader for saving online audio/video into files that are easy to keep in a personal library.

I mostly use it to turn YouTube concert clips and live sessions into MP3 files, then add those files to Spotify via Local Files. The CLI also supports YouTube MP4/FLAC, SoundCloud MP3, X/Twitter videos, Instagram posts/carousels, and a lightweight local web UI.

## Features

- YouTube to MP3, FLAC, or MP4
- SoundCloud to MP3
- X/Twitter video downloads
- Instagram post and carousel downloads
- Optional local web UI backed by a stdlib-only Python server
- Configurable output folders
- Browser-cookie fallback for YouTube bot-detection errors

## Requirements

- Python 3.10+
- FFmpeg and FFprobe on your `PATH`
- Deno 2.3+ on your `PATH` for YouTube JavaScript challenges
- `yt-dlp[default]>=2026.8.19`, including the YouTube challenge solver

Install FFmpeg and Deno:

```bash
# macOS
brew install ffmpeg deno

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg
```

On Linux, follow the [Deno installation instructions](https://docs.deno.com/runtime/getting_started/installation/) to install Deno.

## Setup

```bash
git clone https://github.com/ruari8/youtube-to-mp3-converter.git
cd youtube-to-mp3-converter

python3 -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

After editable install, the `yt2mp3` command is available from the active virtualenv.

## CLI Usage

Download a YouTube video as MP3:

```bash
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID"
```

Choose an MP3 bitrate:

```bash
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID" -q 320
```

Save directly into a Spotify Local Files folder:

```bash
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID" -o "$HOME/Music/YouTube Local Files"
```

Download YouTube as FLAC or MP4:

```bash
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID" --flac
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID" --mp4
```

Download from other supported platforms:

```bash
yt2mp3 "https://soundcloud.com/artist/track-name"
yt2mp3 "https://x.com/user/status/12345"
yt2mp3 "https://www.instagram.com/p/POST_ID/"
```

Instagram carousel options:

```bash
# First item only, which is the default
yt2mp3 "https://www.instagram.com/p/POST_ID/"

# All carousel items
yt2mp3 "https://www.instagram.com/p/POST_ID/" --ig-all

# Specific carousel items
yt2mp3 "https://www.instagram.com/p/POST_ID/" --ig-index 1,3-4
```

If YouTube asks yt-dlp to sign in or confirm you are not a bot, pass browser cookies explicitly:

```bash
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser safari
```

## Personal Chrome extension

The `extension/` folder contains a Chrome side panel for the existing downloader. It reads the video in your active YouTube tab and lets you:

- Set millisecond start/end times such as `0:01.456`, drag the sliders, or use the current playback position.
- Fine-tune either boundary with ± buttons in 1, 10 or 100 millisecond steps. In a time field, ↑/↓ uses the selected step, Shift uses 100 ms, and Option uses 1 ms.
- Preview a clip in the YouTube player.
- Save a clip or the full video as MP3, FLAC or MP4.
- Choose MP3 bitrate, follow download progress, and reveal the finished file in Finder.
- For MP4, turn on **Include subtitles** to burn English captions into the video. This works for full videos and trimmed clips. Creator captions take priority, with automatic captions as a fallback. If no English captions are available, the download reports that instead of silently leaving them out.

### Install on macOS

After installing the requirements above, register the local helper:

```bash
./venv/bin/python scripts/install_chrome_helper.py
```

In Chrome, open `chrome://extensions`, enable Developer mode, click **Load unpacked**, and select this project's `extension` folder. Pin **yt2mp3 · Clip & save** from the extensions menu. Open a YouTube video and click the pinned icon.

Chrome starts the helper on demand. You do not need a terminal or local web server running. Downloads continue if you close the panel, but keep Chrome open until they finish. The panel remembers your format/bitrate and most recent download.

The helper saves to the same `~/Downloads/YouTube_MP3`, `YouTube_FLAC` and `YouTube_MP4` folders as the CLI. Duplicate downloads get numbered filenames. Clips download the source first, then use FFmpeg to cut precisely; video clips are re-encoded as H.264/AAC. FLAC cannot restore detail absent from YouTube's compressed audio. Active live streams are unsupported.

The installer copies the Python helper and downloader to `~/Library/Application Support/yt2mp3` because macOS may prevent Chrome from launching a helper in Documents. It uses the existing pipx yt2mp3 Python environment when available, otherwise the repo's virtualenv. The registration file is `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/local.yt2mp3.json`. Its allowed origin is restricted to this extension's fixed ID.

After Python changes, rerun the installer. After extension changes, click **Reload** on its card in `chrome://extensions`. If the panel reports that the helper is disconnected, expand its setup instructions for the error and click **Retry** after fixing it.

To uninstall, remove the extension in Chrome and delete the registration file and the `~/Library/Application Support/yt2mp3` helper directory. This leaves downloaded media and the CLI intact.

### Verify

```bash
./venv/bin/python -m unittest discover -s tests -v
node --test tests/test_extension.mjs
```

The tests run FFmpeg against generated media in all three formats, check clip lengths and full-file preservation, exercise the native messaging protocol, and check invalid requests and duplicate filenames. They do not depend on YouTube being available.

## Local Web UI

Run the local server:

```bash
python web_server.py
```

Or, after `python -m pip install -e .`:

```bash
yt2mp3-web
```

Then open:

```text
http://127.0.0.1:8008/
```

The web UI writes finished files under the repo-local `downloads/` directory. That folder is intentionally gitignored.

## Audio trimmer

Open `http://127.0.0.1:8008/trimmer` after starting the web server, or choose **Trim audio** from the downloader.

- Choose a full track from the saved Stream Deck pack, or add your own audio files.
- Drag the orange IN/OUT handles, type exact seconds, or nudge either boundary by 0.1 seconds.
- Preview the cut, loop it, or listen from the cursor to hear surrounding audio.
- Zoom around a cut or use the full-track overview to navigate.
- Download a 320 kbps MP3 or an uncompressed WAV. The original file stays untouched.

The trimmer runs in the browser. Web Audio owns decoding and playback; the selected sample range is passed to a worker for MP3/WAV export. No audio is uploaded. Browser storage remembers each track's latest selection when available. Playback and export use the same selection. MP3 adds encoder padding; WAV has the exact selected sample count.

### Share with someone else

Build a portable copy with all nine full tracks included:

```bash
python3 scripts/build_portable_trimmer.py
```

Send `downloads/Sound-Cut-share.zip`. The recipient extracts it and opens **Sound Cut.html** in a desktop browser. It works offline, with no Python, FFmpeg, or server setup. They can also add their own audio files. The full videos remain in the original sound pack; the trimmer bundle includes the full audio only.

The builder reads `downloads/stream-deck-sounds/sources-and-timestamps.json` and embeds its full audio files and original cut presets. The server uses that same manifest for its library. Without the saved pack, the server's trimmer still accepts imported files.

Source UI files live in `frontend/trimmer.html` and `frontend/assets/trimmer/`. The vendored, unmodified [lamejs 1.2.1 encoder](https://github.com/zhuker/lamejs) uses LAME under the LGPL; its license notice is in `frontend/assets/trimmer/vendor/LICENSE`.

## Default Output Locations

When no output directory is provided, the CLI uses:

| Platform / mode | Output folder |
| --- | --- |
| YouTube MP3 | `~/Downloads/YouTube_MP3/` |
| YouTube FLAC | `~/Downloads/YouTube_FLAC/` |
| YouTube MP4 | `~/Downloads/YouTube_MP4/` |
| SoundCloud MP3 | `~/Downloads/SoundCloud_MP3/` |
| X/Twitter MP4 | `~/Downloads/Twitter_Videos/` |
| Instagram media | `~/Downloads/Instagram/` |

## Spotify Local Files Workflow

1. Download MP3s into a stable folder, for example `~/Music/YouTube Local Files`.
2. Open Spotify settings.
3. Enable Local Files.
4. Add the folder that contains the downloaded MP3s.
5. Add tracks from Spotify's Local Files view into normal playlists.

This repo does not write Spotify metadata or sync anything to Spotify. It only creates local audio/video files.

## Maintenance Notes

`yt-dlp` needs frequent updates because supported sites change their markup and extraction rules. If downloads start failing unexpectedly, update the environment that runs your `yt2mp3` command.

For a pipx installation:

```bash
pipx runpip yt2mp3 install --upgrade "yt-dlp[default]>=2026.8.19"
```

For the repo's virtualenv:

```bash
source venv/bin/activate
python -m pip install --upgrade -r requirements.txt
```

Updating Homebrew's `yt-dlp` or the repo's virtualenv does not update pipx's copy. The `[default]` extra installs the YouTube challenge solver alongside `yt-dlp`.

YouTube's Android VR client can return `HTTP Error 403: Forbidden` after metadata extraction succeeds. [yt-dlp fixed this issue in 2026.08.19](https://github.com/yt-dlp/yt-dlp/issues/17456). Update first if you see this error.

For YouTube bot-detection errors, common fixes are:

- Disable VPN/proxy exit nodes temporarily.
- Try a different network.
- Use `--cookies-from-browser chrome`, `safari`, or `firefox`.
- Wait a few minutes and retry if YouTube is rate-limiting the current IP.

## Development

Basic checks:

```bash
python -m py_compile yt2mp3.py web_server.py
yt2mp3 --help
python web_server.py --help
```

The Chrome helper has automated tests described above. Live downloads also need manual verification because third-party extraction rules can change.

## Legal

Use this for personal archiving and only download content you have permission to download. Respect platform terms and copyright law.
