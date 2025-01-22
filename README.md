# YouTube Video Transcriber

Downloads YouTube videos and creates transcriptions. Works locally or via GitHub Actions.

## Quick Start

1. Install dependencies:
```bash
pip install yt-dlp==2023.12.30 SpeechRecognition==3.10.0 pydub==0.25.1
# Install FFmpeg for your OS
```

2. Run:
```bash
python youtube_transcriber.py "YOUTUBE_URL" "LANGUAGE_CODE"
# Example:
python youtube_transcriber.py "https://youtube.com/watch?v=xxx" "he-IL"
```

## GitHub Actions

1. Fork repo
2. Go to Actions tab
3. Run workflow with YouTube URL
4. Download transcript from artifacts