"""Behavior tests for the cross-platform guided launcher."""

from __future__ import annotations

from pathlib import Path

from projects import launcher


class AnswerSequence:
    """Provide deterministic answers to an interactive prompt sequence."""

    def __init__(self, *answers: str) -> None:
        self._answers = iter(answers)

    def __call__(self, _prompt: str) -> str:
        return next(self._answers)


def make_console(*answers: str, language: str = "de") -> launcher.Console:
    """Create a silent console backed by a fixed answer sequence."""
    return launcher.Console(
        language=language,
        input_fn=AnswerSequence(*answers),
        output_fn=lambda _message="": None,
    )


def test_language_from_locale_selects_german_only_for_german_locales() -> None:
    """Non-German systems must receive the English interface by default."""
    assert launcher.language_from_locale("de_DE.UTF-8") == "de"
    assert launcher.language_from_locale("de-AT") == "de"
    assert launcher.language_from_locale("de") == "de"
    assert launcher.language_from_locale("en_US.UTF-8") == "en"
    assert launcher.language_from_locale(None) == "en"


def test_language_preference_round_trip_and_invalid_fallback(tmp_path: Path) -> None:
    """A valid saved preference must persist while corrupt values use the fallback."""
    preference = tmp_path / "language"

    launcher.save_language(preference, "en")
    assert launcher.load_language(preference, "de") == "en"

    preference.write_text("not-a-language", encoding="utf-8")
    assert launcher.load_language(preference, "de") == "de"


def test_audio_wizard_exposes_format_quality_output_and_single_video_mode() -> None:
    """The guided audio flow must map every downloader audio option to CLI arguments."""
    console = make_console(
        "https://example.com/watch?v=one",
        "https://example.com/watch?v=two",
        "",
        "flac",
        "256",
        "~/Music",
        "n",
        "y",
    )

    arguments = launcher.collect_audio_arguments(console, home=Path("/home/alex"))

    assert arguments == [
        "--audio",
        "--audio-format",
        "flac",
        "--audio-quality",
        "256",
        "--output",
        str(Path("~/Music").expanduser()),
        "--single",
        "--verbose",
        "https://example.com/watch?v=one",
        "https://example.com/watch?v=two",
    ]


def test_audio_wizard_uses_friendly_defaults() -> None:
    """Pressing Enter through optional audio questions must produce safe MP3 defaults."""
    console = make_console(
        "https://example.com/watch?v=one",
        "",
        "",
        "",
        "",
        "",
        "",
    )

    arguments = launcher.collect_audio_arguments(console, home=Path("/home/alex"))

    assert arguments == [
        "--audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "192",
        "--output",
        "/home/alex/Downloads",
        "--single",
        "https://example.com/watch?v=one",
    ]


def test_video_wizard_exposes_resolution_playlist_output_and_verbose_mode() -> None:
    """The guided video flow must retain every video downloader option."""
    console = make_console(
        "https://example.com/playlist",
        "",
        "1080",
        "/media/videos",
        "y",
        "y",
    )

    arguments = launcher.collect_video_arguments(console, home=Path("/home/alex"))

    assert arguments == [
        "--resolution",
        "1080",
        "--output",
        "/media/videos",
        "--verbose",
        "https://example.com/playlist",
    ]


def test_pdf_rename_wizard_exposes_recursive_keywords_format_and_verbose_options() -> None:
    """PDF renaming must remain fully configurable through the guided flow."""
    console = make_console(
        "/documents",
        "y",
        "/config/keywords.txt",
        "3",
        "{title}-{date}",
        "y",
    )

    arguments = launcher.collect_pdf_rename_arguments(console)

    assert arguments == [
        "--recursive",
        "--keywords",
        "/config/keywords.txt",
        "--format",
        "{title}-{date}",
        "--verbose",
        "/documents",
    ]


def test_pdf_date_wizard_accepts_multiple_folders_and_all_flags() -> None:
    """Date editing must expose multiple folders, recursion, mtime, and verbose output."""
    console = make_console("/documents/one", "/documents/two", "", "y", "y", "y")

    arguments = launcher.collect_pdf_date_arguments(console, system_name="Darwin")

    assert arguments == [
        "--recursive",
        "--modified-date",
        "--verbose",
        "/documents/one",
        "/documents/two",
    ]


def test_pdf_date_wizard_enables_supported_linux_timestamp_mode() -> None:
    """Linux users must not be led into the unsupported creation-time-only mode."""
    console = make_console("/documents", "", "n", "n")

    arguments = launcher.collect_pdf_date_arguments(console, system_name="Linux")

    assert arguments == ["--modified-date", "/documents"]


def test_preview_flow_runs_dry_run_before_confirmed_pdf_change(tmp_path: Path) -> None:
    """Potentially destructive PDF actions must always preview before execution."""
    calls: list[list[str]] = []
    console = make_console("y")

    def successful_runner(script_name: str, arguments: list[str]) -> int:
        calls.append([script_name, *arguments])
        return 0

    result = launcher.preview_then_apply(
        console,
        "pdfRename.py",
        ["--recursive", str(tmp_path)],
        runner=successful_runner,
    )

    assert result == 0
    assert calls == [
        ["pdfRename.py", "--dry-run", "--recursive", str(tmp_path)],
        ["pdfRename.py", "--recursive", str(tmp_path)],
    ]


def test_preview_flow_does_not_apply_cancelled_pdf_change(tmp_path: Path) -> None:
    """Rejecting the confirmation must leave the preview as the only invocation."""
    calls: list[list[str]] = []
    console = make_console("n", language="en")

    def successful_runner(script_name: str, arguments: list[str]) -> int:
        calls.append([script_name, *arguments])
        return 0

    result = launcher.preview_then_apply(
        console,
        "editCreationDate.py",
        [str(tmp_path)],
        runner=successful_runner,
    )

    assert result == 0
    assert calls == [["editCreationDate.py", "--dry-run", str(tmp_path)]]


def test_console_renders_both_supported_languages() -> None:
    """Switching language must change user-visible guided-flow text."""
    german_messages: list[str] = []
    english_messages: list[str] = []
    german = launcher.Console("de", AnswerSequence(""), german_messages.append)
    english = launcher.Console("en", AnswerSequence(""), english_messages.append)

    german.show("welcome")
    english.show("welcome")

    assert german_messages == ["Willkommen bei Python Tools"]
    assert english_messages == ["Welcome to Python Tools"]
