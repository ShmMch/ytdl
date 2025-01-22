# youtube_transcriber.py

import os
import sys
import logging
import tempfile
import time
import random
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import traceback

# Third-party imports
import yt_dlp
import speech_recognition as sr
from pydub import AudioSegment

@dataclass
class Config:
    """Configuration settings for the application"""
    DEFAULT_LANGUAGE: str = 'he-IL'
    CHUNK_DURATION_MS: int = 60000
    API_RETRY_ATTEMPTS: int = 3
    API_RETRY_DELAY: int = 2
    
    def __post_init__(self):
        self.OUTPUT_DIR, self.TEMP_DIR = self.setup_github_paths()
        # Create directories
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.TEMP_DIR, exist_ok=True)

    def setup_github_paths(self):
        """Configure paths for GitHub Actions environment"""
        workspace = os.getenv('GITHUB_WORKSPACE', os.getcwd())
        output_dir = os.path.join(workspace, 'downloads')
        temp_dir = os.path.join(output_dir, 'temp')
        return output_dir, temp_dir

    def cleanup(self):
        """Clean up temporary files"""
        try:
            for file in os.listdir(self.TEMP_DIR):
                file_path = os.path.join(self.TEMP_DIR, file)
                if os.path.isfile(file_path):
                    try:
                        os.unlink(file_path)
                    except Exception as e:
                        logging.error(f"Error deleting file {file_path}: {e}")
        except Exception as e:
            logging.error(f"Error cleaning up files: {e}")

class TranscriptionError(Exception):
    """Custom exception for transcription-related errors"""
    pass

class URLError(Exception):
    """Custom exception for URL-related errors"""
    pass

