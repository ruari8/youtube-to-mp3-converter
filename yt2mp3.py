#!/usr/bin/env python3
"""
YouTube to MP3 Converter
A simple command-line tool to download YouTube videos and convert them to MP3 format.
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
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,  # Only download single video, not playlist
        'extractaudio': True,
        'audioformat': 'mp3',
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


def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube videos and convert them to MP3 format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  yt2mp3 https://www.youtube.com/watch?v=dQw4w9WgXcQ
  yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o ~/Music
  yt2mp3 https://youtu.be/dQw4w9WgXcQ --output ./downloads
        """
    )
    
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output directory (default: ~/Downloads/YouTube_MP3)'
    )
    parser.add_argument(
        '-q', '--quality',
        default='best',
        help='Audio quality (default: best)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='YouTube to MP3 Converter 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Validate URL
    if not any(domain in args.url for domain in ['youtube.com', 'youtu.be']):
        print("❌ Error: Please provide a valid YouTube URL")
        sys.exit(1)
    
    print("🎵 YouTube to MP3 Converter")
    print("=" * 40)
    
    success = download_youtube_to_mp3(args.url, args.output, args.quality)
    
    if success:
        print("\n🎉 Conversion completed successfully!")
    else:
        print("\n💥 Conversion failed!")
        sys.exit(1)


if __name__ == '__main__':
    main() 