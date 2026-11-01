"""yt-dlp download engine used by KyZer Downloader."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable


class YouTubeDownloader:
    """Wrapper around yt-dlp with GUI-friendly progress callbacks."""

    def __init__(self, output_dir: str | Path = "videos") -> None:
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _format_speed(speed: Any) -> str | None:
        try:
            value = float(speed)
        except (TypeError, ValueError):
            return None
        if value >= 1024 * 1024:
            return f"{value / (1024 * 1024):.1f} MB/s"
        if value >= 1024:
            return f"{value / 1024:.0f} KB/s"
        return f"{value:.0f} B/s"

    @staticmethod
    def _format_eta(seconds: Any) -> str | None:
        try:
            total = max(0, int(float(seconds)))
        except (TypeError, ValueError):
            return None
        minutes, secs = divmod(total, 60)
        return f"{minutes}m {secs}s" if minutes else f"{secs}s"

    def download_video(
        self,
        url: str,
        format_type: str = "best",
        audio_only: bool = False,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> bool:
        try:
            import yt_dlp
        except ImportError as exc:
            raise RuntimeError(
                "yt-dlp is not installed. Run: python -m pip install -r requirements.txt"
            ) from exc

        chosen_format = (format_type or "best").lower()
        audio_only = audio_only or chosen_format in ("mp3", "audio")
        height_limit = {"1080p": 1080, "720p": 720, "480p": 480}.get(chosen_format)
        ffmpeg_path = shutil.which("ffmpeg")

        if audio_only and not ffmpeg_path:
            raise RuntimeError(
                "FFmpeg is required for MP3 conversion. Install FFmpeg, add it to PATH, "
                "and restart KyZer Downloader."
            )

        if audio_only:
            format_selector = "bestaudio/best"
            postprocessors = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        elif ffmpeg_path:
            if height_limit:
                format_selector = (
                    f"bv*[height<={height_limit}]+ba/"
                    f"b[height<={height_limit}]/b"
                )
            else:
                format_selector = "bv*+ba/b"
            postprocessors = []
        else:
            # Single-file fallback avoids a merge requirement when FFmpeg is unavailable.
            limit = height_limit or 1080
            format_selector = f"best[height<={limit}]/best"
            postprocessors = []

        def progress_hook(data: dict) -> None:
            if progress_callback is None:
                return
            status = data.get("status")
            if status == "downloading":
                downloaded = data.get("downloaded_bytes") or 0
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                percent = 0.0
                if total:
                    try:
                        percent = float(downloaded) * 100 / float(total)
                    except (TypeError, ValueError, ZeroDivisionError):
                        percent = 0.0
                else:
                    raw = str(data.get("_percent_str", "")).replace("%", "").strip()
                    try:
                        percent = float(raw)
                    except ValueError:
                        percent = 0.0
                progress_callback({
                    "status": "downloading",
                    "percent": max(0.0, min(100.0, percent)),
                    "speed": self._format_speed(data.get("speed")),
                    "eta": self._format_eta(data.get("eta")),
                })
            elif status == "finished":
                progress_callback({"status": "processing", "percent": 100.0})

        options = {
            "format": format_selector,
            "outtmpl": str(self.output_dir / "%(title)s [%(id)s].%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": False,
            "noprogress": True,
            "windowsfilenames": True,
            "continuedl": True,
            "retries": 5,
            "fragment_retries": 5,
            "socket_timeout": 30,
            "progress_hooks": [progress_hook],
            "postprocessors": postprocessors,
        }
        if ffmpeg_path:
            options["ffmpeg_location"] = ffmpeg_path
        if not audio_only and ffmpeg_path:
            options["merge_output_format"] = "mp4"

        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.download([url])
        if result != 0:
            raise RuntimeError(
                "yt-dlp could not complete this download. The video may be private, "
                "unavailable, age-restricted, or temporarily blocked."
            )
        return True
