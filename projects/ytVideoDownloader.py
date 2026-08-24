"""Download YouTube audio or video with yt-dlp."""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

try:
    from deno import find_deno_bin
except ImportError:
    find_deno_bin = None

OUTPUT_TEMPLATE = "%(title).180B [%(id)s].%(ext)s"
AUDIO_FORMATS = ("mp3", "m4a", "wav", "flac")
SUPPORTED_BROWSERS = (
    "brave",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "safari",
    "vivaldi",
    "whale",
)


@dataclass(frozen=True)
class DownloadRequest:
    """Normalized settings for a yt-dlp download."""

    urls: tuple[str, ...]
    audio: bool
    audio_format: str
    audio_quality: str
    resolution: int | None
    output_dir: Path
    allow_playlist: bool
    verbose: bool
    cookies_from_browser: str | None = None

    def __post_init__(self) -> None:
        """Normalize values supplied by direct callers and the command line."""
        object.__setattr__(self, "urls", tuple(url.strip() for url in self.urls if url.strip()))
        object.__setattr__(self, "audio_format", self.audio_format.lower())
        object.__setattr__(self, "audio_quality", str(self.audio_quality))
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        if self.cookies_from_browser is not None:
            object.__setattr__(self, "cookies_from_browser", self.cookies_from_browser.lower())

        if self.audio_format not in AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {self.audio_format}")
        if self.resolution is not None and self.resolution <= 0:
            raise ValueError("Resolution must be a positive number.")
        if self.cookies_from_browser not in {*SUPPORTED_BROWSERS, None}:
            raise ValueError(f"Unsupported browser: {self.cookies_from_browser}")


def find_deno_executable() -> str | None:
    """Find the managed Deno binary, with a system installation as fallback."""
    if find_deno_bin is not None:
        try:
            return str(find_deno_bin())
        except OSError:
            pass
    return shutil.which("deno")


def build_ydl_options(
    request: DownloadRequest,
    *,
    deno_path: str | None = None,
) -> dict[str, object]:
    """Build deterministic yt-dlp options without performing a download."""
    options: dict[str, object] = {
        "outtmpl": str(request.output_dir / OUTPUT_TEMPLATE),
        "noplaylist": not request.allow_playlist,
        "nooverwrites": True,
        "verbose": request.verbose,
    }
    if deno_path:
        options["js_runtimes"] = {"deno": {"path": deno_path}}
    if request.cookies_from_browser:
        options["cookiesfrombrowser"] = (request.cookies_from_browser,)

    if request.audio:
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": request.audio_format,
                "preferredquality": request.audio_quality,
                "nopostoverwrites": True,
            }
        ]
        return options

    if request.resolution is None:
        options["format"] = "bestvideo+bestaudio/best"
    else:
        options["format"] = (
            f"bestvideo[height<={request.resolution}]+bestaudio/best[height<={request.resolution}]"
        )
    return options


def download(request: DownloadRequest, *, deno_path: str | None = None) -> int:
    """Invoke yt-dlp and return a shell-compatible exit status."""
    active_deno_path = deno_path or find_deno_executable()
    if active_deno_path is None:
        print(
            "JavaScript-Laufzeit Deno fehlt. Starte Python Tools über den normalen Starter "
            "neu, damit die automatische Einrichtung ausgeführt wird.\n"
            "Deno JavaScript runtime is missing. Restart Python Tools with its normal starter "
            "so automatic setup can run.",
            file=sys.stderr,
        )
        return 1
    try:
        with YoutubeDL(build_ydl_options(request, deno_path=active_deno_path)) as ydl:
            return int(ydl.download(request.urls))
    except DownloadError as error:
        print(f"Download failed: {error}", file=sys.stderr)
        return 1


