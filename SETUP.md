# KyZer YouBe — Windows Setup

## Download and install

1. Open the repository's Releases page.
2. Download KyZer-YouBe-Setup.exe.
3. Run the installer. It installs to your Windows user profile and does not require administrator access.
4. Use the Start Menu shortcut, or the optional desktop shortcut.

## First launch

- Open Downloader.
- Paste a YouTube, TikTok or Facebook link.
- Press Get Video Info to fetch title, creator, duration and available preview information.
- Press Play to attempt the in-app preview, or Open on Platform if the source requires its website player.
- Set Start and End to clip a section, choose quality and save folder, then download.

## WhatsApp Status Saver

Copy status media that you can access on your own Android device to a local folder on your PC. Choose that folder in the WhatsApp Status page and scan it. WhatsApp does not provide a public desktop status-download link; the app does not request account credentials or session cookies.

## Troubleshooting

- Video preview does not play: some platforms use stream formats or request headers that the embedded player cannot play. Choose Open on Platform to watch it in the normal browser. Download support is separate from preview support.
- A link fails: the post may be private, login-only, age-restricted, region-restricted, removed, or not currently supported by yt-dlp. Update the app when a new release is available.
- Windows SmartScreen warning: the installer is per-user and built from the public repository, but an unsigned or newly signed app can still be reported as unrecognized. Verify the publisher and download source before running. A trusted code-signing certificate is required to display a verified publisher; reputation warnings cannot be disabled from inside the app.

## Project

Source code and release builds are available at:
https://github.com/KyZer-HADOC/youtube-video-downloader
