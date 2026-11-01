"""Download and media-information layer for KyZer YouBe.

Uses yt-dlp for public YouTube, TikTok and Facebook URLs. WhatsApp Status
media is handled as local files exported/copied from the user's own device.
"""

from __future__ import annotations

import os
import shutil
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


def is_supported_url(url: str) -> bool:
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and detect_platform(url) != "Unsupported"


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
            pass
        return shutil.which("ffmpeg")

    def get_video_info(self, url: str) -> dict[str, Any]:
        """Fetch metadata and a direct progressive URL for optional streaming preview."""
        if not is_supported_url(url):
            raise ValueError("This link is not a supported YouTube, TikTok or Facebook URL.")

        try:
            import yt_dlp
        except ImportError as exc:
            raise RuntimeError("The yt-dlp engine is missing. Reinstall KyZer YouBe.") from exc

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "ignoreerrors": False,
            "socket_timeout": 25,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise RuntimeError("The platform did not return video information.")
        if info.get("_type") == "playlist" or info.get("entries"):
            first = next((entry for entry in info.get("entries", []) if entry), None)
            if not first:
                raise RuntimeError("No playable videos were found in this playlist.")
            info = first
            if not info.get("title"):
                info = ydl.extract_info(info.get("url") or url, download=False)

        formats = info.get("formats") or []
        progressive = [
            item for item in formats
            if item.get("url")
            and item.get("vcodec") not in (None, "none")
            and item.get("acodec") not in (None, "none")
            and not item.get("has_drm")
        ]
        progressive.sort(
            key=lambda item: (
                int(item.get("height") or 0),
                float(item.get("tbr") or 0),
            )
        )
        preview = progressive[-1] if progressive else None
        size = info.get("filesize") or info.get("filesize_approx")
        if not size and preview:
            size = preview.get("filesize") or preview.get("filesize_approx")

        return {
            "id": str(info.get("id") or ""),
            "title": str(info.get("title") or "Untitled video"),
            "uploader": str(info.get("uploader") or info.get("channel") or "Unknown creator"),
            "duration": info.get("duration"),
            "duration_text": format_duration(info.get("duration")),
            "view_count": info.get("view_count"),
            "description": str(info.get("description") or "")[:3000],
            "thumbnail": str(info.get("thumbnail") or ""),
            "webpage_url": str(info.get("webpage_url") or url),
            "platform": detect_platform(url),
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
        download_subtitles: bool = False,
        embed_thumbnail: bool = False,
        allow_playlist: bool = False,
        section: tuple[float, float] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        cancel_event: Any = None,
    ) -> str:
        """Download a supported URL, optionally cutting a selected time range."""
        if not is_supported_url(url):
            raise ValueError("This link is not a supported YouTube, TikTok or Facebook URL.")

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
                "preferredquality": "192",
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
            "noprogress": True,
            "windowsfilenames": True,
            "continuedl": True,
            "overwrites": False,
            "retries": 5,
            "fragment_retries": 5,
            "socket_timeout": 30,
            "merge_output_format": "mp4",
            "postprocessors": postprocessors,
        }

        if ffmpeg:
            options["ffmpeg_location"] = ffmpeg

        if download_subtitles:
            options.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en.*", "si.*"],
                "subtitlesformat": "srt/best",
                "embedsubtitles": True,
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

        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.download([url])

        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelled("Download cancelled by user.")
        if result != 0:
            raise RuntimeError(
                "The platform could not complete this download. The post may be private, "
                "unavailable, region-restricted, or temporarily blocked."
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
