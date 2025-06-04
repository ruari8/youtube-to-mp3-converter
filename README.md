# YouTube to MP3 Converter 🎵

A simple, fast command-line tool to download YouTube videos and convert them to MP3 format. Perfect for downloading long concert videos, podcasts, or any audio content without time limits!

## Features

- ✅ **No time limits** - Download videos of any length (unlike websites with 90min caps)
- ✅ **High quality audio** - 192kbps MP3 by default
- ✅ **Simple command-line interface** - Just `yt2mp3 <youtube_url>`
- ✅ **Automatic file naming** - Uses video title as filename
- ✅ **Custom output directory** - Save files wherever you want
- ✅ **Safe filename handling** - Automatically sanitizes invalid characters

## Quick Start

### Option 1: Simple Usage (No Installation)
```bash
# Activate your virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download and convert a YouTube video
python yt2mp3.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Option 2: Install as Command-Line Tool
```bash
# Activate your virtual environment
source venv/bin/activate

# Install the tool
pip install -e .

# Now you can use it from anywhere
yt2mp3 "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Prerequisites

You need **FFmpeg** installed on your system for audio conversion:

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

### Basic usage
```bash
yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
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

- **Output location**: `~/Downloads/YouTube_MP3/`
- **Audio quality**: 192kbps MP3
- **Filename**: Uses the YouTube video title (sanitized for filesystem)

## For Spotify Local Files

After downloading, you can add these MP3 files to Spotify:

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
- **Video handling**: Downloads best available audio stream, ignores video
- **File safety**: Automatically handles special characters in video titles

## Legal Notice

This tool is for personal use only. Please respect YouTube's Terms of Service and copyright laws. Only download content you have permission to download.

---

Enjoy your unlimited YouTube to MP3 conversions! 🎶 