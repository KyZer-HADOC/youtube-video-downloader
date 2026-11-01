# KyZer Downloader — Setup Guide

## 1. Requirements

- Windows 10 or later
- Python 3.10 or newer
- FFmpeg (recommended; required for MP3 conversion and merging separate audio/video streams)

## 2. Download the project

Clone the repository:

    git clone https://github.com/KyZer-HADOC/youtube-video-downloader.git
    cd youtube-video-downloader

Or download the ZIP from GitHub and extract it.

## 3. Install dependencies

Open Command Prompt or PowerShell in the project folder and run:

    python -m pip install -r requirements.txt

## 4. Launch the desktop app

    python gui.py

The app window is titled **KyZer Downloader**. Paste a YouTube URL, select a quality, choose a save folder, and click **Download Now**.

## 5. Build a Windows EXE

Install PyInstaller:

    python -m pip install pyinstaller

Build the executable:

    pyinstaller --noconfirm --clean --windowed --name "KyZer Downloader" gui.py

The executable will be available in:

    dist\KyZer Downloader\KyZer Downloader.exe

FFmpeg is not bundled automatically. Install it separately and add its bin folder to your Windows PATH if you need MP3 conversion or high-quality audio/video merging.

## Supported formats

- Best quality
- 1080p HD
- 720p HD
- 480p SD
- MP3 audio

## Troubleshooting

### yt-dlp is missing

Run:

    python -m pip install --upgrade -r requirements.txt

### FFmpeg is missing

Install FFmpeg, add the folder containing ffmpeg.exe to PATH, then restart the app. MP3 conversion requires FFmpeg.

### Download fails

Check that the link is public and available, then update yt-dlp:

    python -m pip install --upgrade yt-dlp

Some videos may be private, unavailable, region-restricted, or otherwise inaccessible.

## Legal note

Download only content you have permission to save, and follow YouTube's terms and applicable copyright laws.
