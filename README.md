# Media Downloader 🎵

A simple, fast command-line tool to download media from various platforms.
- Download YouTube videos and convert them to MP3 or lossless FLAC.
- Download YouTube videos as MP4.
- Download SoundCloud tracks as MP3.
- Download videos from Twitter/X as MP4 files.
- Download Instagram posts and carousels.

Perfect for saving your favorite online content for offline access!

## Features

- ✅ **Multi-Platform** - Supports YouTube, SoundCloud, Twitter/X, and Instagram.
- ✅ **Multiple formats** - MP3, FLAC (lossless), or MP4 video.
- ✅ **No time limits** - Download videos of any length.
- ✅ **High quality** - 192kbps MP3 or lossless FLAC for audio.
- ✅ **Simple command-line interface** - Just `yt2mp3 <url>`
- ✅ **macOS Quick Action** - Right-click any URL to download.
- ✅ **Automatic file naming** - Uses video title or post info.
- ✅ **Custom output directory** - Save files wherever you want.
- ✅ **Safe filename handling** - Automatically sanitizes invalid characters.

## Quick Start

### Option 1: Simple Usage (No Installation)
```bash
# Activate your virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download a YouTube video as MP3
python yt2mp3.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Download a Twitter video as MP4
python yt2mp3.py "https://x.com/user/status/12345"
```

### Option 2: Install as Command-Line Tool
```bash
# Activate your virtual environment
source venv/bin/activate

# Install the tool
pip install -e .

# Now you can use it from anywhere
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID"
yt2mp3 "https://x.com/user/status/12345"
```

## Prerequisites

You need **FFmpeg** installed on your system for video and audio processing:

### macOS (using Homebrew)
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

### Windows
Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) or use chocolatey:
```bash
choco install ffmpeg
```

## Usage Examples

### Download YouTube video as MP3 (default)
```bash
yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Download YouTube video as lossless FLAC
```bash
yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --flac
```

### Download YouTube video as MP4
```bash
yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --mp4
```

### Download SoundCloud track as MP3
```bash
yt2mp3 "https://soundcloud.com/artist/track-name"
```

### Download Twitter/X video as MP4
```bash
yt2mp3 "https://x.com/StHydrated/status/1930422978228912172"
```

### Download Instagram post
```bash
# First item only (default)
yt2mp3 "https://www.instagram.com/p/POST_ID/"

# All carousel items
yt2mp3 "https://www.instagram.com/p/POST_ID/" --ig-all

# Specific carousel items
yt2mp3 "https://www.instagram.com/p/POST_ID/" --ig-index 1,3-4
```

### Custom output directory
```bash
yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o ~/Music/YouTube
```

### Using short YouTube URLs
```bash
yt2mp3 "https://youtu.be/dQw4w9WgXcQ"
```

### Help and options
```bash
yt2mp3 --help
```

## macOS Quick Action (Right-Click to Download)

Install the Quick Action to download media by right-clicking any URL:

```bash
# Make sure yt2mp3 is installed first
pip install -e .

# Install the Quick Action
./scripts/install-quick-action.sh
```

**How to use:**
1. Select a URL in any app (browser, Notes, Slack, etc.)
2. Right-click and choose **Services** > **Download with yt2mp3**
3. The file will be downloaded to `~/Downloads/`
4. You'll get a notification when complete

**Note:** You may need to enable it in System Preferences > Keyboard > Shortcuts > Services.

## Default Behavior

| Platform | Output Format | Default Location |
|----------|---------------|------------------|
| YouTube | MP3 (192kbps) | `~/Downloads/YouTube_MP3/` |
| YouTube `--flac` | FLAC (lossless) | `~/Downloads/YouTube_FLAC/` |
| YouTube `--mp4` | MP4 (video) | `~/Downloads/YouTube_MP4/` |
| SoundCloud | MP3 (192kbps) | `~/Downloads/SoundCloud_MP3/` |
| Twitter/X | MP4 | `~/Downloads/Twitter_Videos/` |
| Instagram | MP4 | `~/Downloads/Instagram/` |

## For Spotify Local Files

After downloading YouTube MP3s, you can add them to Spotify:

1. Place MP3 files in a folder (e.g., `~/Music/YouTube/`)
2. Open Spotify → Settings → Local Files
3. Add the folder containing your MP3s
4. The files will appear in your "Local Files" playlist
5. You can add them to regular playlists or download for offline use

## Troubleshooting

### "FFmpeg not found"
Make sure FFmpeg is installed and in your PATH. See Prerequisites section above.

### "No module named 'yt_dlp'"
Make sure you've activated your virtual environment and installed dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Permission errors
Make sure you have write permissions to the output directory.

### Quick Action not appearing
1. Open System Preferences > Keyboard > Shortcuts > Services
2. Find "Download with yt2mp3" and enable it
3. You may need to log out and back in for changes to take effect

## Technical Details

- **Backend**: Uses `yt-dlp` (the actively maintained fork of `youtube-dl`)
- **Audio format**: MP3 at 192kbps or lossless FLAC
- **Video handling**: Downloads best available audio/video quality
- **File safety**: Automatically handles special characters in titles

## Legal Notice

This tool is for personal use only. Please respect the Terms of Service and copyright laws of the platforms you are downloading from. Only download content you have permission to download.

---

Enjoy your media downloads! 🎶
