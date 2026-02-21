# Termux Setup Guide

This guide helps you run the **grahakchetna** project on Termux (Android terminal emulator).

## Prerequisites & Limitations

⚠️ **Important Notes:**
- **Video Processing**: `moviepy` + `ffmpeg` on Termux may be slower or have limitations compared to desktop.
- **Storage**: Ensure you have at least 2GB free space for dependencies + generated videos.
- **Low RAM devices**: Generating videos may fail on devices with <2GB RAM.
- **Git LFS**: Not available in standard Termux. Use workaround below.

---

## Step 1: Install System Dependencies

```bash
pkg update
pkg upgrade
pkg install python3 git ffmpeg imagemagick libjpeg-turbo libpng git-lfs
```

**What each package does:**
- `python3` – Python runtime
- `git` – Version control
- `ffmpeg` – Video/audio encoding (critical for moviepy)
- `imagemagick` – Image processing support
- `libjpeg-turbo`, `libpng` – Image library dependencies for Pillow
- `git-lfs` – Git Large File Storage (for assets folder)

---

## Step 2: Clone the Repository

```bash
git clone https://github.com/gaathatech/grahakchetna.git
cd grahakchetna
```

---

## Step 3: Handle Git LFS Assets

Since `git-lfs` on Termux may have limited support, **skip LFS and get assets manually:**

### Option A: Download Assets Directly (Easiest)
```bash
# Create assets folder if missing
mkdir -p assets

# Download media files manually (replace with your actual URLs or use scp/rsync from desktop)
# Example using curl (if hosted on GitHub releases or cloud):
curl -o assets/bg.mp4 "https://github.com/gaathatech/grahakchetna/releases/download/v1.0/bg.mp4"
curl -o assets/music.mp3 "https://github.com/gaathatech/grahakchetna/releases/download/v1.0/music.mp3"
```

### Option B: Copy from Desktop via scp
```bash
# On your desktop/laptop, run:
scp assets/* user@YOUR_PHONE_IP:/path/to/grahakchetna/assets/

# Or use rsync (faster for multiple files):
rsync -avz assets/ user@YOUR_PHONE_IP:/path/to/grahakchetna/assets/
```

### Option C: Use Git LFS (if available)
```bash
git lfs install
git lfs pull
```

---

## Step 4: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Troubleshooting slow installs:**
- Add `--no-cache-dir` flag to speed up pip: `pip install --no-cache-dir -r requirements.txt`
- If `Pillow` fails: `pip install Pillow --no-binary :all: --force-reinstall` (slower but may work)

---

## Step 5: Setup Environment Variables

```bash
# Create .env file (use your API key)
cat > .env << 'EOF'
# Add your API keys here
GROQ_API_KEY=your-key-here
EOF

chmod 600 .env  # Secure the file
```

---

## Step 6: Run the Application

```bash
# Development server (localhost:5000)
python3 app.py

# In another Termux session, test the API:
curl http://localhost:5000/
```

---

## Performance Tips for Termux

1. **Use smaller videos/images**: Large media files slow down processing.
2. **Batch processing**: Generate multiple videos in sequence, not parallel.
3. **Monitor RAM**: Use `free -h` to check available memory.
4. **Run at night**: Avoid resource-heavy video generation during daily usage.

---

## Common Termux Issues & Fixes

### ❌ `ffmpeg` not found
```bash
pkg install ffmpeg
```

### ❌ `Pillow` installation fails
```bash
pip install Pillow --no-binary :all:
```

### ❌ Permission denied on directories
```bash
chmod -R 755 output/
chmod -R 755 videos/
```

### ❌ Out of storage space
```bash
# Check storage
df -h
# Clear cache
rm -rf ~/.cache/pip/
pkg autoclean
```

### ❌ Assets folder still missing after git pull
```bash
# Manually create it
mkdir -p assets
# Then copy/download media files using Option A or B above
```

---

## Publishing Assets to GitHub

If you want to make assets easily available on Termux without Git LFS:

### Method 1: GitHub Releases
1. Go to your repo → **Releases** → **Create new release**
2. Upload `assets/bg.mp4` and `assets/music.mp3`
3. Share release URL for easy download

### Method 2: Cloud Storage
1. Upload assets to Google Drive, Dropbox, or AWS S3
2. Share a simple script that downloads them

---

## Next Steps

- See [README.md](README.md) for app usage
- See [QUICK_START.md](QUICK_START.md) for API examples
- For issues, check the main repository: https://github.com/gaathatech/grahakchetna

---

**Last Updated:** February 16, 2026
