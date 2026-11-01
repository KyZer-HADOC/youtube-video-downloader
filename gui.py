#!/usr/bin/env python3
"""KyZer Downloader - desktop GUI for yt-dlp."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from urllib.parse import urlsplit
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from downloader import YouTubeDownloader


class KyZerDownloaderApp:
    BG = "#101116"
    HEADER = "#171820"
    PANEL = "#1b1d26"
    INPUT = "#252833"
    TEXT = "#f4f5f7"
    MUTED = "#9da2b0"
    ACCENT = "#ff465c"
    GREEN = "#39d98a"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("KyZer Downloader")
        self.root.geometry("760x700")
        self.root.minsize(650, 640)
        self.root.configure(bg=self.BG)

        self.events: queue.Queue[tuple] = queue.Queue()
        self.is_downloading = False
        self.closing = False

        self.url_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.quality_var = tk.StringVar(value="Best quality")
        self.status_var = tk.StringVar(value="Ready when you are")
        self.progress_text_var = tk.StringVar(value="0%")

        self._configure_styles()
        self._build_interface()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._process_events)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "KyZer.Horizontal.TProgressbar",
            troughcolor=self.INPUT, background=self.ACCENT,
            bordercolor=self.INPUT, lightcolor=self.ACCENT,
            darkcolor=self.ACCENT, thickness=10,
        )
        style.configure(
            "KyZer.TCombobox",
            fieldbackground=self.INPUT, background=self.INPUT,
            foreground=self.TEXT, arrowcolor=self.TEXT,
            bordercolor=self.INPUT, padding=9,
        )
        style.map(
            "KyZer.TCombobox",
            fieldbackground=[("readonly", self.INPUT)],
            foreground=[("readonly", self.TEXT)],
            selectbackground=[("readonly", self.INPUT)],
            selectforeground=[("readonly", self.TEXT)],
        )
        style.configure(
            "Accent.TButton", background=self.ACCENT, foreground="#ffffff",
            borderwidth=0, focusthickness=0, padding=(18, 12),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", "#63313a"), ("active", "#ff6375")],
            foreground=[("disabled", "#b8a2a6"), ("active", "#ffffff")],
        )
        style.configure(
            "Quiet.TButton", background=self.INPUT, foreground=self.TEXT,
            borderwidth=0, focusthickness=0, padding=(12, 9),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Quiet.TButton",
            background=[("active", "#343846"), ("disabled", self.PANEL)],
            foreground=[("disabled", self.MUTED)],
        )

    def _build_interface(self) -> None:
        # Branded header
        header = tk.Frame(self.root, bg=self.HEADER, height=132)
        header.pack(fill="x")
        header.pack_propagate(False)

        inner = tk.Frame(header, bg=self.HEADER)
        inner.pack(fill="both", expand=True, padx=32, pady=22)

        logo = tk.Canvas(inner, width=58, height=58, bg=self.HEADER, highlightthickness=0)
        logo.pack(side="left", padx=(0, 14))
        logo.create_polygon(
            8, 5, 50, 5, 55, 10, 55, 48, 50, 53, 8, 53, 3, 48, 3, 10,
            smooth=True, fill=self.ACCENT, outline=self.ACCENT
        )
        logo.create_polygon(23, 17, 23, 41, 42, 29, fill="#ffffff", outline="#ffffff")

        brand = tk.Frame(inner, bg=self.HEADER)
        brand.pack(side="left", anchor="center")
        tk.Label(
            brand, text="KyZer Downloader", bg=self.HEADER, fg=self.TEXT,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")
        tk.Label(
            brand, text="VIDEO DOWNLOADER  •  SIMPLE, FAST, CLEAN",
            bg=self.HEADER, fg=self.ACCENT, font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            inner, text="DESKTOP EDITION", bg="#292b36", fg="#d7d9e0",
            font=("Segoe UI", 8, "bold"), padx=12, pady=7
        ).pack(side="right", anchor="center")

        tk.Frame(self.root, bg=self.ACCENT, height=3).pack(fill="x")

        # Main content
        content = tk.Frame(self.root, bg=self.BG)
        content.pack(fill="both", expand=True, padx=34, pady=(25, 16))

        tk.Label(
            content, text="Ready to download?", bg=self.BG, fg=self.TEXT,
            font=("Segoe UI", 19, "bold")
        ).pack(anchor="w")
        tk.Label(
            content, text="Paste a video link, choose your quality, and save it to your PC.",
            bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(4, 19))

        # URL card
        url_card = tk.Frame(content, bg=self.PANEL, padx=18, pady=16)
        url_card.pack(fill="x")
        tk.Label(
            url_card, text="VIDEO URL", bg=self.PANEL, fg="#c8cbd4",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(0, 9))
        url_row = tk.Frame(url_card, bg=self.PANEL)
        url_row.pack(fill="x")
        self.url_entry = tk.Entry(
            url_row, textvariable=self.url_var, bg=self.INPUT, fg=self.TEXT,
            insertbackground=self.TEXT, relief="flat", bd=0,
            font=("Segoe UI", 10), highlightthickness=1,
            highlightbackground=self.INPUT, highlightcolor=self.ACCENT,
        )
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=12, padx=(0, 9))
        self.url_entry.bind("<Return>", lambda _event: self.start_download())
        ttk.Button(
            url_row, text="Paste", style="Quiet.TButton", command=self._paste_url
        ).pack(side="right")

        # Quality and destination cards
        options = tk.Frame(content, bg=self.BG)
        options.pack(fill="x", pady=(17, 0))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)

        quality_card = tk.Frame(options, bg=self.PANEL, padx=16, pady=14)
        quality_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(
            quality_card, text="FORMAT & QUALITY", bg=self.PANEL, fg="#c8cbd4",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(0, 8))
        self.quality_box = ttk.Combobox(
            quality_card, textvariable=self.quality_var,
            values=("Best quality", "1080p HD", "720p HD", "480p SD", "MP3 audio"),
            state="readonly", style="KyZer.TCombobox", font=("Segoe UI", 9),
        )
        self.quality_box.pack(fill="x")

        folder_card = tk.Frame(options, bg=self.PANEL, padx=16, pady=14)
        folder_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(
            folder_card, text="SAVE LOCATION", bg=self.PANEL, fg="#c8cbd4",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(0, 8))
        folder_row = tk.Frame(folder_card, bg=self.PANEL)
        folder_row.pack(fill="x")
        self.folder_entry = tk.Entry(
            folder_row, textvariable=self.folder_var, bg=self.INPUT, fg=self.TEXT,
            insertbackground=self.TEXT, relief="flat", bd=0,
            font=("Segoe UI", 9), highlightthickness=1,
            highlightbackground=self.INPUT, highlightcolor=self.ACCENT,
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 7))
        self.browse_button = ttk.Button(
            folder_row, text="Browse", style="Quiet.TButton", command=self._browse_folder
        )
        self.browse_button.pack(side="right")

        # Progress card
        progress_card = tk.Frame(content, bg=self.PANEL, padx=18, pady=16)
        progress_card.pack(fill="x", pady=(17, 0))
        progress_top = tk.Frame(progress_card, bg=self.PANEL)
        progress_top.pack(fill="x")
        tk.Label(
            progress_top, text="DOWNLOAD PROGRESS", bg=self.PANEL, fg="#c8cbd4",
            font=("Segoe UI", 8, "bold")
        ).pack(side="left")
        tk.Label(
            progress_top, textvariable=self.progress_text_var, bg=self.PANEL,
            fg=self.ACCENT, font=("Segoe UI", 9, "bold")
        ).pack(side="right")
        self.progress_bar = ttk.Progressbar(
            progress_card, maximum=100, value=0, style="KyZer.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(11, 10))
        self.status_label = tk.Label(
            progress_card, textvariable=self.status_var, bg=self.PANEL,
            fg=self.MUTED, font=("Segoe UI", 9), anchor="w"
        )
        self.status_label.pack(fill="x")

        # Actions and footer
        actions = tk.Frame(content, bg=self.BG)
        actions.pack(fill="x", pady=(19, 0))
        self.clear_button = ttk.Button(
            actions, text="Clear", style="Quiet.TButton", command=self.clear_fields
        )
        self.clear_button.pack(side="left")
        self.download_button = ttk.Button(
            actions, text="↓   DOWNLOAD NOW", style="Accent.TButton",
            command=self.start_download
        )
        self.download_button.pack(side="right")

        footer = tk.Frame(content, bg=self.BG)
        footer.pack(fill="x", side="bottom", pady=(18, 0))
        tk.Label(
            footer, text="Powered by yt-dlp", bg=self.BG, fg="#777c89",
            font=("Segoe UI", 8)
        ).pack(side="left")
        tk.Label(
            footer, text="Made by KyZer_HADOC", bg=self.BG, fg="#777c89",
            font=("Segoe UI", 8)
        ).pack(side="right")

    @staticmethod
    def _is_supported_url(url: str) -> bool:
        try:
            parsed = urlsplit(url.strip())
            host = (parsed.hostname or "").lower()
            return parsed.scheme in ("http", "https") and (
                host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
            )
        except ValueError:
            return False

    def _paste_url(self) -> None:
        try:
            value = self.root.clipboard_get().strip()
        except tk.TclError:
            value = ""
        if value:
            self.url_var.set(value)
            self.url_entry.focus_set()

    def _browse_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Choose download folder",
            initialdir=self.folder_var.get() or str(Path.home())
        )
        if selected:
            self.folder_var.set(selected)

    def clear_fields(self) -> None:
        if self.is_downloading:
            return
        self.url_var.set("")
        self.quality_var.set("Best quality")
        self.progress_bar["value"] = 0
        self.progress_text_var.set("0%")
        self.status_var.set("Ready when you are")
        self.status_label.configure(fg=self.MUTED)
        self.url_entry.focus_set()

    def _set_busy(self, busy: bool) -> None:
        self.is_downloading = busy
        state = "disabled" if busy else "normal"
        self.download_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.browse_button.configure(state=state)
        self.quality_box.configure(state="disabled" if busy else "readonly")
        self.url_entry.configure(state=state)
        self.folder_entry.configure(state=state)

    def start_download(self) -> None:
        if self.is_downloading:
            return
        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()

        if not url:
            messagebox.showwarning("KyZer Downloader", "Paste a YouTube video link first.")
            self.url_entry.focus_set()
            return
        if not self._is_supported_url(url):
            messagebox.showerror(
                "Invalid link", "Please enter a valid YouTube URL (youtube.com or youtu.be)."
            )
            return
        if not folder:
            messagebox.showwarning("Save location", "Choose a folder for your download.")
            return

        quality_map = {
            "Best quality": "best", "1080p HD": "1080p",
            "720p HD": "720p", "480p SD": "480p", "MP3 audio": "mp3",
        }
        format_type = quality_map.get(self.quality_var.get(), "best")
        try:
            Path(folder).expanduser().mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Save location error", str(exc))
            return

        self._set_busy(True)
        self.progress_bar["value"] = 0
        self.progress_text_var.set("0%")
        self.status_var.set("Connecting to YouTube…")
        self.status_label.configure(fg=self.ACCENT)

        threading.Thread(
            target=self._download_worker,
            args=(url, folder, format_type, format_type == "mp3"),
            daemon=True,
        ).start()

    def _download_worker(self, url: str, folder: str, format_type: str, audio_only: bool) -> None:
        try:
            downloader = YouTubeDownloader(folder)
            callback = lambda data: self.events.put(("progress", data))
            success = downloader.download_video(
                url, format_type=format_type, audio_only=audio_only,
                progress_callback=callback,
            )
            self.events.put(("done", bool(success)))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _process_events(self) -> None:
        if self.closing:
            return
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    data = event[1]
                    percent = max(0.0, min(100.0, float(data.get("percent") or 0)))
                    self.progress_bar["value"] = percent
                    self.progress_text_var.set(f"{percent:.0f}%")
                    if data.get("status") == "processing":
                        self.status_var.set("Finishing up your download…")
                    else:
                        details = []
                        if data.get("speed"):
                            details.append(str(data["speed"]))
                        if data.get("eta"):
                            details.append(f"ETA {data['eta']}")
                        self.status_var.set(
                            "Downloading…" + (f"  {'  •  '.join(details)}" if details else "")
                        )
                elif kind == "done":
                    self._set_busy(False)
                    if event[1]:
                        self.progress_bar["value"] = 100
                        self.progress_text_var.set("100%")
                        self.status_var.set("Download completed successfully.")
                        self.status_label.configure(fg=self.GREEN)
                        messagebox.showinfo(
                            "Download complete", "Your download has been saved successfully."
                        )
                    else:
                        self.status_var.set("The download could not be completed.")
                        self.status_label.configure(fg=self.ACCENT)
                        messagebox.showerror("Download failed", "yt-dlp could not complete this download.")
                elif kind == "error":
                    self._set_busy(False)
                    self.status_var.set("Something went wrong. See the error message.")
                    self.status_label.configure(fg=self.ACCENT)
                    messagebox.showerror("Download error", event[1])
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)

    def _on_close(self) -> None:
        if self.is_downloading and not messagebox.askyesno(
            "Download in progress",
            "A download is still running. Close KyZer Downloader anyway?"
        ):
            return
        self.closing = True
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    KyZerDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
