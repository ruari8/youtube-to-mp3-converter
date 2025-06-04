from setuptools import setup

setup(
    name="yt2mp3",
    version="1.0.0",
    description="A simple YouTube to MP3 converter",
    author="Your Name",
    py_modules=["yt2mp3"],
    install_requires=[
        "yt-dlp>=2024.3.10",
    ],
    entry_points={
        "console_scripts": [
            "yt2mp3=yt2mp3:main",
        ],
    },
    python_requires=">=3.6",
) 