# KyZer YouBe

**KyZer YouBe** is a Windows-first, all-in-one media utility with a dark red desktop interface.

## Platforms and tools

- **YouTube:** videos and supported public posts with quality selection.
- **TikTok:** supported public videos and posts.
- **Facebook:** supported public videos, reels and posts.
- **WhatsApp Status Saver:** saves status photos/videos already copied or exported from your own Android device to a local folder.
- **Video preview:** requests metadata and attempts to stream a preview without first downloading the whole video.
- **Clip selection:** set Start and End points and download only that section.
- **Progress details:** percent, downloaded size, total size, remaining size, speed and ETA.
- **Extras:** MP3 audio, subtitles (English/Sinhala when available), embedded thumbnails, playlist option, download queue and local history.

Downloads depend on the source being publicly accessible and on current yt-dlp extractor support. Private posts, login walls, age restrictions, regional restrictions and platform changes can prevent a download.

## WhatsApp Status

WhatsApp does not provide a public desktop status-download link. The Status Saver page works with files available locally on your own device. On Android, copy the WhatsApp media .Statuses folder to the PC, then select that copied folder in the app. The app does not ask for WhatsApp passwords, QR sessions or account cookies.

## Run from source

1. Install Python 3.10 or newer.
2. Install dependencies:

       python -m pip install -r requirements.txt

3. Launch:

       python app.py

## Build on Windows

Install dependencies and PyInstaller:

       python -m pip install -r requirements.txt
       python -m pip install pyinstaller

Build the app folder:

       python build_windows.py

Build Setup.exe using Inno Setup 6:

       ISCC.exe Setup.iss

GitHub Actions performs these steps automatically and publishes the Windows installer to the Releases page.

## FFmpeg

The Windows bundle includes FFmpeg through imageio-ffmpeg, so users do not need to install it separately for normal clip cutting, audio extraction or format merging.

## Windows security and signing

The installer uses a per-user install location and does not request administrator rights. GitHub Actions can Authenticode-sign the app and installer when the repository has the WINDOWS_CERTIFICATE_BASE64 and WINDOWS_CERTIFICATE_PASSWORD secrets configured with a trusted code-signing certificate. Without a trusted signing certificate, Windows SmartScreen may still show an unrecognized-app warning for a new download; no installer setting can guarantee that warning will never appear.

## Responsible use

Only download content you have permission to save. Follow the source platform's terms and applicable copyright laws. Respect creators' rights and user privacy.
