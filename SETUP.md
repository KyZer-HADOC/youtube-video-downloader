# YouTube Video Downloader - Setup Guide

## 🚀 How to Create the Desktop App

### Step 1: Install Python
- Download Python from https://www.python.org/
- **Important:** Check "Add Python to PATH" during installation
- Verify installation: Open Command Prompt and type `python --version`

### Step 2: Download/Clone Repository
```bash
git clone https://github.com/KyZer-HADOC/youtube-video-downloader.git
cd youtube-video-downloader
```

### Step 3: Build the App

#### **Windows Users:**
1. Double-click `build.bat`
2. Wait for the build to complete
3. Find your executable in the `dist` folder
4. Create a shortcut on your desktop for easy access

#### **macOS/Linux Users:**
```bash
chmod +x build.sh
./build.sh
```

Or manually:
```bash
pip install -r requirements.txt
python3 build.py
```

### Step 4: Run the App

**Windows:**
- Go to the `dist` folder
- Double-click `YouTubeVideoDownloader.exe`
- Create a shortcut and pin to taskbar if desired

**macOS:**
- Go to the `dist` folder
- Double-click `YouTubeVideoDownloader`
- Or drag it to Applications folder

**Linux:**
- Go to the `dist` folder
- Run `./YouTubeVideoDownloader`

---

## ✨ App Features

✅ Download YouTube videos in multiple formats
✅ Extract audio as MP3
✅ Choose video quality (Best, 1080p, 720p)
✅ Modern graphical interface
✅ Progress tracking
✅ Easy folder navigation
✅ No command-line knowledge needed

---

## 📋 System Requirements

- **Windows:** Windows 7 or later
- **macOS:** macOS 10.9 or later
- **Linux:** Most distributions
- **FFmpeg:** Required for audio conversion
  - Windows: Download from https://ffmpeg.org/download.html
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`

---

## 🎯 Quick Start

1. **Paste YouTube URL** in the URL field
2. **Select video format** (Best Quality recommended)
3. **Choose output location** (defaults to Downloads)
4. **Click Download** and wait for completion
5. **Check the output folder** for your downloaded video

---

## ⚙️ Troubleshooting

### "FFmpeg not found"
- Install FFmpeg from https://ffmpeg.org/download.html
- Make sure it's in your system PATH

### "Python not found"
- Install Python from https://www.python.org/
- Make sure to check "Add Python to PATH"

### Build fails
- Delete the `build` and `dist` folders
- Try running the build script again
- Make sure you have enough disk space

### Video won't download
- Check if the URL is valid
- Some videos might be region-locked or private
- Try updating yt-dlp: `pip install --upgrade yt-dlp`

---

## 📝 Advanced Options (CLI)

If you prefer command-line, use:
```bash
python downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -f 720p
```

Options:
- `-f best` - Best quality
- `-f 720p` - 720p HD
- `-f 1080p` - 1080p HD
- `-f mp3` - Audio only
- `-o ./path` - Custom output folder

---

## 🔗 Useful Links

- FFmpeg Download: https://ffmpeg.org/download.html
- Python Download: https://www.python.org/
- GitHub Repository: https://github.com/KyZer-HADOC/youtube-video-downloader
- yt-dlp Documentation: https://github.com/yt-dlp/yt-dlp

---

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Create an issue on GitHub
3. Make sure all dependencies are installed

---

**Enjoy downloading your favorite YouTube videos!** 🎬📥
