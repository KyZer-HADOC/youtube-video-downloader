"""Download and media-information layer for KyZer YouBe.

Uses yt-dlp for public YouTube, TikTok and Facebook URLs. WhatsApp Status
media is handled as local files made available on this PC by the user.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


class DownloadCancelled(Exception):
    """Raised when the user cancels an active transfer."""


PLATFORM_HOSTS = {
    "YouTube": ("youtube.com", "youtu.be"),
    "TikTok": ("tiktok.com",),
    "Facebook": ("facebook.com", "fb.watch"),
}


def get_app_logger() -> logging.Logger:
    """Return the shared rotating diagnostic logger."""
    logger = logging.getLogger("kyzer_yoube")
    if not logger.handlers:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        folder = base / "KyZer YouBe"
        folder.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            folder / "log.txt",
            maxBytes=5 * 1024 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(threadName)s | %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger


class _YtDlpLogger:
    """Forward yt-dlp diagnostics into KyZer YouBe's log.txt."""

    def debug(self, message: str) -> None:
        get_app_logger().debug("yt-dlp: %s", message)

    def warning(self, message: str) -> None:
        get_app_logger().warning("yt-dlp: %s", message)

    def error(self, message: str) -> None:
        get_app_logger().error("yt-dlp: %s", message)


def _safe_url_label(url: str) -> str:
    try:
        parsed = urlsplit(url)
        return "{}{}".format(parsed.netloc, parsed.path[:100])
    except Exception:
        return "<invalid URL>"


def _browser_cookie_option(browser: str | None) -> dict[str, Any]:
    """Only read browser cookies when the user explicitly selected a browser."""
    name = (browser or "").strip().lower()
    if name in ("none", "off", "disabled", ""):
        return {}
    allowed = {"chrome", "edge", "firefox", "brave", "opera", "vivaldi"}
    if name not in allowed:
        return {}
    return {"cookiesfrombrowser": (name,)}


def detect_platform(url: str) -> str:
    """Return the supported platform name, or 'Unsupported'."""
    try:
        host = (urlsplit(url.strip()).hostname or "").lower()
    except ValueError:
        return "Unsupported"

    for platform, domains in PLATFORM_HOSTS.items():
        if any(host == domain or host.endswith("." + domain) for domain in domains):
            return platform
    return "Unsupported"


def is_http_url(url: str) -> bool:
    """Accept a syntactically valid HTTP(S) URL for generic website extraction."""
    try:
        parsed = urlsplit(url.strip())
        return (
            parsed.scheme.lower() in ("http", "https")
            and bool(parsed.hostname)
            and not any(char.isspace() for char in url.strip())
        )
    except (ValueError, TypeError):
        return False


def is_supported_url(url: str) -> bool:
    return is_http_url(url) and detect_platform(url) != "Unsupported"


def format_bytes(value: Any) -> str:
    try:
        amount = max(0.0, float(value))
    except (TypeError, ValueError):
        return "Unknown"
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return "{:.1f} {}".format(amount, unit)
        amount /= 1024
    return "Unknown"


def format_duration(value: Any) -> str:
    try:
        seconds = max(0, int(float(value)))
    except (TypeError, ValueError):
        return "--:--"
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, secs)
    return "{:02d}:{:02d}".format(minutes, secs)


