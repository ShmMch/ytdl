import yt_dlp
import argparse
from pathlib import Path
import logging
import browser_cookie3
import tempfile
import http.cookiejar
import os

class VideoDownloader:
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _get_browser_cookies(self, browser='chrome'):
        """
        Extracts cookies from browser and saves them to a temporary file.
        
        Args:
            browser (str): Browser to extract cookies from ('chrome', 'firefox', 'opera', 'edge')
        
        Returns:
            str: Path to temporary cookies file
        """
        try:
            # Get the appropriate browser's cookies
            cookie_extractor = {
                'chrome': browser_cookie3.chrome,
                'firefox': browser_cookie3.firefox,
                'opera': browser_cookie3.opera,
                'edge': browser_cookie3.edge
            }
            
            if browser not in cookie_extractor:
                self.logger.error(f"Unsupported browser: {browser}")
                return None
                
            # Create temporary file for cookies
            cookie_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
            cookie_path = cookie_file.name
            
            # Extract and save cookies
            cj = cookie_extractor[browser](domain_name='youtube.com')
            
            with open(cookie_path, 'w', encoding='utf-8') as f:
                for cookie in cj:
                    # Write in Netscape cookie file format
                    f.write(f"{cookie.domain}\tTRUE\t{cookie.path}\t"
                           f"{'TRUE' if cookie.secure else 'FALSE'}\t{cookie.expires}\t"
                           f"{cookie.name}\t{cookie.value}\n")
            
            return cookie_path
            
        except Exception as e:
            self.logger.error(f"Error extracting cookies: {str(e)}")
            return None

    def download_video(self, url, browser='chrome', audio=False):
        """
        Downloads a video from the provided URL.
        
        Args:
            url (str): The URL of the video to download
            browser (str): Browser to extract cookies from
        """
        cookie_file = None
        try:
            # Get cookies from browser
            cookie_file = self._get_browser_cookies(browser)
            
            if not cookie_file:
                self.logger.warning("Could not extract cookies, attempting download without them...")
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',  
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                
                # # Post processing
                
                'extractaudio': True if audio else False,      
                'audioquality': 0,       
                'audioformat': 'mp3',   
                # Download options
                'nocheckcertificate': True,
                'no_warnings': False,
                'verbose': True,
                'progress_hooks': [self._progress_hook],
                'ignoreerrors': False,
                
                # Headers
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            }

            # Add cookies if available
            if cookie_file:
                ydl_opts['cookiefile'] = cookie_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info(f"Starting download of {url}")
                
                # Get video info
                self.logger.info("Retrieving video information...")
                info = ydl.extract_info(url, download=False)
                
                if info:
                    self.logger.info(f"Video title: {info.get('title', 'Unknown')}")
                    self.logger.info(f"Duration: {info.get('duration', 'Unknown')} seconds")
                    
                    # Download
                    error_code = ydl.download([url])
                    
                    if error_code != 0:
                        self.logger.error(f"Download failed with error code {error_code}")
                        return False
                        
                    self.logger.info("Download completed successfully")
                    return True
                else:
                    self.logger.error("Could not retrieve video information")
                    return False

        except yt_dlp.utils.DownloadError as e:
            self.logger.error(f"Download error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"An error occurred: {str(e)}")
            return False
        finally:
            # Clean up temporary cookie file
            if cookie_file and os.path.exists(cookie_file):
                try:
                    os.unlink(cookie_file)
                except Exception:
                    pass

    def _progress_hook(self, d):
        """Displays download progress"""
        if d['status'] == 'downloading':
            try:
                if 'total_bytes' in d:
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d['total_bytes']
                    percentage = (downloaded / total) * 100
                    self.logger.info(f"Download progress: {percentage:.1f}%")
                elif 'downloaded_bytes' in d:
                    self.logger.info(f"Downloaded: {d['downloaded_bytes'] / 1024 / 1024:.1f} MB")
            except Exception:
                pass
        elif d['status'] == 'finished':
            self.logger.info(f"Download finished: {d['filename']}")
        elif d['status'] == 'error':
            self.logger.error(f"Error downloading: {d.get('error_message', 'Unknown error')}")

def main():
    parser = argparse.ArgumentParser(description='Download YouTube videos')
    parser.add_argument('url', help='URL of the video to download')
    parser.add_argument('--output-dir', default='downloads', 
                        help='Directory to save downloads (default: downloads)')
    parser.add_argument('--browser', default='chrome',
                        choices=['chrome', 'firefox', 'opera', 'edge'],
                        help='Browser to extract cookies from (default: chrome)')
    parser.add_argument('--audio', help='Download only audio')

    args = parser.parse_args()
    
    downloader = VideoDownloader(output_dir=args.output_dir)
    success = downloader.download_video(args.url, browser=args.browser, audio = args.audio)
    
    if not success:
        exit(1)

if __name__ == "__main__":
    main()
