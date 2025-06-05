# Media Downloader 🎵

A simple, fast command-line tool to download media from various platforms.
- Download YouTube videos and convert them to MP3.
- Download videos from Twitter/X as MP4 files.

Perfect for saving your favorite online content for offline access!

## Features

- ✅ **Multi-Platform** - Supports YouTube (MP3) and Twitter/X (MP4).
- ✅ **No time limits** - Download videos of any length.
- ✅ **High quality** - 192kbps MP3 for YouTube audio.
- ✅ **Simple command-line interface** - Just `yt2mp3 <url>`
- ✅ **Automatic file naming** - Uses video title or tweet info.
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

### Download YouTube video as MP3
```bash
yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Download Twitter/X video as MP4
```bash
yt2mp3 "https://x.com/StHydrated/status/1930422978228912172"
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

## Default Behavior

- **YouTube Output**: `~/Downloads/YouTube_MP3/` as a 192kbps MP3.
- **Twitter Output**: `~/Downloads/Twitter_Videos/` as an MP4 video.
- **Filename**: Uses the YouTube video title or Twitter info (uploader and tweet ID).

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

## Technical Details

- **Backend**: Uses `yt-dlp` (the actively maintained fork of `youtube-dl`)
- **Audio format**: MP3 at 192kbps (good balance of quality and file size)
- **Video handling**: Downloads best available audio for YouTube, best video for Twitter.
- **File safety**: Automatically handles special characters in video titles

## Legal Notice

This tool is for personal use only. Please respect the Terms of Service and copyright laws of the platforms you are downloading from. Only download content you have permission to download.

---

Enjoy your media downloads! 🎶 