def _argument_parser() -> argparse.ArgumentParser:
    """Create the downloader command-line parser."""
    parser = argparse.ArgumentParser(description="Download YouTube audio or video with yt-dlp.")
    parser.add_argument(
        "urls", metavar="URL", nargs="*", help="One or more YouTube video or playlist URLs."
    )
    parser.add_argument(
        "-a", "--audio", action="store_true", help="Download audio instead of video."
    )
    parser.add_argument(
        "--audio-format",
        choices=AUDIO_FORMATS,
        default="mp3",
        help="Audio format to extract (default: mp3).",
    )
    parser.add_argument(
        "--audio-quality",
        default="192",
        help="FFmpeg audio quality value (default: 192).",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        help="Maximum video height, for example 1080.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("."),
        help="Directory for downloaded files (default: current directory).",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Ignore playlist context when a URL also identifies a video.",
    )
    parser.add_argument(
        "--cookies-from-browser",
        choices=SUPPORTED_BROWSERS,
        help="Use the signed-in session from this browser, for example for age restrictions.",
    )
    parser.add_argument("--verbose", action="store_true", help="Show yt-dlp debug output.")
    return parser


def _request_from_values(
    urls: Sequence[str],
    audio: bool,
    audio_format: str,
    audio_quality: str,
    resolution: int | None,
    output_dir: Path,
    single: bool,
    verbose: bool,
    cookies_from_browser: str | None,
) -> DownloadRequest:
    """Convert parsed command-line values into an immutable request."""
    return DownloadRequest(
        urls=tuple(urls),
        audio=audio,
        audio_format=audio_format,
        audio_quality=audio_quality,
        resolution=resolution,
        output_dir=output_dir,
        allow_playlist=not single,
        verbose=verbose,
        cookies_from_browser=cookies_from_browser,
    )


def _interactive_request(args: argparse.Namespace) -> DownloadRequest:
    """Collect the minimum request details when no URL was passed on the command line."""
    url = input("YouTube URL: ").strip()
    if not url:
        raise ValueError("A YouTube URL is required.")

    download_type = input("Download audio or video? [a/v]: ").strip().lower()
    if download_type in {"a", "audio"}:
        audio_format = input("Audio format [mp3/m4a/wav/flac] (mp3): ").strip() or "mp3"
        return _request_from_values(
            urls=(url,),
            audio=True,
            audio_format=audio_format,
            audio_quality=args.audio_quality,
            resolution=None,
            output_dir=args.output,
            single=args.single,
            verbose=args.verbose,
            cookies_from_browser=args.cookies_from_browser,
        )
    if download_type in {"v", "video"}:
        resolution_text = input("Maximum video height (blank for best): ").strip()
        resolution = int(resolution_text) if resolution_text else None
        return _request_from_values(
            urls=(url,),
            audio=False,
            audio_format=args.audio_format,
            audio_quality=args.audio_quality,
            resolution=resolution,
            output_dir=args.output,
            single=args.single,
            verbose=args.verbose,
            cookies_from_browser=args.cookies_from_browser,
        )
    raise ValueError("Choose 'a' for audio or 'v' for video.")


def parse_args(argv: Sequence[str] | None = None) -> DownloadRequest:
    """Parse command-line arguments and fall back to an interactive request."""
    args = _argument_parser().parse_args(argv)
    if not args.urls:
        return _interactive_request(args)
    return _request_from_values(
        urls=args.urls,
        audio=args.audio,
        audio_format=args.audio_format,
        audio_quality=args.audio_quality,
        resolution=args.resolution,
        output_dir=args.output,
        single=args.single,
        verbose=args.verbose,
        cookies_from_browser=args.cookies_from_browser,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the downloader command-line interface."""
    try:
        request = parse_args(argv)
    except ValueError as error:
        print(f"Invalid input: {error}", file=sys.stderr)
        return 2

    if shutil.which("ffmpeg") is None:
        print(
            "FFmpeg is required for audio conversion and video merging. Install it and try again.",
            file=sys.stderr,
        )
        return 1
    return download(request)


if __name__ == "__main__":
    raise SystemExit(main())
