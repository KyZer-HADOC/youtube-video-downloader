# KyZer YouBe

**KyZer YouBe** is a Windows desktop media utility with a dark red interface.

## Platforms and tools

- **YouTube, TikTok and Facebook:** public videos and supported posts with quality selection.
- **Other DL:** try thousands of sites supported by yt-dlp, plus generic webpage and direct media URLs. Compatibility depends on the site and how its player serves video.
- **Separate video/audio downloads:** choose either or both, with independent video resolution and MP3 bitrate settings.
- **Download Later:** save links persistently, close the app, and download selected or all links later.
- **Thumbnail and media details:** load a post thumbnail, title, creator, duration and available size.
- **In-app preview:** attempts to play the source stream without downloading the whole video first.
- **Clip selection:** select Start and End points to download a section.
- **Progress details:** percent, downloaded size, total size, remaining size, speed and ETA.
- **Extras:** subtitles when available, embedded thumbnails, playlists, active queue and local download history.
- **WhatsApp Desktop detection:** checks whether WhatsApp is installed and enables local status-media scanning when a folder is available.

No downloader can guarantee every website works. Private, encrypted, DRM-protected, login-only, CAPTCHA-protected or unsupported players may block extraction. Respect the site's terms and only save content you are allowed to download.

## Other DL

Open Other DL, paste an HTTP or HTTPS webpage/video link, press Get Video Info, choose video/audio and quality, then Download Now. The engine uses yt-dlp's available site-specific extractors first and generic webpage detection as a fallback. Direct media URLs such as MP4 or HLS links can work too. This is broad site support, not a promise that every URL on the internet is downloadable.

## Download Later

Use Save for Later on Downloader or Other DL, or paste a URL into the Download Later tab. Links are kept in the local app data folder at %LOCALAPPDATA%\KyZer YouBe\download_later.json and remain after closing the app. Successfully downloaded links are removed automatically; you can also remove them manually.

## TikTok and HTTP 429 troubleshooting

Some services, especially TikTok, may temporarily rate-limit automated requests or require a browser session. Open the post in your normal browser, finish any CAPTCHA/verification, then in Settings select the same browser under Browser Session and retry. The app reads cookies only after you explicitly select a browser. A 429 response is imposed by the source service, so waiting before retrying may be necessary.

The app adds retry delays and backoff for metadata and subtitle requests. Subtitle failures are treated as optional and should not cancel a successful media download. A severe source-side block can still prevent the whole request.

## Diagnostic log

A rotating diagnostic log is written locally to:

%LOCALAPPDATA%\KyZer YouBe\log.txt

Open Settings and press Open log.txt to view extractor, thumbnail, subtitle, download and runtime errors. The file is kept on this PC.

## WhatsApp Status

KyZer YouBe checks whether WhatsApp Desktop is installed. WhatsApp Desktop does not expose a supported public status-download API or a guaranteed .Statuses folder. The app scans a real local status-media folder only if one exists or has been exported by the user. It does not treat private chat caches as status media and does not request account credentials or QR sessions.

## Run from source

1. Install Python 3.10 or newer.
2. Install dependencies: python -m pip install -r requirements.txt
3. Launch: python app.py

## Build on Windows

Install dependencies and PyInstaller, run python build_windows.py, then compile Setup.iss with Inno Setup 6. GitHub Actions performs these steps and publishes Setup.exe to Releases.

## FFmpeg

The Windows bundle includes FFmpeg through imageio-ffmpeg for format merging, audio extraction and clip cutting.

## Windows security

The installer is per-user and does not request administrator rights. Without a trusted Authenticode certificate, Windows SmartScreen may still show an unrecognized-app warning for a new download.

## Responsible use

Only download content you have permission to save. Follow platform terms, copyright laws and privacy rules.
