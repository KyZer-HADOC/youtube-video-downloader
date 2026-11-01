# KyZer Downloader

A lightweight Windows desktop YouTube downloader with a modern Tkinter interface and yt-dlp as its download engine.

## Features

- Download videos in best available quality, 1080p, 720p, or 480p.
- Extract audio as MP3.
- Choose the output folder.
- Live progress, download speed, and estimated time remaining.
- Background downloading keeps the interface responsive.
- FFmpeg support for format merging and MP3 conversion.

## Run from source

1. Install Python 3.10 or newer.
2. Clone this repository.
3. Install dependencies:

       python -m pip install -r requirements.txt

4. Start the app:

       python gui.py

## FFmpeg

FFmpeg is recommended for merging separate video/audio streams and is required for MP3 conversion. Install FFmpeg and make sure the ffmpeg command is available in your system PATH. Without FFmpeg, the downloader falls back to a single-file video format where possible.

## Build a Windows executable

Install PyInstaller:

       python -m pip install pyinstaller

Then build:

       pyinstaller --noconfirm --clean --windowed --name "KyZer Downloader" gui.py

The executable will be created in the dist folder. FFmpeg must still be installed separately unless you bundle it yourself.

## Update yt-dlp

       python -m pip install --upgrade yt-dlp

Download only content you have permission to save, and follow YouTube's terms and applicable copyright laws.
