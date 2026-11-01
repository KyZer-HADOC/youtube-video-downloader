from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PNG_ICON = ROOT / "KyZer YouBe.png"
ICO_ICON = ROOT / "KyZer YouBe.ico"


def create_windows_icon() -> None:
    if not PNG_ICON.is_file():
        raise FileNotFoundError("The root icon image 'KyZer YouBe.png' is missing.")
    image = Image.open(PNG_ICON).convert("RGBA")
    image.save(
        ICO_ICON,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def main() -> int:
    create_windows_icon()
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed", "--onedir",
        "--name", "KyZer YouBe",
        "--icon", str(ICO_ICON),
        "--add-data", "{};.".format(PNG_ICON),
        # yt-dlp loads extractors dynamically, so keep its extractor package.
        "--collect-all", "yt_dlp",
        # Collect only the FFmpeg binary/package resources, not unrelated Qt modules.
        "--collect-binaries", "imageio_ffmpeg",
        "--hidden-import", "PySide6.QtMultimedia",
        "--hidden-import", "PySide6.QtMultimediaWidgets",
        "--hidden-import", "certifi",
        str(ROOT / "app.py"),
    ]
    print("Building size-optimised KyZer YouBe for Windows…", flush=True)
    completed = subprocess.run(args, cwd=ROOT, check=False)
    if completed.returncode != 0:
        return completed.returncode
    expected = ROOT / "dist" / "KyZer YouBe" / "KyZer YouBe.exe"
    if not expected.is_file():
        raise FileNotFoundError("PyInstaller finished without creating {}".format(expected))
    print("Build ready: {}".format(expected), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
