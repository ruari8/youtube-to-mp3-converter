from pathlib import Path

from setuptools import setup


ROOT = Path(__file__).resolve().parent

setup(
    name="yt2mp3",
    version="1.2.1",
    description="Local media downloader for YouTube, SoundCloud, X/Twitter, and Instagram",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Ruari",
    py_modules=["yt2mp3", "web_server"],
    install_requires=[
        "yt-dlp>=2024.3.10",
    ],
    entry_points={
        "console_scripts": [
            "yt2mp3=yt2mp3:main",
            "yt2mp3-web=web_server:main",
        ],
    },
    python_requires=">=3.10",
    project_urls={
        "Source": "https://github.com/ruari8/youtube-to-mp3-converter",
    },
)
