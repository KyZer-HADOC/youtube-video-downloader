#!/usr/bin/env python3
"""KyZer YouBe - feature-rich multi-platform video downloader."""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from downloader import (
    DownloadCancelled,
    YouTubeDownloader,
    detect_platform,
    format_duration,
    is_supported_url,
    get_app_logger,
)


APP_NAME = "KyZer YouBe"
BG = "#0b0d12"
SURFACE = "#131720"
CARD = "#171d28"
CARD_ALT = "#1c2431"
BORDER = "#283242"
TEXT = "#f3f5f8"
MUTED = "#929eae"
RED = "#f04458"
RED_HOVER = "#ff6071"
GREEN = "#45d49a"
BLUE = "#67b7ff"


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base) / relative)


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    folder = Path(base) / APP_NAME if base else Path.home() / ".kyzer_yoube"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def pretty_count(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "—"
    return "{:,}".format(number)


def make_card(parent: QWidget | None = None, padding: int = 16) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(parent)
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setSpacing(12)
    return frame, layout


class InfoWorker(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, url: str, cookies_browser: str | None = None) -> None:
        super().__init__()
        self.url = url
        self.cookies_browser = cookies_browser

    def run(self) -> None:
        try:
            engine = YouTubeDownloader()
            info = engine.get_video_info(self.url, cookies_browser=self.cookies_browser)
            info["thumbnail_data"] = engine.fetch_thumbnail(info)
            self.succeeded.emit(info)
        except Exception as exc:
            get_app_logger().exception("Get Video Info worker failed")
            self.failed.emit(str(exc))


class DownloadWorker(QThread):
    progress = Signal(dict)
    succeeded = Signal(list)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        urls: list[str],
        output_dir: str,
        download_video: bool,
        download_audio: bool,
        video_quality: str,
        audio_quality: str,
        subtitles: bool,
        thumbnail: bool,
        playlist: bool,
        section: tuple[float, float] | None,
        cookies_browser: str | None,
    ) -> None:
        super().__init__()
        self.urls = urls
        self.output_dir = output_dir
        self.download_video = download_video
        self.download_audio = download_audio
        self.video_quality = video_quality
        self.audio_quality = audio_quality
        self.subtitles = subtitles
        self.thumbnail = thumbnail
        self.playlist = playlist
        self.section = section
        self.cookies_browser = cookies_browser
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            engine = YouTubeDownloader(self.output_dir)
            results = []
            total = len(self.urls)
            for index, url in enumerate(self.urls, start=1):
                tasks = []
                if self.download_video:
                    tasks.append(("VIDEO", self.video_quality, False))
                if self.download_audio:
                    tasks.append(("AUDIO", "audio", True))

                for media_kind, quality, audio_only in tasks:
                    if self.cancel_event.is_set():
                        raise DownloadCancelled("Download queue cancelled by user.")

                    def report_progress(data: dict[str, Any]) -> None:
                        payload = dict(data)
                        payload["queue_index"] = index
                        payload["queue_total"] = total
                        payload["media_kind"] = media_kind
                        self.progress.emit(payload)

                    path = engine.download_video(
                        url,
                        quality=quality,
                        audio_only=audio_only,
                        audio_quality=self.audio_quality,
                        download_subtitles=self.subtitles and media_kind == "VIDEO",
                        embed_thumbnail=self.thumbnail and media_kind == "VIDEO",
                        allow_playlist=self.playlist,
                        section=self.section,
                        progress_callback=report_progress,
                        cancel_event=self.cancel_event,
                        cookies_browser=self.cookies_browser,
                    )
                    results.append({"path": path, "url": url, "kind": media_kind})

            if self.cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.succeeded.emit(results)
        except DownloadCancelled:
            self.cancelled.emit()
        except Exception as exc:
            get_app_logger().exception("Download worker failed")
            self.failed.emit(str(exc))


