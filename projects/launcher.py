"""Cross-platform guided interface for the Python tools collection."""

from __future__ import annotations

import argparse
import locale
import platform
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

SUPPORTED_LANGUAGES = {"de", "en"}
PROJECT_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = PROJECT_DIRECTORY.parent
LANGUAGE_FILE = REPOSITORY_ROOT / ".python-tools-language"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "de": {
        "welcome": "Willkommen bei Python Tools",
        "main_menu": (
            "\nWas möchtest du tun?\n"
            "  1. YouTube als Audio herunterladen\n"
            "  2. YouTube als Video herunterladen\n"
            "  3. PDFs nach Datum und Inhalt umbenennen\n"
            "  4. PDF-Dateidatum aus dem Dateinamen setzen\n"
            "  5. Sprache / Language ändern\n"
            "  0. Beenden"
        ),
        "menu_choice": "Auswahl",
        "invalid_choice": "Bitte wähle eine der angezeigten Möglichkeiten.",
        "value_required": "Bitte gib einen Wert ein.",
        "yes_no_required": "Bitte antworte mit Ja oder Nein.",
        "first_url": "YouTube-URL",
        "more_url": "Weitere URL (Enter = weiter)",
        "audio_format": "Audioformat: 1=MP3, 2=M4A, 3=WAV, 4=FLAC",
        "audio_quality": "Audioqualität in kbit/s",
        "output_directory": "Ausgabeordner",
        "allow_playlist": "Playlist herunterladen, falls die URL eine enthält?",
        "verbose": "Ausführliche technische Meldungen anzeigen?",
        "resolution": "Maximale Videoauflösung (z. B. 1080, Enter = beste)",
        "folder": "PDF-Ordner",
        "more_folder": "Weiterer PDF-Ordner (Enter = weiter)",
        "recursive": "Auch Unterordner verarbeiten?",
        "keyword_file": "Eigene Keyword-Datei (Enter = mitgelieferte verwenden)",
        "name_format": ("Dateiname: 1=Datum_Titel, 2=Titel_Datum, 3=eigenes Format"),
        "custom_name_format": (
            "Eigenes Format mit {{date}} und {{title}}, z. B. {{title}}-{{date}}"
        ),
        "modified_date": "Zusätzlich das Änderungsdatum setzen?",
        "linux_modified_only": (
            "Linux kann das Erstellungsdatum normalerweise nicht ändern. "
            "Daher wird das Änderungsdatum gesetzt."
        ),
        "preview_start": "\nZuerst wird eine sichere Vorschau ausgeführt.",
        "preview_failed": (
            "Die Vorschau meldete mindestens ein Problem. Prüfe die Ausgabe sorgfältig."
        ),
        "apply_changes": "Die angezeigten Änderungen jetzt wirklich anwenden?",
        "change_cancelled": "Es wurden keine Änderungen angewendet.",
        "command_failed": "Das Werkzeug wurde mit einem Fehler beendet (Code {code}).",
        "command_success": "Das Werkzeug wurde erfolgreich beendet.",
        "press_enter": "Enter drücken, um zum Hauptmenü zurückzukehren",
        "language_menu": "Sprache wählen: 1=Deutsch, 2=English",
        "language_saved": "Sprache wurde auf Deutsch umgestellt.",
        "goodbye": "Auf Wiedersehen!",
        "interrupted": "Vorgang abgebrochen.",
        "media_rights": ("Bitte lade nur Medien herunter, für die du die nötigen Rechte besitzt."),
        "ffmpeg_missing": (
            "FFmpeg fehlt. Installiere es zuerst und starte Python Tools erneut:\n{command}"
        ),
        "ready": "Python Tools ist startbereit.",
    },
    "en": {
        "welcome": "Welcome to Python Tools",
        "main_menu": (
            "\nWhat would you like to do?\n"
            "  1. Download YouTube audio\n"
            "  2. Download YouTube video\n"
            "  3. Rename PDFs by date and content\n"
            "  4. Set PDF file dates from filenames\n"
            "  5. Change language / Sprache ändern\n"
            "  0. Exit"
        ),
        "menu_choice": "Choice",
        "invalid_choice": "Please choose one of the displayed options.",
        "value_required": "Please enter a value.",
        "yes_no_required": "Please answer Yes or No.",
        "first_url": "YouTube URL",
        "more_url": "Another URL (Enter = continue)",
        "audio_format": "Audio format: 1=MP3, 2=M4A, 3=WAV, 4=FLAC",
        "audio_quality": "Audio quality in kbit/s",
        "output_directory": "Output folder",
        "allow_playlist": "Download the playlist if the URL contains one?",
        "verbose": "Show detailed technical messages?",
        "resolution": "Maximum video resolution (e.g. 1080, Enter = best)",
        "folder": "PDF folder",
        "more_folder": "Another PDF folder (Enter = continue)",
        "recursive": "Process subfolders too?",
        "keyword_file": "Custom keyword file (Enter = use bundled file)",
        "name_format": ("Filename: 1=Date_Title, 2=Title_Date, 3=custom format"),
        "custom_name_format": (
            "Custom format using {{date}} and {{title}}, e.g. {{title}}-{{date}}"
        ),
        "modified_date": "Also set the modification date?",
        "linux_modified_only": (
            "Linux normally cannot change file creation time. "
            "The modification date will be set instead."
        ),
        "preview_start": "\nA safe preview will run first.",
        "preview_failed": (
            "The preview reported at least one problem. Review its output carefully."
        ),
        "apply_changes": "Apply the displayed changes now?",
        "change_cancelled": "No changes were applied.",
        "command_failed": "The tool exited with an error (code {code}).",
        "command_success": "The tool completed successfully.",
        "press_enter": "Press Enter to return to the main menu",
        "language_menu": "Choose language: 1=Deutsch, 2=English",
        "language_saved": "Language changed to English.",
        "goodbye": "Goodbye!",
        "interrupted": "Operation cancelled.",
        "media_rights": "Only download media when you have the necessary rights.",
        "ffmpeg_missing": (
            "FFmpeg is missing. Install it first, then restart Python Tools:\n{command}"
        ),
        "ready": "Python Tools is ready.",
    },
}

InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]
ToolRunner = Callable[[str, list[str]], int]


class Console:
    """Translate, display, and validate interactive console prompts."""

    def __init__(
        self,
        language: str,
        input_fn: InputFunction = input,
        output_fn: OutputFunction = print,
    ) -> None:
        self.language = language if language in SUPPORTED_LANGUAGES else "en"
        self.input_fn = input_fn
        self.output_fn = output_fn

    def translate(self, key: str, **values: object) -> str:
        """Return one translated message with optional format values."""
        return TRANSLATIONS[self.language][key].format(**values)

    def show(self, key: str, **values: object) -> None:
        """Display one translated message."""
        self.output_fn(self.translate(key, **values))

    def ask(self, key: str, *, default: str | None = None, required: bool = False) -> str:
        """Prompt for text and apply a visible default when input is blank."""
        while True:
            label = self.translate(key)
            default_label = f" [{default}]" if default is not None else ""
            answer = self.input_fn(f"{label}{default_label}: ").strip()
            if answer:
                return answer
            if default is not None:
                return default
            if not required:
                return ""
            self.show("value_required")

    def ask_yes_no(self, key: str, *, default: bool = False) -> bool:
        """Prompt until a localized yes/no answer is provided."""
        suffix = "J/n" if self.language == "de" and default else "j/N"
        if self.language == "en":
            suffix = "Y/n" if default else "y/N"

        while True:
            answer = self.input_fn(f"{self.translate(key)} [{suffix}]: ").strip().lower()
            if not answer:
                return default
            if answer in {"j", "ja", "y", "yes"}:
                return True
            if answer in {"n", "nein", "no"}:
                return False
            self.show("yes_no_required")

    def ask_choice(
        self,
        key: str,
        choices: dict[str, str],
        *,
        default: str,
    ) -> str:
        """Prompt until an allowed choice or its default is selected."""
        while True:
            answer = self.ask(key, default=default).lower()
            if answer in choices:
                return choices[answer]
            self.show("invalid_choice")


def language_from_locale(locale_name: str | None) -> str:
    """Choose German for German locales and English for every other locale."""
    normalized_locale = locale_name.lower().replace("-", "_") if locale_name else ""
    if normalized_locale == "de" or normalized_locale.startswith("de_"):
        return "de"
    return "en"


