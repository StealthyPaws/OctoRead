# 🚀 Deployment Guide — OctoRead

## Streamlit Cloud (Recommended)

### Prerequisites
- GitHub account
- Streamlit Cloud account (free at share.streamlit.io)

### Steps

**1. Push to GitHub**
```bash
git init
git add .
git commit -m "Initial OctoRead deployment"
git remote add origin https://github.com/YOUR_USERNAME/octoread.git
git push -u origin main
```

**2. Connect to Streamlit Cloud**
1. Go to https://share.streamlit.io
2. Click "New app"
3. Select your repository
4. Set **Main file path** to `app.py`
5. Click **Deploy**

**3. System packages (Tesseract)**

Streamlit Cloud reads `packages.txt` automatically. Your file should contain:
```
tesseract-ocr
tesseract-ocr-eng
libtesseract-dev
libgl1-mesa-glx
libglib2.0-0
```

This installs Tesseract OCR on the cloud server before your app starts.

**4. Python packages**

`requirements.txt` is also read automatically. No extra steps needed.

---

## Local Development

### macOS
```bash
brew install tesseract
pip install -r requirements.txt
streamlit run app.py
```

### Ubuntu / Debian
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng libtesseract-dev
pip install -r requirements.txt
streamlit run app.py
```

### Windows
1. Download Tesseract installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Add Tesseract to PATH
3. Run:
```bash
pip install -r requirements.txt
streamlit run app.py
```
If Tesseract is installed to a non-default path on Windows, add this to `strategy_agent.py`:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## Common Errors & Fixes

### `TesseractNotFoundError`
**Cause:** Tesseract binary not in PATH.
**Fix:**
- Linux: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`
- Windows: install binary and set `tesseract_cmd` path in code

### `cv2` import error on Streamlit Cloud
**Cause:** Wrong OpenCV package.
**Fix:** Make sure `requirements.txt` uses `opencv-python-headless` (not `opencv-python`). The headless version works without a display server.

### `libGL.so.1` not found
**Cause:** Missing system lib for OpenCV.
**Fix:** Add `libgl1-mesa-glx` to `packages.txt`.

### App crashes on large images
**Cause:** Memory limit on free Streamlit Cloud tier.
**Fix:** The UpscaleStrategy only upscales images smaller than 1000px. Large images skip upscaling.

### LLM Enhancement not working
**Cause:** No Anthropic API key provided, or key expired.
**Fix:** Enter a valid `sk-ant-...` key in the UI toggle, or leave LLM Enhancement off.

### `ImportError: python-docx`
**Cause:** python-docx not installed.
**Fix:** Ensure `python-docx>=1.1.0` is in `requirements.txt`. The .docx export button will silently hide itself if this package is missing.

---

## Environment Variables (Optional)

If you want to pre-set the Anthropic API key instead of entering it in the UI, set a Streamlit secret:

1. In Streamlit Cloud dashboard → App → Settings → Secrets
2. Add:
```toml
[secrets]
ANTHROPIC_API_KEY = "sk-ant-..."
```
3. In `user_agent.py`, read it with:
```python
import streamlit as st
api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
```
