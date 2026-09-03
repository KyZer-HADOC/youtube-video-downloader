#!/usr/bin/env python3
"""
YouTube Video Downloader GUI
A graphical interface for downloading YouTube videos
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading
from downloader import YouTubeDownloader


class YouTubeDownloaderGUI:
    """GUI for YouTube video downloader"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Downloader")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        self.downloader = None
        self.downloading = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the GUI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="YouTube Video Downloader",
            font=("Helvetica", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # URL Input
        ttk.Label(main_frame, text="Video URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(main_frame, width=50)
        self.url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Output Directory
        ttk.Label(main_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        
        self.output_entry = ttk.Entry(output_frame, width=35)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.output_entry.insert(0, "videos")
        
        browse_btn = ttk.Button(output_frame, text="Browse", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Format Selection
        ttk.Label(main_frame, text="Format:").grid(row=3, column=0, sticky=tk.W, pady=5)
        format_frame = ttk.Frame(main_frame)
        format_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5)
        
        self.format_var = tk.StringVar(value="best")
        formats = ["best", "1080p", "720p", "mp3"]
        
        for fmt in formats:
            ttk.Radiobutton(
                format_frame,
                text=fmt,
                variable=self.format_var,
                value=fmt
            ).pack(side=tk.LEFT, padx=5)
        
        # Audio Only Checkbox
        self.audio_var = tk.BooleanVar()
        ttk.Checkbutton(
            main_frame,
            text="Audio Only (MP3)",
            variable=self.audio_var
        ).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Progress Bar
        ttk.Label(main_frame, text="Progress:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate'
        )
        self.progress.grid(row=5, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Status Label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="blue")
        self.status_label.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Buttons Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        self.download_btn = ttk.Button(
            button_frame,
            text="Download",
            command=self.start_download
        )
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_fields
        ).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
    
    def browse_directory(self):
        """Open directory browser"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)
    
    def clear_fields(self):
        """Clear all input fields"""
        self.url_entry.delete(0, tk.END)
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, "videos")
        self.status_label.config(text="Ready", foreground="blue")
        self.progress.stop()
    
    def start_download(self):
        """Start downloading in a separate thread"""
        url = self.url_entry.get().strip()
        
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
        
        if not ("youtube.com" in url or "youtu.be" in url):
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
        
        self.downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="Downloading...", foreground="orange")
        
        # Run download in separate thread
        thread = threading.Thread(
            target=self._download_thread,
            args=(url,)
        )
        thread.daemon = True
        thread.start()
    
    def _download_thread(self, url):
        """Download thread"""
        try:
            output_dir = self.output_entry.get()
            self.downloader = YouTubeDownloader(output_dir)
            
            success = self.downloader.download_video(
                url,
                format_type=self.format_var.get(),
                audio_only=self.audio_var.get()
            )
            
            if success:
                self.status_label.config(text="✓ Download completed!", foreground="green")
                messagebox.showinfo("Success", "Video downloaded successfully!")
            else:
                self.status_label.config(text="✗ Download failed", foreground="red")
                messagebox.showerror("Error", "Failed to download video")
        
        except Exception as e:
            self.status_label.config(text="✗ Error occurred", foreground="red")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        finally:
            self.progress.stop()
            self.download_btn.config(state=tk.NORMAL)
            self.downloading = False


def main():
    """Main GUI entry point"""
    root = tk.Tk()
    app = YouTubeDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