class YouTubeDownloader:
    """yt-dlp wrapper shared by the GUI workers."""

    def __init__(self, output_dir: str | Path = "downloads") -> None:
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def ffmpeg_path() -> str | None:
        """Prefer the FFmpeg binary bundled by imageio-ffmpeg."""
        try:
            import imageio_ffmpeg
            candidate = imageio_ffmpeg.get_ffmpeg_exe()
            if candidate and Path(candidate).exists():
                return candidate
        except Exception:
            get_app_logger().exception("Could not locate bundled FFmpeg")
        return shutil.which("ffmpeg")

    @staticmethod
    def fetch_thumbnail(info: dict[str, Any]) -> bytes | None:
        """Fetch a thumbnail with source-page headers and a browser-like User-Agent."""
        candidates = info.get("thumbnail_candidates") or []
        if not candidates and info.get("thumbnail"):
            candidates = [{"url": info["thumbnail"], "http_headers": {}}]

        for candidate in candidates:
            image_url = candidate.get("url")
            if not image_url:
                continue
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0.0.0 Safari/537.36"
                ),
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": info.get("webpage_url") or "",
            }
            headers.update(candidate.get("http_headers") or {})
            try:
                request = urllib.request.Request(image_url, headers=headers)
                with urllib.request.urlopen(request, timeout=15) as response:
                    data = response.read(8 * 1024 * 1024 + 1)
                if data and len(data) <= 8 * 1024 * 1024:
                    get_app_logger().info(
                        "Loaded thumbnail (%s bytes) for %s",
                        len(data), _safe_url_label(info.get("webpage_url", "")),
                    )
                    return data
            except Exception as exc:
                get_app_logger().warning("Thumbnail request failed: %s", exc)
        return None

    def get_video_info(
        self,
        url: str,
        cookies_browser: str | None = None,
        allow_generic: bool = False,
    ) -> dict[str, Any]:
        """Fetch metadata for supported platforms or an arbitrary HTTP(S) page."""
        valid = is_supported_url(url) or (allow_generic and is_http_url(url))
        if not valid:
            raise ValueError(
                "Enter a valid HTTP or HTTPS video/page link. "
                "Use Other DL for sites outside YouTube, TikTok and Facebook."
            )

        try:
            import yt_dlp
        except ImportError as exc:
            raise RuntimeError("The yt-dlp engine is missing. Reinstall KyZer YouBe.") from exc

        platform = detect_platform(url)
        if platform == "Unsupported" and allow_generic:
            platform = "Other Website"
        get_app_logger().info(
            "Fetching video information: platform=%s url=%s browser_cookies=%s",
            platform, _safe_url_label(url), cookies_browser or "off",
        )
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": False,
            "logger": _YtDlpLogger(),
            "skip_download": True,
            "noplaylist": True,
            "ignoreerrors": False,
            "socket_timeout": 35,
            "extract_flat": False,
            # Slow down metadata requests to reduce platform-side rate limiting.
            "retries": 8,
            "extractor_retries": 8,
            "sleep_interval_requests": 3.0,
            "sleep_interval": 5.0,
            "max_sleep_interval": 10.0,
            "retry_sleep": {
                "http": "linear=5::5",
                "extractor": "linear=3::3",
                "fragment": "linear=3::3",
            },
            "verbose": True,
        }
        options.update(_browser_cookie_option(cookies_browser))

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            get_app_logger().exception(
                "Video info extraction failed: platform=%s url=%s",
                platform, _safe_url_label(url),
            )
            message = str(exc)
            if "429" in message or "Too Many Requests" in message:
                raise RuntimeError(
                    "The platform is rate-limiting requests (HTTP 429). Wait a while and retry. "
                    "For a CAPTCHA/verification block, open the post in your browser, solve it, "
                    "then select that browser under Settings > Browser cookies and retry. "
                    "The same network/IP must be used. See log.txt for technical details.\n\n"
                    + message
                ) from exc
            raise RuntimeError(
                "Could not read this post. It may be private, unavailable, or temporarily blocked. "
                "Update the app and check log.txt for the exact extractor error.\n\n" + message
            ) from exc

        if not info:
            raise RuntimeError("The platform did not return video information.")
        if info.get("_type") == "playlist" or info.get("entries"):
            first = next((entry for entry in info.get("entries", []) if entry), None)
            if not first:
                raise RuntimeError("No playable videos were found in this playlist.")
            info = first
            if not info.get("title"):
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(info.get("url") or url, download=False)

        formats = info.get("formats") or []
        video_formats = [
            item for item in formats
            if item.get("url")
            and item.get("vcodec") not in (None, "none")
            and not item.get("has_drm")
        ]
        progressive = [
            item for item in video_formats
            if item.get("acodec") not in (None, "none")
        ]
        preview_candidates = progressive or video_formats
        preview_candidates.sort(
            key=lambda item: (
                int(item.get("height") or 0),
                float(item.get("tbr") or 0),
            )
        )
        preview = preview_candidates[-1] if preview_candidates else None

        thumbnails = info.get("thumbnails") or []
        thumbnails = sorted(
            (item for item in thumbnails if item.get("url")),
            key=lambda item: (
                int(item.get("width") or 0) * int(item.get("height") or 0),
                int(item.get("preference") or 0),
            ),
            reverse=True,
        )
        thumbnail_url = str(info.get("thumbnail") or "")
        if thumbnail_url and all(item.get("url") != thumbnail_url for item in thumbnails):
            thumbnails.insert(0, {"url": thumbnail_url, "http_headers": {}})

        size = info.get("filesize") or info.get("filesize_approx")
        if not size and preview:
            size = preview.get("filesize") or preview.get("filesize_approx")

        get_app_logger().info(
            "Video info loaded: platform=%s title=%r formats=%d thumbnail_candidates=%d preview=%s",
            platform, str(info.get("title") or "")[:100], len(formats),
            len(thumbnails), bool(preview),
        )
        return {
            "id": str(info.get("id") or ""),
            "title": str(info.get("title") or "Untitled video"),
            "uploader": str(info.get("uploader") or info.get("channel") or "Unknown creator"),
            "duration": info.get("duration"),
            "duration_text": format_duration(info.get("duration")),
            "view_count": info.get("view_count"),
            "description": str(info.get("description") or "")[:3000],
            "thumbnail": thumbnail_url or (thumbnails[0].get("url") if thumbnails else ""),
            "thumbnail_candidates": thumbnails,
            "webpage_url": str(info.get("webpage_url") or url),
            "platform": platform,
            "filesize": size,
            "filesize_text": format_bytes(size),
            "width": (preview or {}).get("width") or info.get("width"),
            "height": (preview or {}).get("height") or info.get("height"),
            "preview_url": (preview or {}).get("url"),
            "preview_headers": (preview or {}).get("http_headers") or info.get("http_headers") or {},
        }

    def download_video(
        self,
        url: str,
        quality: str = "best",
        output_template: str | None = None,
        audio_only: bool = False,
        audio_quality: str = "192",
        download_subtitles: bool = False,
        embed_thumbnail: bool = False,
        allow_playlist: bool = False,
        section: tuple[float, float] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        cancel_event: Any = None,
        cookies_browser: str | None = None,
        allow_generic: bool = False,
    ) -> str:
        """Download supported platforms or a generic HTTP(S) page if enabled."""
        valid = is_supported_url(url) or (allow_generic and is_http_url(url))
        if not valid:
            raise ValueError(
                "Enter a valid HTTP or HTTPS video/page link. "
                "Use Other DL for websites outside YouTube, TikTok and Facebook."
            )

        try:
            import yt_dlp
        except ImportError as exc:
            raise RuntimeError("The yt-dlp engine is missing. Reinstall KyZer YouBe.") from exc

        ffmpeg = self.ffmpeg_path()
        quality = (quality or "best").lower()
        max_height = {
            "2160p": 2160, "1440p": 1440, "1080p": 1080,
            "720p": 720, "480p": 480, "360p": 360,
        }.get(quality)

        if audio_only or quality == "audio":
            if not ffmpeg:
                raise RuntimeError("The bundled FFmpeg engine could not be found.")
            format_selector = "bestaudio/best"
            postprocessors = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(audio_quality or "192").replace(" kbps", ""),
            }]
        else:
            postprocessors = []
            if max_height:
                format_selector = (
                    "bv*[height<={0}]+ba/b[height<={0}]/"
                    "bv*[height<={0}]/b".format(max_height)
                )
            else:
                format_selector = "bv*+ba/b"

        existing_files = {
            path.resolve() for path in self.output_dir.rglob("*") if path.is_file()
        }
        template = output_template or str(
            self.output_dir / "%(title).180B [%(id)s].%(ext)s"
        )
        options: dict[str, Any] = {
            "format": format_selector,
            "outtmpl": template,
            "noplaylist": not allow_playlist,
            "quiet": True,
            "no_warnings": False,
            "logger": _YtDlpLogger(),
            "noprogress": True,
            "windowsfilenames": True,
            "continuedl": True,
            "overwrites": False,
            "retries": 8,
            "fragment_retries": 8,
            "extractor_retries": 8,
            # Be gentle with subtitle and metadata endpoints; aggressive retries worsen 429 blocks.
            "sleep_interval_requests": 3.0,
            "sleep_interval": 5.0,
            "max_sleep_interval": 10.0,
            "retry_sleep": {
                "http": "linear=5::5",
                "extractor": "linear=3::3",
                "fragment": "linear=3::3",
            },
            "socket_timeout": 35,
            "merge_output_format": "mp4",
            "postprocessors": postprocessors,
        }
        options.update(_browser_cookie_option(cookies_browser))

        if ffmpeg:
            options["ffmpeg_location"] = ffmpeg

        if download_subtitles:
            # Captions are optional; a subtitle endpoint returning HTTP 429
            # must not cancel an otherwise successful video/audio download.
            options["ignoreerrors"] = True
            options.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en.*", "si.*"],
                "subtitlesformat": "srt/best",
                "embedsubtitles": True,
                "sleep_interval_subtitles": 20.0,
                "skip_unavailable_fragments": True,
            })

        if embed_thumbnail:
            options["writethumbnail"] = True
            options["postprocessors"].append({
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False,
            })

        if section is not None:
            start, end = float(section[0]), float(section[1])
            if start < 0 or end <= start:
                raise ValueError("The clip end time must be after its start time.")
            options["download_ranges"] = (
                lambda _info, _ydl: [{"start_time": start, "end_time": end}]
            )
            options["force_keyframes_at_cuts"] = True

        def progress_hook(data: dict[str, Any]) -> None:
            if cancel_event is not None and cancel_event.is_set():
                raise DownloadCancelled("Download cancelled by user.")

            if not progress_callback:
                return

            status = data.get("status")
            if status == "downloading":
                downloaded = data.get("downloaded_bytes") or 0
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                try:
                    downloaded_num = int(downloaded)
                    total_num = int(total) if total else 0
                except (TypeError, ValueError):
                    downloaded_num, total_num = 0, 0

                percent = (downloaded_num * 100 / total_num) if total_num else 0.0
                speed = data.get("speed")
                eta = data.get("eta")
                remaining = max(0, total_num - downloaded_num) if total_num else None
                progress_callback({
                    "status": "downloading",
                    "percent": max(0.0, min(100.0, percent)),
                    "downloaded": downloaded_num,
                    "total": total_num or None,
                    "remaining": remaining,
                    "downloaded_text": format_bytes(downloaded_num),
                    "total_text": format_bytes(total_num) if total_num else "Estimating…",
                    "remaining_text": format_bytes(remaining) if remaining is not None else "Estimating…",
                    "speed_text": format_bytes(speed) + "/s" if speed else "—",
                    "eta_text": format_duration(eta) if eta is not None else "—",
                })
            elif status == "finished":
                progress_callback({
                    "status": "processing",
                    "percent": 100.0,
                    "downloaded_text": "Download received",
                    "total_text": "Processing media…",
                    "remaining_text": "—",
                    "speed_text": "—",
                    "eta_text": "—",
                })

        options["progress_hooks"] = [progress_hook]
        platform = detect_platform(url)
        if platform == "Unsupported" and allow_generic:
            platform = "Other Website"
        get_app_logger().info(
            "Starting download: platform=%s url=%s audio_only=%s subtitles=%s cookies=%s",
            platform, _safe_url_label(url), audio_only,
            download_subtitles, cookies_browser or "off",
        )
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                result = ydl.download([url])
        except DownloadCancelled:
            raise
        except Exception:
            get_app_logger().exception(
                "Download failed: platform=%s url=%s", detect_platform(url), _safe_url_label(url)
            )
            raise

        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelled("Download cancelled by user.")
        if result != 0:
            raise RuntimeError(
                "The platform could not complete this download. The post may be private, "
                "unavailable, region-restricted, or temporarily blocked. "
                "Check log.txt for the exact error."
            )

        candidates = sorted(
            (
                path for path in self.output_dir.rglob("*")
                if path.is_file() and path.resolve() not in existing_files
                and not path.name.endswith((".part", ".ytdl"))
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return str(candidates[0])
        raise RuntimeError("yt-dlp finished but no new output file was found in the save folder.")