def setup_logging() -> logging.Logger:
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('youtube_transcription.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def validate_url(url: str) -> bool:
    """Validate YouTube URL format"""
    if not url.startswith(('http://', 'https://')):
        raise URLError("Invalid URL format")
    if 'youtube.com' not in url and 'youtu.be' not in url:
        raise URLError("Not a YouTube URL")
    return True

def safe_filename(filename: str) -> str:
    """Create safe filename from potentially unsafe string"""
    return "".join(char for char in filename 
                  if char.isalnum() or char in "._- ").rstrip()

class ProxyRotator:
    def __init__(self):
        # Add your proxy list here if you have them
        self.proxy_list = [
            # Example proxies - replace with real ones if you have them
            # 'http://proxy1.example.com:8080',
            # 'http://proxy2.example.com:8080',
        ]
        
    def get_proxy(self):
        """Get a random proxy from the list"""
        if self.proxy_list:
            return random.choice(self.proxy_list)
        return None

class VideoDownloader:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging()
        self.proxy_rotator = ProxyRotator()

    def _get_download_options(self, output_template: str) -> dict:
        """Get download options with randomized user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
        ]

        ydl_opts = {
            'outtmpl': output_template,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'socket_timeout': 30,
            'retries': 10,
            'writethumbnail': False,
            'quiet': False,
            'no_warnings': True,
            'progress_hooks': [self._progress_hook],
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'noplaylist': True,
            'extract_flat': False,
            'extractor_retries': 5,
            'file_access_retries': 5,
            'fragment_retries': 10,
            'retry_sleep_functions': {'http': lambda n: 5 * (n + 1)},
            'http_headers': {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '115',
                'Connection': 'keep-alive',
            }
        }

        # Add proxy if available
        proxy = self.proxy_rotator.get_proxy()
        if proxy:
            ydl_opts['proxy'] = proxy

        return ydl_opts

    def download_video(self, url: str) -> Optional[str]:
        """Download video and extract audio with bot check bypass attempts"""
        try:
            validate_url(url)
            
            temp_filename = f'video_{int(time.time())}'
            output_template = os.path.join(self.config.OUTPUT_DIR, temp_filename)

            for attempt in range(3):  # Try 3 times with different approaches
                try:
                    # Get fresh options for each attempt
                    ydl_opts = self._get_download_options(output_template)
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        self.logger.info(f"Download attempt {attempt + 1} for {url}")
                        
                        # Try to get video info first
                        info = ydl.extract_info(url, download=False)
                        if not info:
                            raise TranscriptionError("Could not retrieve video information")
                        
                        # If successful, proceed with download
                        info = ydl.extract_info(url, download=True)
                        self.logger.info(f"Video title: {info.get('title', 'Unknown')}")
                        
                        # Look for the downloaded WAV file
                        expected_wav_file = f"{output_template}.wav"
                        if os.path.exists(expected_wav_file):
                            return expected_wav_file

                        # Fallback: search for any WAV file
                        wav_files = [f for f in os.listdir(self.config.OUTPUT_DIR) 
                                   if f.endswith('.wav')]
                        if wav_files:
                            latest_wav = max(wav_files, 
                                           key=lambda x: os.path.getctime(
                                               os.path.join(self.config.OUTPUT_DIR, x)))
                            return os.path.join(self.config.OUTPUT_DIR, latest_wav)

                except yt_dlp.utils.DownloadError as e:
                    error_message = str(e).lower()
                    self.logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                    
                    if attempt < 2:  # Don't sleep on last attempt
                        if "sign in to confirm you're not a bot" in error_message:
                            time.sleep((attempt + 1) * 5)
                        elif "rate limit" in error_message:
                            time.sleep((attempt + 1) * 10)
                        else:
                            time.sleep(attempt + 1)
                    
                    if attempt == 2:  # Last attempt failed
                        raise

            return None

        except Exception as e:
            self.logger.error(f"Download error: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None
   
class YouTubeTranscriber:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging()

    def safe_transcribe(self, audio_chunk: sr.AudioData, recognizer: sr.Recognizer, 
                       language: str) -> str:
        """Safely transcribe audio with retries"""
        for attempt in range(self.config.API_RETRY_ATTEMPTS):
            try:
                return recognizer.recognize_google(audio_chunk, language=language)
            except sr.RequestError as e:
                if attempt == self.config.API_RETRY_ATTEMPTS - 1:
                    raise TranscriptionError(
                        f"Failed after {self.config.API_RETRY_ATTEMPTS} attempts: {e}")
                time.sleep(self.config.API_RETRY_DELAY ** attempt)
            except sr.UnknownValueError:
                return "[inaudible]"

    def transcribe_large_audio(self, audio_path: str, language: str) -> Optional[str]:
        """Transcribe large audio file by splitting into chunks"""
        recognizer = sr.Recognizer()
        transcript_parts = []

        try:
            audio = AudioSegment.from_wav(audio_path)
            total_chunks = len(audio) // self.config.CHUNK_DURATION_MS + 1

            for i in range(0, len(audio), self.config.CHUNK_DURATION_MS):
                self.logger.info(
                    f"Processing chunk {i//self.config.CHUNK_DURATION_MS + 1} of {total_chunks}")
                
                chunk = audio[i:i + self.config.CHUNK_DURATION_MS]
                chunk_path = os.path.join(self.config.TEMP_DIR, f'chunk_{i}.wav')
                
                try:
                    chunk.export(
                        chunk_path,
                        format='wav',
                        parameters=['-ar', '16000', '-ac', '1', '-bits_per_raw_sample', '16']
                    )

                    with sr.AudioFile(chunk_path) as source:
                        audio_chunk = recognizer.record(source)
                    
                    chunk_transcript = self.safe_transcribe(audio_chunk, recognizer, language)
                    transcript_parts.append(chunk_transcript)

                except Exception as chunk_error:
                    self.logger.error(
                        f"Error processing chunk {i//self.config.CHUNK_DURATION_MS + 1}: {chunk_error}")
                    transcript_parts.append("[Error transcribing this section]")
                
                finally:
                    # Clean up chunk file
                    if os.path.exists(chunk_path):
                        try:
                            os.remove(chunk_path)
                        except Exception as e:
                            self.logger.warning(f"Could not remove temporary file {chunk_path}: {e}")
                
                time.sleep(1)  # Rate limiting

            full_transcript = ' '.join(transcript_parts)
            
            # Save transcript
            transcript_file = os.path.splitext(audio_path)[0] + '_transcript.txt'
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(full_transcript)
            
            self.logger.info(f"Full transcript saved to {transcript_file}")
            return full_transcript

        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            self.logger.error(traceback.format_exc())
            return None

    def process_video(self, video_url: str, language: Optional[str] = None) -> Optional[str]:
        """Process video from URL to transcript"""
        try:
            validate_url(video_url)
            language = language or self.config.DEFAULT_LANGUAGE
            
            downloader = VideoDownloader(self.config)
            audio_path = downloader.download_video(video_url)
            
            if not audio_path:
                raise TranscriptionError("Audio download failed")
                
            self.logger.info(f'Processing audio file: {audio_path}')
            return self.transcribe_large_audio(audio_path, language)

        except Exception as e:
            self.logger.error(f"Video processing error: {e}")
            self.logger.error(traceback.format_exc())
            return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <YouTube_URL> [language_code]")
        sys.exit(1)
    
    video_url = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        config = Config()
        transcriber = YouTubeTranscriber(config)
        
        # Clean up before starting
        config.cleanup()
        
        result = transcriber.process_video(video_url, language)
        
        if result:
            print("\nTranscription successful!")
            print("\nTranscript Preview:")
            print(result[:500] + "..." if len(result) > 500 else result)
        else:
            print("Failed to transcribe the video.")
            sys.exit(1)
            
        # Clean up after completion
        config.cleanup()
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
