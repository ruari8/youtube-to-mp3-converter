#!/usr/bin/env python3
"""
Media Downloader
A simple command-line tool to download YouTube videos as MP3s or MP4s, Twitter videos as MP4s, and Instagram media.
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
            duration = int(info.get('duration', 0))
            
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


def download_youtube_to_flac(url, output_path=None):
    """
    Download YouTube video and convert to lossless FLAC.
    """
    if output_path is None:
        output_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'YouTube_FLAC')

    create_output_dir(output_path)

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'flac',
        }],
        'noplaylist': True,
        'writethumbnail': False,
        'writeinfojson': False,
        'writedescription': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'embed_chapters': False,
        'split_chapters': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = int(info.get('duration', 0))

            print(f"Title: {title}")
            print(f"Duration: {duration // 60}:{duration % 60:02d}")
            print(f"Downloading and converting to FLAC (lossless)...")

            ydl.download([url])

            print(f"✅ Successfully converted: {title}")
            print(f"📁 Saved to: {output_path}")
            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def download_youtube_to_mp4(url, output_path=None):
    """
    Download YouTube video as MP4.
    
    Args:
        url (str): YouTube video URL
        output_path (str): Directory to save the MP4 file
    
    Returns:
        bool: True if successful, False otherwise
    """
    if output_path is None:
        output_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'YouTube_MP4')
    
    create_output_dir(output_path)
    
    # Configure yt-dlp options for MP4 video download
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',  # Merge video and audio into MP4
        'noplaylist': True,  # Only download single video, not playlist
        'no_warnings': False,
        'ignoreerrors': False,
        'writethumbnail': False,  # Don't download thumbnails
        'writeinfojson': False,   # Don't write info files
        'writedescription': False,  # Don't write description files
        'writesubtitles': False,   # Don't download subtitles
        'writeautomaticsub': False,  # Don't download auto-generated subs
        'embed_chapters': False,   # Don't embed chapters
        'split_chapters': False,   # Don't split into chapters
        'extract_flat': False,     # Full extraction, not just metadata
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = int(info.get('duration', 0))
            
            print(f"Title: {title}")
            print(f"Duration: {duration // 60}:{duration % 60:02d}")
            print(f"Downloading video as MP4...")
            
            # Download video
            ydl.download([url])
            
            print(f"✅ Successfully downloaded: {title}")
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


def download_soundcloud_to_mp3(url, output_path=None):
    """
    Download SoundCloud track as MP3.
    """
    if output_path is None:
        output_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'SoundCloud_MP3')

    create_output_dir(output_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
        'writethumbnail': False,
        'writeinfojson': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            uploader = info.get('uploader', 'Unknown')
            duration = int(info.get('duration', 0))

            print(f"Title: {title}")
            print(f"Artist: {uploader}")
            print(f"Duration: {duration // 60}:{duration % 60:02d}")
            print(f"Downloading and converting to MP3...")

            ydl.download([url])

            print(f"✅ Successfully converted: {title}")
            print(f"📁 Saved to: {output_path}")
            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def download_instagram_media(url, output_path=None, download_all=False, playlist_items=None):
    """
    Download Instagram media (focus on videos). Supports single post, full carousel,
    or selected carousel indices without authentication.

    Args:
        url (str): Instagram post URL
        output_path (str): Directory to save files
        download_all (bool): If True, download all items from a carousel
        playlist_items (str|None): Indices or ranges (e.g., "1,3-5") for carousel items

    Returns:
        bool: True if successful, False otherwise
    """
    if output_path is None:
        output_path = os.path.join(os.path.expanduser('~'), 'Downloads', 'Instagram')

    create_output_dir(output_path)

    multiple_items = bool(download_all or playlist_items)

    # Prefer MP4 when available; fall back to best
    outtmpl_single = os.path.join(output_path, '%(uploader)s_%(id)s.%(ext)s')
    outtmpl_multi = os.path.join(output_path, '%(uploader)s_%(playlist_index)s_%(id)s.%(ext)s')

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': outtmpl_multi if multiple_items else outtmpl_single,
        # Treat carousels as playlists so we can target indices
        'noplaylist': False,
        'no_warnings': False,
        'ignoreerrors': False,
    }

    # Default behavior: first item only when neither --ig-all nor --ig-index is provided
    if not multiple_items:
        ydl_opts['playlist_items'] = '1'
    elif playlist_items:
        ydl_opts['playlist_items'] = playlist_items

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Instagram')
            print(f"Post title: {title}")
            print("Downloading Instagram media...")
            ydl.download([url])
            print("✅ Successfully downloaded Instagram media")
            print(f"📁 Saved to: {output_path}")
            return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download media: YouTube (MP3, FLAC, or MP4), Twitter (MP4), Instagram (MP4), SoundCloud (MP3).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download YouTube video as MP3 (default)
  yt2mp3 https://www.youtube.com/watch?v=dQw4w9WgXcQ
  yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o ~/Music

  # Download YouTube video as lossless FLAC
  yt2mp3 https://www.youtube.com/watch?v=dQw4w9WgXcQ --flac

  # Download YouTube video as MP4
  yt2mp3 https://www.youtube.com/watch?v=dQw4w9WgXcQ --mp4
  yt2mp3 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --mp4 -o ~/Videos

  # Download SoundCloud track as MP3
  yt2mp3 https://soundcloud.com/artist/track-name

  # Download Twitter video as MP4
  yt2mp3 https://twitter.com/user/status/12345
  yt2mp3 https://x.com/user/status/12345 -o ./videos

  # Download Instagram post (first carousel item by default)
  yt2mp3 https://www.instagram.com/p/POST_ID/

  # Download all carousel items
  yt2mp3 https://www.instagram.com/p/POST_ID/ --ig-all -o ~/Downloads/Instagram

  # Download specific carousel indices
  yt2mp3 https://www.instagram.com/p/POST_ID/ --ig-index 1,3-4
        """
    )
    
    parser.add_argument('url', help='YouTube, Twitter, Instagram, or SoundCloud URL')
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output directory'
    )
    parser.add_argument(
        '-q', '--quality',
        default='best',
        help='Audio quality for YouTube MP3 downloads (default: best)'
    )
    parser.add_argument(
        '--mp4',
        action='store_true',
        help='For YouTube: download as MP4 video instead of MP3 audio'
    )
    parser.add_argument(
        '--flac',
        action='store_true',
        help='For YouTube: download as lossless FLAC audio instead of MP3'
    )
    # Instagram options (no-login). By default, downloads first item only
    parser.add_argument(
        '--ig-all',
        action='store_true',
        help='For Instagram carousels: download all items'
    )
    parser.add_argument(
        '--ig-index',
        default=None,
        help='For Instagram carousels: indices or ranges (e.g., 1,3-5)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='Media Downloader 1.2.0'
    )
    
    args = parser.parse_args()
    
    url = args.url
    success = False

    if 'youtube.com' in url or 'youtu.be' in url:
        if args.mp4:
            print("🎬 YouTube to MP4 Downloader")
            print("=" * 40)
            success = download_youtube_to_mp4(url, args.output)
        elif args.flac:
            print("🎵 YouTube to FLAC Converter (Lossless)")
            print("=" * 40)
            success = download_youtube_to_flac(url, args.output)
        else:
            print("🎵 YouTube to MP3 Converter")
            print("=" * 40)
            success = download_youtube_to_mp3(url, args.output, args.quality)
    elif 'soundcloud.com' in url:
        print("🎧 SoundCloud to MP3 Downloader")
        print("=" * 40)
        success = download_soundcloud_to_mp3(url, args.output)
    elif 'twitter.com' in url or 'x.com' in url:
        print("🐦 Twitter Video Downloader")
        print("=" * 40)
        success = download_twitter_video(url, args.output)
    elif 'instagram.com' in url:
        print("📸 Instagram Downloader")
        print("=" * 40)
        success = download_instagram_media(
            url,
            args.output,
            download_all=args.ig_all,
            playlist_items=args.ig_index,
        )
    else:
        print("❌ Error: Please provide a valid YouTube, Twitter, Instagram, or SoundCloud URL.")
        sys.exit(1)

    if success:
        print("\n🎉 Download completed successfully!")
    else:
        print("\n💥 Download failed!")
        sys.exit(1)


if __name__ == '__main__':
    main() 