class KyZerYouBe(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        icon_path = resource_path("KyZer YouBe.png")
        if Path(icon_path).exists():
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1320, 900)
        self.setMinimumSize(980, 720)

        self.info: dict[str, Any] | None = None
        self.info_worker: InfoWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.queue_urls: list[str] = []
        self.history_file = app_data_dir() / "history.json"
        self.history: list[dict[str, str]] = self._load_history()
        self.output_dir = str(Path.home() / "Downloads" / "KyZer YouBe")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self.status_folder = ""
        self.whatsapp_installed = False

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.8)
        self.player.setAudioOutput(self.audio_output)
        self.player.durationChanged.connect(self._duration_changed)
        self.player.positionChanged.connect(self._position_changed)
        self.player.errorOccurred.connect(self._player_error)
        self.player.playbackStateChanged.connect(self._playback_state_changed)

        self._build_shell()
        self._show_page(0)
        self._refresh_history()
        self._detect_whatsapp_desktop(auto_scan=True)

    def _load_history(self) -> list[dict[str, str]]:
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save_history(self, title: str, path: str, url: str) -> None:
        self.history.insert(0, {
            "title": title,
            "path": path,
            "url": url,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        self.history = self.history[:100]
        try:
            self.history_file.write_text(
                json.dumps(self.history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
        self._refresh_history()

    def _build_shell(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(84)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 10, 28, 10)
        header_layout.setSpacing(14)

        logo = QLabel()
        logo.setFixedSize(58, 58)
        pixmap = QPixmap(icon_path := resource_path("KyZer YouBe.png"))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(
                58, 58, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        header_layout.addWidget(logo)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(1)
        brand_name = QLabel("KyZer <span style='color:#f04458'>YouBe</span>")
        brand_name.setObjectName("BrandName")
        brand_name.setTextFormat(Qt.RichText)
        sub = QLabel("ALL-IN-ONE MEDIA DOWNLOADER")
        sub.setObjectName("BrandSub")
        brand_box.addWidget(brand_name)
        brand_box.addWidget(sub)
        header_layout.addLayout(brand_box)
        header_layout.addStretch(1)

        self.header_status = QLabel("●  ALL SYSTEMS READY")
        self.header_status.setObjectName("HeaderStatus")
        header_layout.addWidget(self.header_status)
        outer.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(205)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(13, 22, 13, 15)
        side_layout.setSpacing(8)

        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("⌂", "Downloader"),
            ("◉", "WhatsApp Status"),
            ("◷", "Download History"),
            ("⚙", "Settings"),
        ]
        for index, (symbol, title) in enumerate(nav_items):
            button = QPushButton("{}   {}".format(symbol, title))
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, i=index: self._show_page(i))
            side_layout.addWidget(button)
            self.nav_buttons.append(button)

        side_layout.addStretch(1)
        side_note = QLabel("MADE BY\nKyZer_HADOC")
        side_note.setObjectName("SideNote")
        side_layout.addWidget(side_note)
        body.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_downloader_page())
        self.pages.addWidget(self._build_whatsapp_page())
        self.pages.addWidget(self._build_history_page())
        self.pages.addWidget(self._build_settings_page())
        body.addWidget(self.pages, 1)

        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self) -> str:
        return """
        QWidget#Root { background: #0b0d12; color: #f3f5f8; font-family: 'Segoe UI'; }
        QFrame#Header { background: #111720; border-bottom: 1px solid #283242; }
        QLabel#BrandName { color: #f3f5f8; font-size: 25px; font-weight: 800; }
        QLabel#BrandSub { color: #f04458; font-size: 9px; font-weight: 800; letter-spacing: 2px; }
        QLabel#HeaderStatus { color: #45d49a; font-size: 10px; font-weight: 700; }
        QFrame#Sidebar { background: #10151d; border-right: 1px solid #283242; }
        QPushButton#NavButton {
            text-align: left; color: #929eae; background: transparent;
            border: 0; border-radius: 10px; padding: 14px 12px;
            font-size: 12px; font-weight: 650;
        }
        QPushButton#NavButton:hover { background: #1c2431; color: #ffffff; }
        QPushButton#NavButton:checked {
            color: #ffffff; background: #321b25; border-left: 3px solid #f04458;
        }
        QLabel#SideNote { color: #637083; font-size: 9px; line-height: 1.5; padding: 12px 8px; }
        QFrame#Card { background: #171d28; border: 1px solid #283242; border-radius: 14px; }
        QLabel#SectionTitle { color: #f3f5f8; font-size: 15px; font-weight: 750; }
        QLabel#Muted { color: #929eae; font-size: 11px; }
        QLabel#FieldLabel { color: #aeb8c6; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
        QLabel#MetaValue { color: #f3f5f8; font-size: 12px; font-weight: 650; }
        QLabel#HeroTitle { color: #ffffff; font-size: 25px; font-weight: 800; }
        QLabel#HeroSub { color: #929eae; font-size: 12px; }
        QLineEdit, QComboBox, QDoubleSpinBox {
            color: #f3f5f8; background: #0f141c; border: 1px solid #303b4c;
            border-radius: 8px; padding: 10px 12px; min-height: 18px;
            selection-background-color: #f04458;
        }
        QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 1px solid #f04458; }
        QComboBox QAbstractItemView {
            background: #171d28; color: #f3f5f8; selection-background-color: #622532;
            border: 1px solid #303b4c;
        }
        QPushButton {
            color: #f3f5f8; background: #222c3b; border: 1px solid #354256;
            border-radius: 8px; padding: 10px 14px; font-size: 11px; font-weight: 700;
        }
        QPushButton:hover { background: #2b3749; border-color: #53647c; }
        QPushButton:disabled { color: #637083; background: #161c25; border-color: #242c39; }
        QPushButton#Primary {
            color: #ffffff; background: #e83e54; border: 1px solid #ff6576;
            padding: 12px 20px; font-size: 12px;
        }
        QPushButton#Primary:hover { background: #ff5369; }
        QPushButton#Danger { color: #ff7d8b; background: #2b1920; border-color: #63303d; }
        QPushButton#Ghost { color: #c4ceda; background: #171d28; border-color: #283242; }
        QCheckBox { color: #b9c3d0; spacing: 8px; font-size: 11px; }
        QCheckBox::indicator { width: 16px; height: 16px; }
        QCheckBox::indicator:unchecked { background: #0f141c; border: 1px solid #48566a; border-radius: 4px; }
        QCheckBox::indicator:checked { background: #e83e54; border: 1px solid #ff6576; border-radius: 4px; }
        QProgressBar {
            color: #ffffff; background: #0d1219; border: 1px solid #2b3544;
            border-radius: 7px; height: 13px; text-align: center;
        }
        QProgressBar::chunk { background: #f04458; border-radius: 6px; }
        QSlider::groove:horizontal { background: #303b4c; height: 5px; border-radius: 2px; }
        QSlider::handle:horizontal { background: #f04458; width: 13px; margin: -5px 0; border-radius: 6px; }
        QListWidget { color: #f3f5f8; background: #10151d; border: 1px solid #283242; border-radius: 9px; padding: 6px; }
        QListWidget::item { padding: 10px; border-bottom: 1px solid #242d3a; }
        QListWidget::item:selected { background: #35202a; }
        QScrollArea { border: 0; background: transparent; }
        QScrollBar:vertical { background: #0b0d12; width: 10px; margin: 2px; }
        QScrollBar::handle:vertical { background: #354256; border-radius: 4px; min-height: 30px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """

    def _scroll_page(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)
        return scroll

    def _page_container(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(16)
        return page, layout

    def _label(self, text: str, name: str = "Muted") -> QLabel:
        label = QLabel(text)
        label.setObjectName(name)
        return label

    def _build_downloader_page(self) -> QWidget:
        page, layout = self._page_container()

        hero = QVBoxLayout()
        hero.setSpacing(5)
        hero.addWidget(self._label("Your media. Your way.", "HeroTitle"))
        hero.addWidget(self._label(
            "Download, preview and clip videos from your favourite platforms.",
            "HeroSub"
        ))
        layout.addLayout(hero)

        url_card, url_layout = make_card(padding=16)
        url_layout.addWidget(self._label("VIDEO OR POST LINK", "FieldLabel"))
        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste a YouTube, TikTok or Facebook link here…")
        self.url_edit.returnPressed.connect(self.get_video_info)
        self.url_edit.textChanged.connect(self._update_platform_badge)
        url_row.addWidget(self.url_edit, 1)
        self.paste_button = QPushButton("▣  Paste")
        self.paste_button.setObjectName("Ghost")
        self.paste_button.clicked.connect(self.paste_url)
        url_row.addWidget(self.paste_button)
        self.info_button = QPushButton("⌕  Get Video Info")
        self.info_button.setObjectName("Primary")
        self.info_button.clicked.connect(self.get_video_info)
        url_row.addWidget(self.info_button)
        url_layout.addLayout(url_row)

        platform_row = QHBoxLayout()
        platform_row.addWidget(self._label("SUPPORTED:", "FieldLabel"))
        self.platform_badges = []
        for name, tone in (("YOUTUBE", RED), ("TIKTOK", TEXT), ("FACEBOOK", BLUE), ("WA STATUS", GREEN)):
            badge = QLabel(name)
            badge.setStyleSheet(
                "color:{}; background:#202938; border:1px solid #344256; "
                "border-radius:9px; padding:5px 9px; font-size:9px; font-weight:800;".format(tone)
            )
            platform_row.addWidget(badge)
            self.platform_badges.append(badge)
        platform_row.addStretch(1)
        url_layout.addLayout(platform_row)
        layout.addWidget(url_card)

        main_row = QHBoxLayout()
        main_row.setSpacing(14)

        preview_card, preview_layout = make_card(padding=13)
        preview_header = QHBoxLayout()
        preview_header.addWidget(self._label("VIDEO PREVIEW", "SectionTitle"))
        preview_header.addStretch(1)
        self.preview_platform = self._label("WAITING FOR LINK", "FieldLabel")
        preview_header.addWidget(self.preview_platform)
        preview_layout.addLayout(preview_header)

        self.preview_stack = QStackedWidget()
        self.preview_stack.setMinimumHeight(260)
        self.preview_stack.setMaximumHeight(370)
        self.preview_placeholder = QLabel(
            "▶\n\nPaste a link and press  GET VIDEO INFO\n\nWatch here without downloading the full video."
        )
        self.preview_placeholder.setAlignment(Qt.AlignCenter)
        self.preview_placeholder.setStyleSheet(
            "background:#080b10; color:#8390a1; border:1px dashed #354256; "
            "border-radius:10px; font-size:12px;"
        )
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background:#05070a; border-radius:10px;")
        self.preview_stack.addWidget(self.preview_placeholder)
        self.preview_stack.addWidget(self.video_widget)
        preview_layout.addWidget(self.preview_stack, 1)
        self.player.setVideoOutput(self.video_widget)

        player_controls = QHBoxLayout()
        self.play_button = QPushButton("▶  Play")
        self.play_button.clicked.connect(self.toggle_playback)
        player_controls.addWidget(self.play_button)
        self.browser_button = QPushButton("Open on Platform")
        self.browser_button.setObjectName("Ghost")
        self.browser_button.clicked.connect(self.open_source)
        player_controls.addWidget(self.browser_button)
        player_controls.addStretch(1)
        self.playback_time = self._label("00:00 / 00:00")
        player_controls.addWidget(self.playback_time)
        preview_layout.addLayout(player_controls)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderMoved.connect(self._seek_preview)
        preview_layout.addWidget(self.seek_slider)
        main_row.addWidget(preview_card, 7)

        details_card, details_layout = make_card(padding=16)
        details_layout.addWidget(self._label("VIDEO INFORMATION", "SectionTitle"))
        self.thumbnail_preview = QLabel("Thumbnail will appear here")
        self.thumbnail_preview.setAlignment(Qt.AlignCenter)
        self.thumbnail_preview.setMinimumSize(220, 120)
        self.thumbnail_preview.setMaximumHeight(150)
        self.thumbnail_preview.setStyleSheet(
            "background:#0b1018; color:#758398; border:1px dashed #354256; border-radius:9px;"
        )
        details_layout.addWidget(self.thumbnail_preview)
        self.video_title = self._label("No video selected", "MetaValue")
        self.video_title.setWordWrap(True)
        self.creator_label = self._label("Creator: —")
        self.duration_label = self._label("Duration: —")
        self.views_label = self._label("Views: —")
        self.size_label = self._label("Estimated size: —")
        self.resolution_label = self._label("Resolution: —")
        for widget in (
            self.video_title, self.creator_label, self.duration_label,
            self.views_label, self.size_label, self.resolution_label,
        ):
            widget.setWordWrap(True)
            details_layout.addWidget(widget)
        details_layout.addStretch(1)
        self.info_status = self._label("Waiting for video information…")
        self.info_status.setWordWrap(True)
        details_layout.addWidget(self.info_status)
        main_row.addWidget(details_card, 4)
        layout.addLayout(main_row)

        trim_card, trim_layout = make_card(padding=15)
        trim_top = QHBoxLayout()
        trim_top.addWidget(self._label("CLIP SELECTOR", "SectionTitle"))
        trim_top.addStretch(1)
        self.trim_check = QCheckBox("Download selected part only")
        trim_top.addWidget(self.trim_check)
        trim_layout.addLayout(trim_top)

        trim_row = QHBoxLayout()
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0, 999999)
        self.start_spin.setDecimals(1)
        self.start_spin.setSuffix(" sec")
        self.start_spin.setPrefix("Start  ")
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0, 999999)
        self.end_spin.setDecimals(1)
        self.end_spin.setSuffix(" sec")
        self.end_spin.setPrefix("End  ")
        self.set_start_button = QPushButton("Set start at playhead")
        self.set_start_button.clicked.connect(lambda: self.start_spin.setValue(self.player.position() / 1000.0))
        self.set_end_button = QPushButton("Set end at playhead")
        self.set_end_button.clicked.connect(lambda: self.end_spin.setValue(self.player.position() / 1000.0))
        trim_row.addWidget(self.start_spin)
        trim_row.addWidget(self.set_start_button)
        trim_row.addWidget(self.end_spin)
        trim_row.addWidget(self.set_end_button)
        trim_layout.addLayout(trim_row)
        trim_layout.addWidget(self._label(
            "Preview the stream, seek to the exact moment, then set Start and End. "
            "The clip is cut by the media engine; FFmpeg makes cuts more accurate.",
            "Muted"
        ))
        layout.addWidget(trim_card)

        options_card, options_layout = make_card(padding=15)
        options_layout.addWidget(self._label("DOWNLOAD SETTINGS", "SectionTitle"))

        media_selection = QHBoxLayout()
        self.video_check = QCheckBox("Download Video")
        self.video_check.setChecked(True)
        self.audio_check = QCheckBox("Download Audio")
        self.audio_check.setChecked(False)
        media_selection.addWidget(self.video_check)
        media_selection.addWidget(self.audio_check)
        media_selection.addStretch(1)
        options_layout.addLayout(media_selection)

        options_row = QHBoxLayout()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Best quality", "4K (2160p)", "1440p", "1080p", "720p", "480p", "360p"
        ])
        self.quality_combo.setCurrentText("Best quality")
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(["320 kbps", "256 kbps", "192 kbps", "128 kbps"])
        self.audio_quality_combo.setCurrentText("192 kbps")
        options_row.addWidget(self._label("VIDEO QUALITY", "FieldLabel"))
        options_row.addWidget(self.quality_combo, 2)
        options_row.addWidget(self._label("AUDIO QUALITY", "FieldLabel"))
        options_row.addWidget(self.audio_quality_combo, 2)
        self.output_edit = QLineEdit(self.output_dir)
        self.output_edit.setMinimumWidth(220)
        options_row.addWidget(self._label("SAVE TO", "FieldLabel"))
        options_row.addWidget(self.output_edit, 3)
        self.browse_output_button = QPushButton("Browse")
        self.browse_output_button.clicked.connect(self.browse_output)
        options_row.addWidget(self.browse_output_button)
        options_layout.addLayout(options_row)
        self.video_check.toggled.connect(self.quality_combo.setEnabled)
        self.audio_check.toggled.connect(self.audio_quality_combo.setEnabled)
        self.audio_quality_combo.setEnabled(False)

        extras = QHBoxLayout()
        self.subtitles_check = QCheckBox("Download subtitles (EN / SI)")
        self.thumbnail_check = QCheckBox("Embed thumbnail")
        self.playlist_check = QCheckBox("Download playlist")
        extras.addWidget(self.subtitles_check)
        extras.addWidget(self.thumbnail_check)
        extras.addWidget(self.playlist_check)
        extras.addStretch(1)
        options_layout.addLayout(extras)
        layout.addWidget(options_card)

        progress_card, progress_layout = make_card(padding=16)
        progress_header = QHBoxLayout()
        progress_header.addWidget(self._label("DOWNLOAD PROGRESS", "SectionTitle"))
        progress_header.addStretch(1)
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("color:#f04458; font-size:18px; font-weight:800;")
        progress_header.addWidget(self.percent_label)
        progress_layout.addLayout(progress_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        progress_layout.addWidget(self.progress_bar)

        metrics = QHBoxLayout()
        self.downloaded_metric = self._metric(metrics, "DOWNLOADED", "0 B")
        self.total_metric = self._metric(metrics, "TOTAL SIZE", "Estimating…")
        self.remaining_metric = self._metric(metrics, "REMAINING", "—")
        self.speed_metric = self._metric(metrics, "SPEED", "—")
        self.eta_metric = self._metric(metrics, "TIME LEFT", "—")
        progress_layout.addLayout(metrics)

        action_row = QHBoxLayout()
        self.add_queue_button = QPushButton("+  Add to Queue")
        self.add_queue_button.clicked.connect(self.add_to_queue)
        action_row.addWidget(self.add_queue_button)
        self.queue_count_label = self._label("Queue: 0")
        action_row.addWidget(self.queue_count_label)
        action_row.addStretch(1)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("Danger")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_download)
        action_row.addWidget(self.cancel_button)
        self.download_button = QPushButton("⬇  DOWNLOAD NOW")
        self.download_button.setObjectName("Primary")
        self.download_button.clicked.connect(self.start_download)
        action_row.addWidget(self.download_button)
        progress_layout.addLayout(action_row)

        self.download_status = self._label("Ready to download.")
        progress_layout.addWidget(self.download_status)
        layout.addWidget(progress_card)

        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(95)
        self.queue_list.setVisible(False)
        layout.addWidget(self.queue_list)
        layout.addStretch(1)
        return self._scroll_page(page)

    def _metric(self, layout: QHBoxLayout, title: str, value: str) -> QLabel:
        box = QVBoxLayout()
        name = QLabel(title)
        name.setStyleSheet("color:#8390a1; font-size:8px; font-weight:800;")
        label = QLabel(value)
        label.setStyleSheet("color:#f3f5f8; font-size:11px; font-weight:700;")
        box.addWidget(name)
        box.addWidget(label)
        layout.addLayout(box)
        return label

    def _build_whatsapp_page(self) -> QWidget:
        page, layout = self._page_container()
        layout.addWidget(self._label("WhatsApp Status Saver", "HeroTitle"))
        layout.addWidget(self._label(
            "Save status photos and videos that are already available in a local WhatsApp media folder.",
            "HeroSub"
        ))

        notice, notice_layout = make_card(padding=17)
        notice_label = QLabel(
            "KyZer YouBe automatically checks whether WhatsApp Desktop is installed on this PC. "
            "It can scan a local status-media folder if WhatsApp or a user export makes one "
            "available. WhatsApp Desktop does not expose a supported public status-download API, "
            "so the app will not pretend that private chat-cache files are statuses."
        )
        notice_label.setWordWrap(True)
        notice_label.setStyleSheet("color:#bdc7d4; font-size:11px; line-height:1.5;")
        notice_layout.addWidget(notice_label)
        self.whatsapp_status_label = QLabel("Checking WhatsApp Desktop…")
        self.whatsapp_status_label.setWordWrap(True)
        self.whatsapp_status_label.setStyleSheet(
            "color:#45d49a; font-size:11px; font-weight:700; padding-top:5px;"
        )
        notice_layout.addWidget(self.whatsapp_status_label)
        wa_actions = QHBoxLayout()
        self.open_whatsapp_button = QPushButton("Open WhatsApp Desktop")
        self.open_whatsapp_button.clicked.connect(self.open_whatsapp_desktop)
        wa_actions.addWidget(self.open_whatsapp_button)
        self.detect_whatsapp_button = QPushButton("Detect Again")
        self.detect_whatsapp_button.clicked.connect(
            lambda: self._detect_whatsapp_desktop(auto_scan=True)
        )
        wa_actions.addWidget(self.detect_whatsapp_button)
        self.install_whatsapp_button = QPushButton("Get WhatsApp for PC")
        self.install_whatsapp_button.setObjectName("Primary")
        self.install_whatsapp_button.clicked.connect(self.get_whatsapp_desktop)
        wa_actions.addWidget(self.install_whatsapp_button)
        wa_actions.addStretch(1)
        notice_layout.addLayout(wa_actions)
        layout.addWidget(notice)

        folder_card, folder_layout = make_card()
        folder_layout.addWidget(self._label("STATUS MEDIA FOLDER", "FieldLabel"))
        row = QHBoxLayout()
        self.status_folder_edit = QLineEdit()
        self.status_folder_edit.setPlaceholderText("Select your copied WhatsApp .Statuses folder…")
        row.addWidget(self.status_folder_edit, 1)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_status_folder)
        row.addWidget(browse)
        self.browse_status_button = browse
        scan = QPushButton("↻  Scan Folder")
        scan.setObjectName("Primary")
        scan.clicked.connect(self.scan_status_folder)
        row.addWidget(scan)
        self.scan_status_button = scan
        folder_layout.addLayout(row)
        layout.addWidget(folder_card)

        results_card, results_layout = make_card()
        head = QHBoxLayout()
        head.addWidget(self._label("FOUND STATUS MEDIA", "SectionTitle"))
        head.addStretch(1)
        self.status_count = self._label("0 items")
        head.addWidget(self.status_count)
        results_layout.addLayout(head)
        self.status_list = QListWidget()
        self.status_list.setMinimumHeight(270)
        results_layout.addWidget(self.status_list)
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_status_button = QPushButton("Save Selected to Downloads")
        self.save_status_button.setObjectName("Primary")
        self.save_status_button.setEnabled(False)
        self.save_status_button.clicked.connect(self.save_selected_status)
        save_row.addWidget(self.save_status_button)
        results_layout.addLayout(save_row)
        layout.addWidget(results_card)
        layout.addStretch(1)
        return self._scroll_page(page)

    def _build_history_page(self) -> QWidget:
        page, layout = self._page_container()
        layout.addWidget(self._label("Download History", "HeroTitle"))
        layout.addWidget(self._label("Your recent downloads on this PC.", "HeroSub"))
        card, card_layout = make_card()
        header = QHBoxLayout()
        header.addWidget(self._label("RECENT FILES", "SectionTitle"))
        header.addStretch(1)
        clear_button = QPushButton("Clear History")
        clear_button.clicked.connect(self.clear_history)
        header.addWidget(clear_button)
        card_layout.addLayout(header)
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.open_history_item)
        card_layout.addWidget(self.history_list)
        open_row = QHBoxLayout()
        open_folder = QPushButton("Open Selected File Location")
        open_folder.clicked.connect(self.open_history_location)
        open_row.addStretch(1)
        open_row.addWidget(open_folder)
        card_layout.addLayout(open_row)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _build_settings_page(self) -> QWidget:
        page, layout = self._page_container()
        layout.addWidget(self._label("Settings", "HeroTitle"))
        layout.addWidget(self._label("Choose where KyZer YouBe saves your downloads.", "HeroSub"))
        card, card_layout = make_card()
        card_layout.addWidget(self._label("DEFAULT DOWNLOAD FOLDER", "FieldLabel"))
        row = QHBoxLayout()
        self.settings_output_edit = QLineEdit(self.output_dir)
        row.addWidget(self.settings_output_edit, 1)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_settings_output)
        row.addWidget(browse)
        card_layout.addLayout(row)
        save = QPushButton("Save Settings")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_settings)
        card_layout.addWidget(save, alignment=Qt.AlignRight)
        layout.addWidget(card)

        connection, connection_layout = make_card()
        connection_layout.addWidget(self._label("BROWSER SESSION (OPTIONAL)", "SectionTitle"))
        browser_row = QHBoxLayout()
        browser_row.addWidget(self._label("Browser cookies", "FieldLabel"))
        self.cookies_browser_combo = QComboBox()
        self.cookies_browser_combo.addItem("Disabled", None)
        for browser in ("Chrome", "Edge", "Firefox", "Brave", "Opera", "Vivaldi"):
            self.cookies_browser_combo.addItem(browser, browser.lower())
        browser_row.addWidget(self.cookies_browser_combo, 1)
        connection_layout.addLayout(browser_row)
        connection_layout.addWidget(self._label(
            "For a TikTok/website verification or rate-limit block: open the post in that "
            "browser, complete its CAPTCHA, then select the same browser here. Cookies are "
            "only read when you explicitly select a browser. Close the browser first if its "
            "cookie database is locked.",
            "Muted"
        ))
        log_row = QHBoxLayout()
        log_row.addWidget(self._label("Troubleshooting", "FieldLabel"))
        log_row.addStretch(1)
        open_log = QPushButton("Open log.txt")
        open_log.clicked.connect(self.open_log_file)
        log_row.addWidget(open_log)
        connection_layout.addLayout(log_row)
        layout.addWidget(connection)

        about, about_layout = make_card()
        about_layout.addWidget(self._label("ABOUT KYZER YOUBE", "SectionTitle"))
        about_layout.addWidget(self._label(
            "KyZer YouBe is a desktop media utility powered by yt-dlp, PySide6 and FFmpeg. "
            "YouTube, TikTok and Facebook support depends on the source being publicly accessible. "
            "Respect creators' rights and each platform's terms.",
            "Muted"
        ))
        layout.addWidget(about)
        layout.addStretch(1)
        return page

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def paste_url(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_edit.setText(text)
            self.url_edit.setFocus()
            self._update_platform_badge()

    def _update_platform_badge(self) -> None:
        url = self.url_edit.text().strip()
        platform = detect_platform(url)
        if platform == "Unsupported" and url:
            self.preview_platform.setText("UNSUPPORTED LINK")
            self.preview_platform.setStyleSheet("color:#ff7786; font-weight:800;")
        elif platform != "Unsupported":
            self.preview_platform.setText(platform.upper())
            self.preview_platform.setStyleSheet("color:#45d49a; font-weight:800;")
        else:
            self.preview_platform.setText("WAITING FOR LINK")
            self.preview_platform.setStyleSheet("color:#929eae;")

    def get_video_info(self) -> None:
        if self.info_worker and self.info_worker.isRunning():
            return
        url = self.url_edit.text().strip()
        if not is_supported_url(url):
            QMessageBox.warning(
                self, APP_NAME,
                "Paste a valid public YouTube, TikTok or Facebook post/video URL."
            )
            return

        self._update_platform_badge()
        self.info_button.setEnabled(False)
        self.info_button.setText("Getting info…")
        self.info_status.setText("Fetching title, duration, formats and preview stream…")
        self.header_status.setText("●  FETCHING VIDEO INFO")
        browser = self.cookies_browser_combo.currentData()
        get_app_logger().info(
            "Get Video Info clicked: platform=%s browser_cookies=%s",
            detect_platform(url), browser or "off",
        )
        self.info_worker = InfoWorker(url, cookies_browser=browser)
        self.info_worker.succeeded.connect(self._info_ready)
        self.info_worker.failed.connect(self._info_failed)
        self.info_worker.finished.connect(self._info_thread_finished)
        self.info_worker.start()

    def _info_thread_finished(self) -> None:
        self.info_button.setEnabled(True)
        self.info_button.setText("⌕  Get Video Info")
        if self.header_status.text() == "●  FETCHING VIDEO INFO":
            self.header_status.setText("●  ALL SYSTEMS READY")

    def _info_ready(self, info: dict[str, Any]) -> None:
        self.info = info
        thumbnail_data = info.get("thumbnail_data")
        if thumbnail_data:
            image = QPixmap()
            if image.loadFromData(thumbnail_data):
                self.thumbnail_preview.setPixmap(image.scaled(
                    self.thumbnail_preview.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                ))
                self.thumbnail_preview.setText("")
            else:
                self.thumbnail_preview.setPixmap(QPixmap())
                self.thumbnail_preview.setText("Thumbnail unavailable")
        else:
            self.thumbnail_preview.setPixmap(QPixmap())
            self.thumbnail_preview.setText("Thumbnail unavailable")

        self.video_title.setText(info.get("title", "Untitled video"))
        self.creator_label.setText("Creator: {}".format(info.get("uploader") or "—"))
        self.duration_label.setText("Duration: {}".format(info.get("duration_text") or "—"))
        self.views_label.setText("Views: {}".format(pretty_count(info.get("view_count"))))
        self.size_label.setText("Estimated size: {}".format(info.get("filesize_text") or "Unknown"))
        height = info.get("height")
        width = info.get("width")
        resolution = "{} × {}".format(width, height) if width and height else "Adaptive / unknown"
        self.resolution_label.setText("Preview quality: {}".format(resolution))
        self.preview_platform.setText(info.get("platform", "VIDEO").upper())
        self.preview_platform.setStyleSheet("color:#45d49a; font-weight:800;")

        duration = info.get("duration")
        if duration:
            self.end_spin.setMaximum(float(duration))
            self.end_spin.setValue(float(duration))
            self.start_spin.setMaximum(float(duration))

        preview_url = info.get("preview_url")
        self.player.stop()
        if preview_url:
            self.player.setSource(QUrl(preview_url))
            self.preview_stack.setCurrentWidget(self.video_widget)
            self.play_button.setEnabled(True)
            self.play_button.setText("▶  Play")
            self.info_status.setText(
                "Preview stream prepared. Press Play to play it inside KyZer YouBe."
            )
        else:
            self.player.setSource(QUrl())
            self.preview_stack.setCurrentWidget(self.preview_placeholder)
            self.play_button.setEnabled(False)
            self.info_status.setText(
                "No direct preview stream is available for this post. Use Open on Platform."
            )


    def _info_failed(self, message: str) -> None:
        get_app_logger().error("Get Video Info failed: %s", message)
        self.info_status.setText("Could not fetch video information. Details saved to log.txt.")
        QMessageBox.critical(
            self, "Video info error",
            message + "\n\nDiagnostic log: " + str(app_data_dir() / "log.txt")
        )

    def toggle_playback(self) -> None:
        if self.player.source().isEmpty():
            self.info_status.setText(
                "This post did not provide a direct stream for in-app playback. "
                "Use Open on Platform to watch it in your browser."
            )
            return

        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_button.setText("▶  Play")
            return

        if self.player.mediaStatus() == QMediaPlayer.EndOfMedia:
            self.player.setPosition(0)
        self.preview_stack.setCurrentWidget(self.video_widget)
        self.player.play()
        self.play_button.setText("Ⅱ  Pause")

    def _playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.play_button.setText(
            "Ⅱ  Pause" if state == QMediaPlayer.PlayingState else "▶  Play"
        )

    def open_source(self) -> None:
        url = self.url_edit.text().strip()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _player_error(self, _error: QMediaPlayer.Error, error_string: str) -> None:
        if error_string:
            get_app_logger().warning("Embedded preview playback error: %s", error_string)
            self.play_button.setText("▶  Play")
            self.info_status.setText(
                "This stream could not play in the embedded player: {}. "
                "Use Open on Platform.".format(error_string)
            )

    def _duration_changed(self, duration_ms: int) -> None:
        duration = max(0, duration_ms // 1000)
        self.playback_time.setText(
            "{} / {}".format(format_duration(0), format_duration(duration))
        )

    def _position_changed(self, position_ms: int) -> None:
        duration = self.player.duration()
        if duration > 0 and not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(int(position_ms * 1000 / duration))
        self.playback_time.setText(
            "{} / {}".format(
                format_duration(position_ms / 1000),
                format_duration(duration / 1000),
            )
        )

    def _seek_preview(self, value: int) -> None:
        duration = self.player.duration()
        if duration > 0:
            self.player.setPosition(int(duration * value / 1000))

    def browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose download folder", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)

    def add_to_queue(self) -> None:
        url = self.url_edit.text().strip()
        if not is_supported_url(url):
            QMessageBox.warning(self, APP_NAME, "Paste a supported video URL first.")
            return
        if url not in self.queue_urls:
            self.queue_urls.append(url)
            self.queue_list.addItem("{}  •  {}".format(detect_platform(url), url))
            self.queue_list.setVisible(True)
            self.queue_count_label.setText("Queue: {}".format(len(self.queue_urls)))
        self.download_status.setText("Added to queue. Click Download Now to start this link.")

    def start_download(self) -> None:
        if self.download_worker and self.download_worker.isRunning():
            return
        current_url = self.url_edit.text().strip()
        if self.queue_urls:
            urls = list(self.queue_urls)
        elif is_supported_url(current_url):
            urls = [current_url]
        else:
            QMessageBox.warning(
                self, APP_NAME, "Paste a valid YouTube, TikTok or Facebook link first."
            )
            return

        download_video = self.video_check.isChecked()
        download_audio = self.audio_check.isChecked()
        if not download_video and not download_audio:
            QMessageBox.warning(
                self, APP_NAME, "Select Download Video, Download Audio, or both."
            )
            return

        output = self.output_edit.text().strip() or self.output_dir
        try:
            Path(output).expanduser().mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            get_app_logger().exception("Could not create download output folder")
            QMessageBox.critical(self, "Save folder error", str(exc))
            return

        video_quality = {
            "4K (2160p)": "2160p",
            "1440p": "1440p",
            "1080p": "1080p",
            "720p": "720p",
            "480p": "480p",
            "360p": "360p",
        }.get(self.quality_combo.currentText(), "best")
        audio_quality = str(self.audio_quality_combo.currentData() or
                            self.audio_quality_combo.currentText().split()[0])
        browser = self.cookies_browser_combo.currentData()

        section = None
        if self.trim_check.isChecked():
            start = self.start_spin.value()
            end = self.end_spin.value()
            if end <= start:
                QMessageBox.warning(self, "Clip selection", "End time must be after start time.")
                return
            if self.info and self.info.get("duration") and end > float(self.info["duration"]):
                QMessageBox.warning(self, "Clip selection", "End time is beyond the video duration.")
                return
            section = (start, end)

        self.output_dir = output
        self.download_button.setEnabled(False)
        self.download_button.setText("Downloading…")
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self._set_metrics("0 B", "Estimating…", "—", "—", "—")
        media_names = []
        if download_video:
            media_names.append("video")
        if download_audio:
            media_names.append("audio")
        self.download_status.setText(
            "Starting {} item(s) ({})…".format(len(urls), " + ".join(media_names))
        )
        self.header_status.setText("●  DOWNLOAD IN PROGRESS")

        get_app_logger().info(
            "Starting queue: urls=%d video=%s audio=%s video_quality=%s audio_quality=%s subtitles=%s",
            len(urls), download_video, download_audio, video_quality, audio_quality,
            self.subtitles_check.isChecked() and download_video,
        )
        self.download_worker = DownloadWorker(
            urls=urls,
            output_dir=output,
            download_video=download_video,
            download_audio=download_audio,
            video_quality=video_quality,
            audio_quality=audio_quality,
            subtitles=self.subtitles_check.isChecked(),
            thumbnail=self.thumbnail_check.isChecked(),
            playlist=self.playlist_check.isChecked(),
            section=section,
            cookies_browser=browser,
        )
        self.download_worker.progress.connect(self._download_progress)
        self.download_worker.succeeded.connect(self._download_succeeded)
        self.download_worker.failed.connect(self._download_failed)
        self.download_worker.cancelled.connect(self._download_cancelled)
        self.download_worker.finished.connect(self._download_thread_finished)
        self.download_worker.start()


    def _set_metrics(self, downloaded: str, total: str, remaining: str, speed: str, eta: str) -> None:
        self.downloaded_metric.setText(downloaded)
        self.total_metric.setText(total)
        self.remaining_metric.setText(remaining)
        self.speed_metric.setText(speed)
        self.eta_metric.setText(eta)

    def _download_progress(self, data: dict[str, Any]) -> None:
        queue_index = data.get("queue_index")
        queue_total = data.get("queue_total")
        queue_prefix = (
            "Queue {}/{}  •  ".format(queue_index, queue_total)
            if queue_index and queue_total and queue_total > 1 else ""
        )
        media_prefix = "[{}]  ".format(data.get("media_kind", "MEDIA"))
        if data.get("status") == "processing":
            self.download_status.setText(queue_prefix + media_prefix + "Download received — merging and processing…")
        else:
            percent = int(max(0, min(100, float(data.get("percent") or 0))))
            self.progress_bar.setValue(percent)
            self.percent_label.setText("{}%".format(percent))
            self._set_metrics(
                data.get("downloaded_text", "—"),
                data.get("total_text", "Estimating…"),
                data.get("remaining_text", "—"),
                data.get("speed_text", "—"),
                data.get("eta_text", "—"),
            )
            self.download_status.setText(queue_prefix + media_prefix + "Downloading media…")

    def _download_succeeded(self, results: list[dict[str, str]]) -> None:
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.download_status.setText(
            "Completed {} file(s) successfully.".format(len(results))
        )
        for result in results:
            path = str(result.get("path") or "")
            source_url = str(result.get("url") or self.url_edit.text().strip())
            title = Path(path).name
            if self.info and source_url == self.info.get("webpage_url"):
                title = str(self.info.get("title") or title)
            kind = str(result.get("kind") or "MEDIA").title()
            if kind == "Audio":
                title = "{} (Audio)".format(title)
            self._save_history(title, path, source_url)

        self.queue_urls.clear()
        self.queue_list.clear()
        self.queue_list.setVisible(False)
        self.queue_count_label.setText("Queue: 0")
        QMessageBox.information(
            self, APP_NAME, "Completed {} file(s) successfully.".format(len(results))
        )


    def _download_failed(self, message: str) -> None:
        get_app_logger().error("Download failed: %s", message)
        self.download_status.setText("Download failed. Details saved to log.txt.")
        QMessageBox.critical(
            self, "Download error",
            message + "\n\nDiagnostic log: " + str(app_data_dir() / "log.txt")
        )

    def _download_cancelled(self) -> None:
        self.download_status.setText("Download cancelled.")
        self.header_status.setText("●  READY")

    def _download_thread_finished(self) -> None:
        self.download_button.setEnabled(True)
        self.download_button.setText("⬇  DOWNLOAD NOW")
        self.cancel_button.setEnabled(False)
        self.header_status.setText("●  ALL SYSTEMS READY")

    def cancel_download(self) -> None:
        if self.download_worker and self.download_worker.isRunning():
            self.download_status.setText("Cancelling after the current transfer chunk…")
            self.download_worker.cancel()
            self.cancel_button.setEnabled(False)

    def _detect_whatsapp_desktop(self, auto_scan: bool = False) -> None:
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        candidates = [
            local / "Programs" / "WhatsApp" / "WhatsApp.exe",
            local / "WhatsApp" / "WhatsApp.exe",
            roaming / "WhatsApp" / "WhatsApp.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "WindowsApps",
        ]
        executable = next(
            (path for path in candidates if path.is_file() and path.name.lower() == "whatsapp.exe"),
            None,
        )

        package_root = local / "Packages"
        packages = []
        if package_root.is_dir():
            try:
                packages = [
                    p for p in package_root.iterdir()
                    if p.is_dir() and "whatsappdesktop" in p.name.lower()
                ]
            except OSError:
                packages = []
        installed = bool(executable or packages)

        status_candidates = [
            local / "WhatsApp" / "Media" / ".Statuses",
            roaming / "WhatsApp" / "Media" / ".Statuses",
            Path.home() / "Documents" / "WhatsApp" / "Media" / ".Statuses",
        ]
        for package in packages:
            status_candidates.extend([
                package / "LocalState" / "shared" / ".Statuses",
                package / "LocalState" / "shared" / "Statuses",
                package / "LocalCache" / "Roaming" / "WhatsApp" / "Media" / ".Statuses",
            ])
        detected_folder = next((p for p in status_candidates if p.is_dir()), None)

        self.whatsapp_installed = installed
        if not installed:
            self.whatsapp_status_label.setText(
                "✕ WhatsApp Desktop was NOT detected on this PC. Install WhatsApp for PC "
                "to enable this section."
            )
            self.whatsapp_status_label.setStyleSheet(
                "color:#ff7786; font-size:11px; font-weight:700; padding-top:5px;"
            )
            self.open_whatsapp_button.setEnabled(False)
            self.install_whatsapp_button.setVisible(True)
            self.status_folder_edit.setEnabled(False)
            self.browse_status_button.setEnabled(False)
            self.scan_status_button.setEnabled(False)
            self.save_status_button.setEnabled(False)
            self.status_list.clear()
            self.status_count.setText("0 items")
            return

        self.whatsapp_status_label.setText(
            "✓ WhatsApp Desktop detected on this PC."
            + (
                " A local status-media folder was found."
                if detected_folder else
                " No public .Statuses folder is exposed by this desktop installation; "
                "you can still select a folder exported to this PC."
            )
        )
        self.whatsapp_status_label.setStyleSheet(
            "color:#45d49a; font-size:11px; font-weight:700; padding-top:5px;"
        )
        self.open_whatsapp_button.setEnabled(True)
        self.install_whatsapp_button.setVisible(False)
        self.status_folder_edit.setEnabled(True)
        self.browse_status_button.setEnabled(True)
        self.scan_status_button.setEnabled(True)
        self.save_status_button.setEnabled(True)
        if detected_folder and auto_scan:
            self.status_folder_edit.setText(str(detected_folder))
            self.scan_status_folder()

    def open_whatsapp_desktop(self) -> None:
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        candidates = [
            local / "Programs" / "WhatsApp" / "WhatsApp.exe",
            local / "WhatsApp" / "WhatsApp.exe",
        ]
        executable = next((p for p in candidates if p.is_file()), None)
        if executable:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(executable)))
        else:
            QDesktopServices.openUrl(QUrl("whatsapp://"))

    def get_whatsapp_desktop(self) -> None:
        QDesktopServices.openUrl(QUrl("https://www.whatsapp.com/download"))

    def open_log_file(self) -> None:
        log_path = app_data_dir() / "log.txt"
        if not log_path.exists():
            get_app_logger().info("Log opened by user")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_path)))

    def browse_status_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select copied WhatsApp .Statuses folder",
            self.status_folder_edit.text() or str(Path.home())
        )
        if folder:
            self.status_folder_edit.setText(folder)

    def scan_status_folder(self) -> None:
        if not self.whatsapp_installed:
            QMessageBox.information(
                self, APP_NAME, "You need WhatsApp Desktop installed on this PC first."
            )
            return
        folder = Path(self.status_folder_edit.text().strip()).expanduser()
        if not folder.is_dir():
            QMessageBox.warning(self, APP_NAME, "Choose a valid local status media folder.")
            return
        allowed = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".3gp", ".mov"}
        found = sorted(
            (item for item in folder.iterdir() if item.is_file() and item.suffix.lower() in allowed),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        self.status_list.clear()
        for item in found:
            kind = "VIDEO" if item.suffix.lower() in {".mp4", ".3gp", ".mov"} else "PHOTO"
            row = QListWidgetItem("{}   •   {}   •   {}".format(kind, item.name, self._file_size(item.stat().st_size)))
            row.setData(Qt.UserRole, str(item))
            self.status_list.addItem(row)
        self.status_count.setText("{} items".format(len(found)))
        self.status_folder = str(folder)

    @staticmethod
    def _file_size(size: int) -> str:
        from downloader import format_bytes
        return format_bytes(size)

    def save_selected_status(self) -> None:
        if not self.whatsapp_installed:
            QMessageBox.information(
                self, APP_NAME, "You need WhatsApp Desktop installed on this PC first."
            )
            return
        item = self.status_list.currentItem()
        if not item:
            QMessageBox.information(self, APP_NAME, "Select a status photo or video first.")
            return
        source = Path(item.data(Qt.UserRole))
        destination_dir = Path(self.output_dir) / "WhatsApp Status"
        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / source.name
            if destination.exists():
                destination = destination_dir / "{}_{}".format(
                    datetime.now().strftime("%H%M%S"), source.name
                )
            shutil.copy2(source, destination)
        except OSError as exc:
            QMessageBox.critical(self, "Could not save status", str(exc))
            return
        QMessageBox.information(self, APP_NAME, "Saved to:\n{}".format(destination))

    def _refresh_history(self) -> None:
        if not hasattr(self, "history_list"):
            return
        self.history_list.clear()
        for item in self.history:
            self.history_list.addItem(
                "{}\n{}   •   {}".format(item.get("title", "Download"), item.get("date", ""), item.get("path", ""))
            )

    def clear_history(self) -> None:
        reply = QMessageBox.question(
            self, APP_NAME, "Clear the download history list? Downloaded files will not be deleted."
        )
        if reply == QMessageBox.Yes:
            self.history = []
            try:
                self.history_file.write_text("[]", encoding="utf-8")
            except OSError:
                pass
            self._refresh_history()

    def open_history_item(self, item: QListWidgetItem) -> None:
        index = self.history_list.row(item)
        if 0 <= index < len(self.history):
            path = self.history[index].get("path", "")
            if Path(path).is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            else:
                QMessageBox.information(self, APP_NAME, "That file is no longer at its saved location.")

    def open_history_location(self) -> None:
        index = self.history_list.currentRow()
        if 0 <= index < len(self.history):
            path = Path(self.history[index].get("path", ""))
            if path.exists():
                target = path if path.is_dir() else path.parent
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            else:
                QMessageBox.information(self, APP_NAME, "The saved file or folder cannot be found.")

    def browse_settings_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose default download folder", self.settings_output_edit.text()
        )
        if folder:
            self.settings_output_edit.setText(folder)

    def save_settings(self) -> None:
        folder = self.settings_output_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, APP_NAME, "Choose a valid default download folder.")
            return
        try:
            Path(folder).expanduser().mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "Settings error", str(exc))
            return
        self.output_dir = folder
        self.output_edit.setText(folder)
        self.cookies_browser = self.cookies_browser_combo.currentData()
        get_app_logger().info(
            "Settings saved: download_folder=%s browser_cookies=%s",
            folder, self.cookies_browser or "off",
        )
        QMessageBox.information(self, APP_NAME, "Settings saved.")

    def closeEvent(self, event: Any) -> None:
        if self.download_worker and self.download_worker.isRunning():
            reply = QMessageBox.question(
                self, APP_NAME,
                "A download is running. Cancel it and close KyZer YouBe?",
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self.download_worker.cancel()
            self.download_worker.wait(2500)
        self.player.stop()
        event.accept()


def main() -> None:
    get_app_logger().info("KyZer YouBe starting")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("KyZer_HADOC")
    app.setStyle("Fusion")
    icon_file = resource_path("KyZer YouBe.png")
    if Path(icon_file).exists():
        app.setWindowIcon(QIcon(icon_file))
    window = KyZerYouBe()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
