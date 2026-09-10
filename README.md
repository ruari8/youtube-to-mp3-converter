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

There is no formal test suite yet. Most verification is currently manual because the behavior depends on third-party sites and FFmpeg.

## Legal

Use this for personal archiving and only download content you have permission to download. Respect platform terms and copyright law.