def load_language(path: Path, fallback: str) -> str:
    """Load a saved language preference or return a supported fallback."""
    fallback_language = fallback if fallback in SUPPORTED_LANGUAGES else "en"
    try:
        saved_language = path.read_text(encoding="utf-8").strip().lower()
    except (OSError, UnicodeError):
        return fallback_language
    return saved_language if saved_language in SUPPORTED_LANGUAGES else fallback_language


def save_language(path: Path, language: str) -> None:
    """Persist a validated language preference."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    path.write_text(f"{language}\n", encoding="utf-8")


def _collect_values(console: Console, first_key: str, more_key: str) -> list[str]:
    values = [console.ask(first_key, required=True)]
    while value := console.ask(more_key):
        values.append(value)
    return values


def _expanded_path(value: str) -> str:
    return str(Path(value).expanduser())


def _default_download_directory(home: Path) -> str:
    return str(home / "Downloads")


def collect_audio_arguments(console: Console, *, home: Path | None = None) -> list[str]:
    """Collect every audio-download option as ytVideoDownloader CLI arguments."""
    urls = _collect_values(console, "first_url", "more_url")
    audio_format = console.ask_choice(
        "audio_format",
        {
            "1": "mp3",
            "mp3": "mp3",
            "2": "m4a",
            "m4a": "m4a",
            "3": "wav",
            "wav": "wav",
            "4": "flac",
            "flac": "flac",
        },
        default="mp3",
    )
    quality = console.ask("audio_quality", default="192")
    output = console.ask(
        "output_directory",
        default=_default_download_directory(home or Path.home()),
    )
    allow_playlist = console.ask_yes_no("allow_playlist", default=False)
    verbose = console.ask_yes_no("verbose", default=False)

    arguments = [
        "--audio",
        "--audio-format",
        audio_format,
        "--audio-quality",
        quality,
        "--output",
        _expanded_path(output),
    ]
    if not allow_playlist:
        arguments.append("--single")
    if verbose:
        arguments.append("--verbose")
    return [*arguments, *urls]


def collect_video_arguments(console: Console, *, home: Path | None = None) -> list[str]:
    """Collect every video-download option as ytVideoDownloader CLI arguments."""
    urls = _collect_values(console, "first_url", "more_url")
    resolution = console.ask("resolution")
    while resolution and (not resolution.isdigit() or int(resolution) <= 0):
        console.show("invalid_choice")
        resolution = console.ask("resolution")
    output = console.ask(
        "output_directory",
        default=_default_download_directory(home or Path.home()),
    )
    allow_playlist = console.ask_yes_no("allow_playlist", default=False)
    verbose = console.ask_yes_no("verbose", default=False)

    arguments: list[str] = []
    if resolution:
        arguments.extend(["--resolution", resolution])
    arguments.extend(["--output", _expanded_path(output)])
    if not allow_playlist:
        arguments.append("--single")
    if verbose:
        arguments.append("--verbose")
    return [*arguments, *urls]


def collect_pdf_rename_arguments(console: Console) -> list[str]:
    """Collect every PDF renaming option as pdfRename CLI arguments."""
    folder = _expanded_path(console.ask("folder", required=True))
    recursive = console.ask_yes_no("recursive", default=False)
    keyword_file = console.ask("keyword_file")
    name_format = console.ask_choice(
        "name_format",
        {
            "1": "{date}_{title}",
            "2": "{title}_{date}",
            "3": "custom",
        },
        default="1",
    )
    if name_format == "custom":
        name_format = console.ask("custom_name_format", required=True)
    verbose = console.ask_yes_no("verbose", default=False)

    arguments: list[str] = []
    if recursive:
        arguments.append("--recursive")
    if keyword_file:
        arguments.extend(["--keywords", _expanded_path(keyword_file)])
    arguments.extend(["--format", name_format])
    if verbose:
        arguments.append("--verbose")
    arguments.append(folder)
    return arguments


def collect_pdf_date_arguments(
    console: Console,
    *,
    system_name: str | None = None,
) -> list[str]:
    """Collect every PDF timestamp option as editCreationDate CLI arguments."""
    folders = [
        _expanded_path(folder) for folder in _collect_values(console, "folder", "more_folder")
    ]
    recursive = console.ask_yes_no("recursive", default=False)
    active_system = system_name or platform.system()
    if active_system == "Linux":
        console.show("linux_modified_only")
        modified_date = True
    else:
        modified_date = console.ask_yes_no("modified_date", default=False)
    verbose = console.ask_yes_no("verbose", default=False)

    arguments: list[str] = []
    if recursive:
        arguments.append("--recursive")
    if modified_date:
        arguments.append("--modified-date")
    if verbose:
        arguments.append("--verbose")
    return [*arguments, *folders]


def run_project_tool(script_name: str, arguments: list[str]) -> int:
    """Run one bundled project script with the current Python interpreter."""
    script_path = PROJECT_DIRECTORY / script_name
    try:
        completed = subprocess.run(
            [sys.executable, str(script_path), *arguments],
            check=False,
        )
    except OSError as error:
        print(f"Could not start {script_name}: {error}", file=sys.stderr)
        return 1
    return completed.returncode


def preview_then_apply(
    console: Console,
    script_name: str,
    arguments: list[str],
    *,
    runner: ToolRunner = run_project_tool,
) -> int:
    """Preview a PDF operation and apply it only after explicit confirmation."""
    console.show("preview_start")
    preview_result = runner(script_name, ["--dry-run", *arguments])
    if preview_result:
        console.show("preview_failed")

    if not console.ask_yes_no("apply_changes", default=False):
        console.show("change_cancelled")
        return 0

    result = runner(script_name, arguments)
    if result:
        console.show("command_failed", code=result)
    else:
        console.show("command_success")
    return result


def _ffmpeg_install_command(system_name: str) -> str:
    if system_name == "Darwin":
        return "brew install ffmpeg"
    if system_name == "Windows":
        return "winget install Gyan.FFmpeg"
    return "sudo apt install ffmpeg  # Debian/Ubuntu"


def _media_is_ready(console: Console) -> bool:
    import shutil

    if shutil.which("ffmpeg") is not None:
        return True
    console.show("ffmpeg_missing", command=_ffmpeg_install_command(platform.system()))
    return False


def _pause(console: Console) -> None:
    console.input_fn(f"\n{console.translate('press_enter')}")


def _change_language(console: Console, preference_path: Path) -> None:
    language = console.ask_choice(
        "language_menu",
        {
            "1": "de",
            "de": "de",
            "deutsch": "de",
            "2": "en",
            "en": "en",
            "english": "en",
        },
        default="1" if console.language == "de" else "2",
    )
    console.language = language
    save_language(preference_path, language)
    console.show("language_saved")


def run_menu(console: Console, *, preference_path: Path = LANGUAGE_FILE) -> int:
    """Run the complete guided menu until the user exits."""
    console.show("welcome")
    while True:
        console.show("main_menu")
        choice = console.ask("menu_choice", required=True)

        if choice == "0":
            console.show("goodbye")
            return 0
        if choice == "5":
            _change_language(console, preference_path)
            continue
        if choice not in {"1", "2", "3", "4"}:
            console.show("invalid_choice")
            continue

        if choice in {"1", "2"}:
            console.show("media_rights")
            if not _media_is_ready(console):
                _pause(console)
                continue
            arguments = (
                collect_audio_arguments(console)
                if choice == "1"
                else collect_video_arguments(console)
            )
            result = run_project_tool("ytVideoDownloader.py", arguments)
            if result:
                console.show("command_failed", code=result)
            else:
                console.show("command_success")
        elif choice == "3":
            arguments = collect_pdf_rename_arguments(console)
            preview_then_apply(console, "pdfRename.py", arguments)
        else:
            arguments = collect_pdf_date_arguments(console)
            preview_then_apply(console, "editCreationDate.py", arguments)

        _pause(console)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start the guided Python Tools menu / Python-Tools-Menü starten."
    )
    parser.add_argument("--language", choices=sorted(SUPPORTED_LANGUAGES))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether the launcher can start, then exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Load language settings and start the guided interface."""
    args = _argument_parser().parse_args(list(argv) if argv is not None else None)
    detected_locale = locale.getlocale()[0]
    fallback_language = language_from_locale(detected_locale)
    language = args.language or load_language(LANGUAGE_FILE, fallback_language)
    if args.language:
        save_language(LANGUAGE_FILE, language)
    console = Console(language)

    if args.check:
        console.show("ready")
        return 0

    try:
        return run_menu(console)
    except (EOFError, KeyboardInterrupt):
        print()
        console.show("interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
