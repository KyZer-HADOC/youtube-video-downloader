# KyZer YouBe — Windows Setup

## Download and install

1. Open the repository's Releases page.
2. Download KyZer-YouBe-Setup.exe.
3. Run the installer. It installs to your Windows user profile and does not require administrator access.
4. Use the Start Menu shortcut or optional desktop shortcut.

## Downloader

Paste a YouTube, TikTok or Facebook link and press Get Video Info. When the source provides a thumbnail and direct preview stream, the app loads those details. Press Play to attempt playback in the preview panel.

Tick Download Video, Download Audio, or both. Set video resolution and audio bitrate independently, select the save folder, then download. You can set clip Start and End points before downloading.

## Other DL

Open the Other DL tab for links from additional websites. Paste an HTTP or HTTPS page/video URL and press Get Video Info. Choose video/audio and quality, then Download Now. This uses yt-dlp's supported site extractors and generic webpage fallback. Many websites work, but DRM, private, encrypted, login-only and unsupported players may not.

## Download Later

Use Save for Later from Downloader or Other DL, or paste a URL into the Download Later tab. Saved links stay available after closing the app. Select one or more links and press Download Selected, or choose Download All. Successfully downloaded links are removed automatically.

## TikTok / HTTP 429

TikTok may temporarily block requests or require a signed-in browser session:
1. Open the same post in your browser and complete any verification challenge.
2. In KyZer YouBe open Settings, then Browser Session.
3. Select the browser you used. The app only reads its cookies when you explicitly select it.
4. Retry Get Video Info. If HTTP 429 continues, wait before trying again; the source service is rate-limiting your IP/session.

Subtitle download is optional. A subtitle endpoint rate-limit should not cancel a successful video download, though the source can still block the main media request.

## Diagnostic log

KyZer YouBe writes a rotating diagnostic log to:

%LOCALAPPDATA%\KyZer YouBe\log.txt

Open Settings → Open log.txt to view the exact extractor or download error. The log remains on this PC.

## WhatsApp Desktop

KyZer YouBe checks whether WhatsApp Desktop is installed on the PC. If it is not found, the app says WhatsApp for PC is needed and shows its official download page. WhatsApp Desktop does not provide a public status-download API. Automatic scanning is possible only when a real local status-media folder is exposed or exported.

## Troubleshooting

- **Thumbnail not shown:** the source may not expose a usable image URL or may block image requests.
- **Preview does not play:** some streams cannot be played by the embedded Windows media backend. Use Open on Platform for the browser.
- **Other DL fails:** the site may not be supported, the player may use DRM/encryption, or the page may require a login or verification.
- **SmartScreen warning:** an unsigned or newly signed app can still be unrecognized. A trusted signing certificate is required for a verified publisher; reputation warnings cannot be disabled by app settings.

## Project

https://github.com/KyZer-HADOC/youtube-video-downloader
