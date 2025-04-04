import os
import re
import logging
from typing import Optional, Tuple
from pathlib import Path
from tqdm import tqdm
from pytubefix import YouTube, Playlist
from pytubefix.exceptions import PytubeFixError
from pydub import AudioSegment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YouTubeDownloader:
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the downloader with an optional output directory."""
        self.output_dir = output_dir or os.getcwd()
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def is_valid_link(self, link: str) -> bool:
        """Validate if the provided link is a valid YouTube URL."""
        youtube_regex = (
            r'(https?://)?(www\.)?'
            '(youtube|youtu|youtube-nocookie)\.(com|be)/'
            '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(re.match(youtube_regex, link))

    def is_playlist(self, link: str) -> bool:
        """Check if the link is a YouTube playlist."""
        return 'playlist' in link

    def on_progress(self, stream, chunk: bytes, bytes_remaining: int):
        """Callback function to update download progress."""
        if not hasattr(self, 'progress_bar'):
            self.progress_bar = tqdm(
                total=stream.filesize,
                unit='iB',
                unit_scale=True
            )
        self.progress_bar.update(len(chunk))

    def download_video(self, yt: YouTube, resolution: Optional[str] = None) -> Optional[str]:
        """Download video with specified resolution or highest available."""
        try:
            if resolution:
                stream = yt.streams.filter(res=resolution).first()
            else:
                stream = yt.streams.get_highest_resolution()

            if not stream:
                logger.warning("Requested resolution not available. Using highest available.")
                stream = yt.streams.get_highest_resolution()

            logger.info(f"Downloading video: {yt.title}")
            out_file = stream.download(output_path=self.output_dir)
            return out_file
        except PytubeFixError as e:
            logger.error(f"Error downloading video: {str(e)}")
            return None

    def download_audio(self, yt: YouTube, audio_format: str = 'mp3') -> Optional[str]:
        """Download and convert audio to specified format."""
        try:
            stream = yt.streams.get_audio_only()
            if not stream:
                logger.error("No audio stream available")
                return None

            logger.info(f"Downloading audio: {yt.title}")
            temp_file = stream.download(
                output_path=self.output_dir,
                filename_prefix="temp_audio_"
            )

            # Convert to desired audio format
            output_path = os.path.join(
                self.output_dir,
                f"{yt.title}.{audio_format}"
            )
            
            # Convert to MP3 using pydub
            audio = AudioSegment.from_file(temp_file)
            audio.export(output_path, format="mp3")
            
            # Clean up temporary file
            os.remove(temp_file)
            return output_path
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            return None

    def process_playlist(self, playlist_url: str, download_type: str, **kwargs) -> None:
        """Process all videos in a playlist."""
        try:
            playlist = Playlist(playlist_url)
            logger.info(f"Downloading playlist: {playlist.title}")
            
            for video_url in playlist.video_urls:
                self.process_single_video(video_url, download_type, **kwargs)
        except Exception as e:
            logger.error(f"Error processing playlist: {str(e)}")

    def process_single_video(self, video_url: str, download_type: str, **kwargs) -> Optional[str]:
        """Process a single video URL."""
        try:
            yt = YouTube(
                video_url,
                on_progress_callback=self.on_progress
            )
            
            if download_type == 'v':
                return self.download_video(yt, kwargs.get('resolution'))
            elif download_type == 'a':
                return self.download_audio(yt, kwargs.get('audio_format', 'mp3'))
            else:
                logger.error("Invalid download type specified")
                return None
                
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            return None

def main():
    downloader = YouTubeDownloader()
    
    while True:
        try:
            link = input("\nEnter YouTube video/playlist URL (or 'exit' to quit): ").strip()
            if link.lower() == 'exit':
                break

            if not downloader.is_valid_link(link):
                logger.error("Invalid YouTube URL. Please try again.")
                continue

            download_type = input("Download type - Video (V) or Audio (A): ").lower()
            if download_type not in ['v', 'a']:
                logger.error("Invalid download type. Please enter 'V' or 'A'.")
                continue

            if download_type == 'v':
                resolution = input("Enter desired resolution (e.g., 720p, 1080p) or press Enter for highest: ").strip()
                kwargs = {'resolution': resolution if resolution else None}
            else:
                audio_format = input("Enter audio format (mp3/wav) or press Enter for mp3: ").strip() or 'mp3'
                kwargs = {'audio_format': audio_format}

            if downloader.is_playlist(link):
                downloader.process_playlist(link, download_type, **kwargs)
            else:
                result = downloader.process_single_video(link, download_type, **kwargs)
                if result:
                    logger.info(f"Download completed: {result}")

        except KeyboardInterrupt:
            logger.info("\nDownload cancelled by user.")
            break
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
