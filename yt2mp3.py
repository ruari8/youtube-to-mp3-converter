#!/usr/bin/env python3
"""
Media Downloader
A simple command-line tool to download YouTube videos as MP3s or Twitter videos as MP4s.
"""

import os
import sys
import argparse
from pathlib import Path
import yt_dlp


def create_output_dir(output_path):
    """Create output directory if it doesn't exist."""
    Path(output_path).mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename):
    """Remove or replace invalid filename characters."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def download_youtube_to_mp3(url, output_path=None, quality='best'):
    """
    Download YouTube video and convert to MP3.
    
    Args:
        url (str): YouTube video URL
        output_path (str): Directory to save the MP3 file
        quality (str): Audio quality ('best', 'worst', or specific format)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if output_path is None:
        output_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'YouTube_MP3')
    
    create_output_dir(output_path)
    
    # Configure yt-dlp options - fixed to prevent multiple downloads
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',  # Best audio only, specific formats
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,  # Only download single video, not playlist
        'no_warnings': False,
        'ignoreerrors': False,
        'writethumbnail': False,  # Don't download thumbnails
        'writeinfojson': False,   # Don't write info files
        'writedescription': False,  # Don't write description files
        'writesubtitles': False,   # Don't download subtitles
        'writeautomaticsub': False,  # Don't download auto-generated subs
        'embed_chapters': False,   # Don't embed chapters
        'split_chapters': False,   # Don't split into chapters (THIS IS KEY!)
        'extract_flat': False,     # Full extraction, not just metadata
        'ignoreerrors': False,     # Stop on errors rather than continue
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            print(f"Title: {title}")
            print(f"Duration: {duration // 60}:{duration % 60:02d}")
            print(f"Downloading and converting to MP3...")
            
            # Download and convert
            ydl.download([url])
            
            print(f"✅ Successfully converted: {title}")
            print(f"📁 Saved to: {output_path}")
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def download_twitter_video(url, output_path=None):
    """
    Download a video from a Tweet URL.

    Args:
        url (str): Twitter video URL
        output_path (str): Directory to save the MP4 file

    Returns:
        bool: True if successful, False otherwise
    """
    if output_path is None:
        output_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'Twitter_Videos')

    create_output_dir(output_path)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, '%(uploader)s_%(id)s.%(ext)s'),
        'noplaylist': True,
        'no_warnings': False,
        'ignoreerrors': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            uploader = info.get('uploader', 'Unknown')
            tweet_id = info.get('id', 'Unknown')
            
            print(f"Uploader: @{uploader}")
            print(f"Tweet ID: {tweet_id}")
            print(f"Downloading video...")

            ydl.download([url])

            print(f"✅ Successfully downloaded video from @{uploader}")
            print(f"📁 Saved to: {output_path}")
            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download videos from YouTube (as MP3) or Twitter (as MP4).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download YouTube video as MP3
  yt2mp3 https://www.youtube.com/watch?v=dQw4w9WgXcQ
  yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o ~/Music

  # Download Twitter video as MP4
  yt2mp3 https://twitter.com/user/status/12345
  yt2mp3 https://x.com/user/status/12345 -o ./videos
        """
    )
    
    parser.add_argument('url', help='YouTube or Twitter URL')
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output directory'
    )
    parser.add_argument(
        '-q', '--quality',
        default='best',
        help='Audio quality for YouTube downloads (default: best)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='Media Downloader 1.1.0'
    )
    
    args = parser.parse_args()
    
    url = args.url
    success = False

    if 'youtube.com' in url or 'youtu.be' in url:
        print("🎵 YouTube to MP3 Converter")
        print("=" * 40)
        success = download_youtube_to_mp3(url, args.output, args.quality)
    elif 'twitter.com' in url or 'x.com' in url:
        print("🐦 Twitter Video Downloader")
        print("=" * 40)
        success = download_twitter_video(url, args.output)
    else:
        print("❌ Error: Please provide a valid YouTube or Twitter URL.")
        sys.exit(1)

    if success:
        print("\n🎉 Download completed successfully!")
    else:
        print("\n💥 Download failed!")
        sys.exit(1)


if __name__ == '__main__':
    main() 