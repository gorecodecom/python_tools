"""Tests for the yt-dlp downloader boundary and command-line interface."""

from pathlib import Path
from typing import Self

import pytest
from yt_dlp.utils import DownloadError

from projects import ytVideoDownloader as downloader


def make_request(**overrides: object) -> downloader.DownloadRequest:
    """Build a download request with stable defaults for option tests."""
    values: dict[str, object] = {
        "urls": ("https://example.com/watch?v=video",),
        "audio": False,
        "audio_format": "mp3",
        "audio_quality": "192",
        "resolution": None,
        "output_dir": Path("downloads"),
        "allow_playlist": True,
        "verbose": False,
    }
    values.update(overrides)
    return downloader.DownloadRequest(**values)


def test_mp3_request_uses_mp3_audio_postprocessor() -> None:
    """Audio downloads must ask FFmpeg to extract the selected MP3 codec."""
    options = downloader.build_ydl_options(make_request(audio=True, audio_format="mp3"))

    assert options["format"] == "bestaudio/best"
    assert options["postprocessors"] == [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
            "nopostoverwrites": True,
        }
    ]


def test_wav_request_uses_wav_audio_postprocessor() -> None:
    """Changing the requested audio format must change the FFmpeg codec."""
    options = downloader.build_ydl_options(make_request(audio=True, audio_format="wav"))

    assert options["postprocessors"][0]["preferredcodec"] == "wav"


def test_audio_postprocessor_never_overwrites_existing_converted_files() -> None:
    """FFmpeg conversion must preserve an existing final audio file."""
    options = downloader.build_ydl_options(make_request(audio=True))

    assert options["postprocessors"][0]["nopostoverwrites"] is True


def test_1080p_video_request_has_no_unrestricted_fallback() -> None:
    """Every video fallback must preserve the requested maximum height."""
    options = downloader.build_ydl_options(make_request(resolution=1080))

    assert options["format"] == "bestvideo[height<=1080]+bestaudio/best[height<=1080]"


def test_options_allow_playlists_and_never_overwrite_existing_files() -> None:
    """The default request preserves playlists and existing user files."""
    options = downloader.build_ydl_options(make_request())

    assert options["noplaylist"] is False
    assert options["nooverwrites"] is True
    assert options["outtmpl"].endswith("%(title).180B [%(id)s].%(ext)s")


def test_single_option_disables_playlist_downloads() -> None:
    """The explicit single-item flag must opt out of playlist expansion."""
    request = downloader.parse_args(["--single", "https://example.com/watch?v=video"])

    assert request.allow_playlist is False


def test_browser_session_is_passed_to_yt_dlp_for_age_restricted_videos() -> None:
    """An explicitly selected browser must provide its signed-in session to yt-dlp."""
    request = downloader.parse_args(
        [
            "--cookies-from-browser",
            "safari",
            "https://example.com/watch?v=age-restricted",
        ]
    )

    assert downloader.build_ydl_options(request)["cookiesfrombrowser"] == ("safari",)


def test_managed_deno_runtime_is_passed_to_yt_dlp_for_youtube_challenges() -> None:
    """YouTube extraction must use the Deno binary installed with Python Tools."""
    options = downloader.build_ydl_options(
        make_request(),
        deno_path="/managed/python-tools/deno",
    )

    assert options["js_runtimes"] == {
        "deno": {"path": "/managed/python-tools/deno"},
    }


def test_parse_args_normalizes_multiple_audio_urls() -> None:
    """CLI audio settings and multiple positional URLs become one immutable request."""
    request = downloader.parse_args(
        [
            "--audio",
            "--audio-format",
            "flac",
            "--audio-quality",
            "256",
            "--output",
            "saved-media",
            "https://example.com/watch?v=one",
            "https://example.com/watch?v=two",
        ]
    )

    assert request.urls == (
        "https://example.com/watch?v=one",
        "https://example.com/watch?v=two",
    )
    assert request.audio is True
    assert request.audio_format == "flac"
    assert request.audio_quality == "256"
    assert request.output_dir == Path("saved-media")
    assert request.allow_playlist is True
    assert request.__dataclass_params__.frozen is True


def test_parse_args_prompts_for_a_video_request_without_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No positional URLs must construct a request through the short prompt flow."""
    answers = iter(["https://example.com/watch?v=video", "v", "720"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    request = downloader.parse_args([])

    assert request.urls == ("https://example.com/watch?v=video",)
    assert request.audio is False
    assert request.resolution == 720


def test_download_passes_real_options_to_yt_dlp_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The network boundary receives the built options and complete URL list."""
    received: dict[str, object] = {}

    class FakeYoutubeDL:
        def __init__(self, options: dict[str, object]) -> None:
            received["options"] = options

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def download(self, urls: tuple[str, ...]) -> int:
            received["urls"] = urls
            return 0

    monkeypatch.setattr(downloader, "YoutubeDL", FakeYoutubeDL)
    request = make_request(urls=("https://example.com/one", "https://example.com/two"))

    assert downloader.download(request, deno_path="/managed/python-tools/deno") == 0
    assert received["urls"] == request.urls
    assert received["options"] == downloader.build_ydl_options(
        request,
        deno_path="/managed/python-tools/deno",
    )


def test_download_returns_nonzero_for_yt_dlp_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Network failures must become a concise, non-zero CLI outcome."""

    class FailingYoutubeDL:
        def __init__(self, _options: dict[str, object]) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def download(self, _urls: tuple[str, ...]) -> int:
            raise DownloadError("source is unavailable")

    monkeypatch.setattr(downloader, "YoutubeDL", FailingYoutubeDL)

    assert downloader.download(make_request(), deno_path="/managed/python-tools/deno") == 1
    assert "Download failed: source is unavailable" in capsys.readouterr().err


def test_download_stops_with_clear_message_when_deno_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing JS runtime must fail clearly before yt-dlp attempts a download."""

    class FakeYoutubeDL:
        def __init__(self, _options: dict[str, object]) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def download(self, _urls: tuple[str, ...]) -> int:
            return 0

    monkeypatch.setattr(downloader, "YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr(downloader, "find_deno_executable", lambda: None, raising=False)

    assert downloader.download(make_request()) == 1
    error_output = capsys.readouterr().err
    assert "JavaScript-Laufzeit Deno fehlt" in error_output
    assert "Deno JavaScript runtime is missing" in error_output
