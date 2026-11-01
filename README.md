# KyZer YouBe

A Windows desktop video and audio downloader by **KyZer_HADOC**.

[![Download for Windows](https://img.shields.io/badge/Download-Windows%20Setup-red?logo=windows)](https://github.com/KyZer-HADOC/youtube-video-downloader/releases/latest)
[![GitHub Release](https://img.shields.io/github/v/release/KyZer-HADOC/youtube-video-downloader)](https://github.com/KyZer-HADOC/youtube-video-downloader/releases/latest)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Source%20Code-black?logo=github)](https://github.com/KyZer-HADOC/youtube-video-downloader)

## Download and install (recommended)

**You do not need a GitHub account or special repository access to download this public project.**

1. Open the [Latest Releases page](https://github.com/KyZer-HADOC/youtube-video-downloader/releases/latest).
2. Under **Assets**, download **KyZer-YouBe-Setup.exe**.
3. Double-click the downloaded installer.
4. Follow the setup steps. It installs for your Windows user and does not need administrator access.
5. Launch **KyZer YouBe** from the Start Menu.

[**Download KyZer YouBe for Windows — Setup.exe**](https://github.com/KyZer-HADOC/youtube-video-downloader/releases/latest/download/KyZer-YouBe-Setup.exe)

> Download the Setup.exe from Releases for the ready-to-install application. The Git commands below download the source-code project; they do not download the compiled Setup.exe.

## Download the source using Git

This is useful for developers or anyone who wants the project files.

### 1. Install Git

Open PowerShell or Command Prompt and check whether Git is installed:

```powershell
git --version
```

If Windows says that Git is not recognised, install Git for Windows from [git-scm.com](https://git-scm.com/download/win), then reopen the terminal.

### 2. Clone this public repository

Run:

```powershell
git clone --depth 1 https://github.com/KyZer-HADOC/youtube-video-downloader.git
cd youtube-video-downloader
```

Git downloads the latest project source into a folder named `youtube-video-downloader`. No username, password, personal access token or collaborator invitation is required for this public repository.

### 3. Run from source (optional)

Install Python 3.12, then run these commands inside the cloned folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

If PowerShell blocks virtual-environment activation, use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

### 4. Update an existing Git clone

Open a terminal inside the cloned `youtube-video-downloader` folder and run:

```powershell
git pull
```

## Features

- **YouTube, TikTok and Facebook:** download supported public videos and posts.
- **Other DL:** use yt-dlp's supported extractors and generic webpage detection for many additional sites and direct media URLs.
- **Separate video/audio options:** download video, MP3 audio, or both; select video resolution and audio bitrate separately.
- **Download Later:** save links locally and download them another time.
- **Video information and thumbnails:** display available titles, creators, durations, sizes and thumbnails.
- **Preview:** attempt to play an available source stream inside the app.
- **Clip selector:** choose start and end times to download a section.
- **Progress information:** percentage, downloaded size, total size, remaining size, speed and ETA.
- **Extras:** subtitles when available, embedded thumbnails, playlist downloads, queue and download history.
- **Diagnostics:** rotating `log.txt` file for troubleshooting.

No downloader can support literally every website. Private, DRM-protected, encrypted, login-only, CAPTCHA-protected or unsupported players may prevent extraction. Follow the website's rules and only download content you have permission to save.

## WhatsApp Status — important

The WhatsApp tab has a different limitation:

- KyZer YouBe checks whether **WhatsApp Desktop is installed on this PC**.
- WhatsApp Desktop does not provide a public API that lets this app fetch your account's Status updates directly.
- The app can scan a local status-media folder only when that folder actually exists and is accessible on the PC.
- If no such folder is exposed, the app cannot automatically fetch statuses from WhatsApp's servers. You may need to export/copy status files to the PC yourself.

The app does not ask for your WhatsApp password, QR login or private account session.

## TikTok and HTTP 429 errors

Some platforms temporarily limit automated requests or require a browser session.

1. Open the same post in your normal browser and complete any verification prompt.
2. In KyZer YouBe, open **Settings → Browser Session**.
3. Select the browser you used. Cookies are read only when you explicitly select a browser.
4. Retry after a short wait. An HTTP 429 response is a source-side rate limit, so the app cannot guarantee an immediate fix.

## Diagnostic log

The app writes a rotating log file here:

```text
%LOCALAPPDATA%\KyZer YouBe\log.txt
```

Open **Settings → Open log.txt** to inspect errors. The log stays on your PC.

## Build the Windows installer (developers)

The GitHub Actions workflow builds the Windows installer automatically whenever changes are pushed to `main`.

To build locally on Windows:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller pillow
python build_windows.py
```

Then compile `Setup.iss` using [Inno Setup 6](https://jrsoftware.org/isinfo.php).

## Windows security note

The installer is built for per-user installation and does not request administrator access. Unless a trusted Authenticode signing certificate is configured for the build, Windows SmartScreen may show an unrecognised-app warning. Do not bypass security warnings unless you have verified that the installer came from this official repository.

## Links

- **Repository:** https://github.com/KyZer-HADOC/youtube-video-downloader
- **Latest Windows installer:** https://github.com/KyZer-HADOC/youtube-video-downloader/releases/latest
- **Build status:** https://github.com/KyZer-HADOC/youtube-video-downloader/actions

## Responsible use

Respect creators' rights, privacy, copyright law and each source platform's terms of service.
