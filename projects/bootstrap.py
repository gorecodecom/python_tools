"""Prepare the Python environment before starting the guided launcher."""

from __future__ import annotations

import hashlib
import platform
import stat
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER_VENV_NAME = ".python-tools-venv"
OWNERSHIP_MARKER_NAME = ".python-tools-owned"
OWNERSHIP_MARKER_CONTENT = "Managed by Python Tools.\n"
DEPENDENCY_IMPORT_CHECK = "import dateparser, deno, pdfplumber, tqdm, yt_dlp"
VENV_VERSION_CHECK = "import sys; raise SystemExit(sys.version_info < (3, 11))"
CommandRunner = Callable[[list[str], Path, bool], int]


def python_version_is_supported(version: tuple[int, int]) -> bool:
    """Return whether a Python major/minor pair satisfies the project minimum."""
    return version >= (3, 11)


def dependency_import_check(system_name: str) -> str:
    """Return the runtime import check required by one operating system."""
    if system_name == "Windows":
        return f"{DEPENDENCY_IMPORT_CHECK}, pywintypes, win32file"
    return DEPENDENCY_IMPORT_CHECK


def _requirements_fingerprint(requirements_path: Path) -> str:
    return hashlib.sha256(requirements_path.read_bytes()).hexdigest()


def _requirements_are_current(requirements_path: Path, marker_path: Path) -> bool:
    try:
        saved_fingerprint = marker_path.read_text(encoding="utf-8").strip()
        return saved_fingerprint == _requirements_fingerprint(requirements_path)
    except (OSError, UnicodeError):
        return False


def _save_requirements_fingerprint(requirements_path: Path, marker_path: Path) -> None:
    fingerprint = _requirements_fingerprint(requirements_path)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(f"{fingerprint}\n", encoding="utf-8")


def _venv_python(repository_root: Path, system_name: str) -> Path:
    venv_directory = repository_root / LAUNCHER_VENV_NAME
    if system_name == "Windows":
        return venv_directory / "Scripts" / "python.exe"
    return venv_directory / "bin" / "python"


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_point)


def _environment_is_owned(venv_directory: Path) -> bool:
    marker = venv_directory / OWNERSHIP_MARKER_NAME
    try:
        return not marker.is_symlink() and marker.read_text(encoding="utf-8") == (
            OWNERSHIP_MARKER_CONTENT
        )
    except (OSError, UnicodeError):
        return False


def _write_ownership_marker(venv_directory: Path) -> bool:
    try:
        venv_directory.mkdir(parents=False, exist_ok=True)
        (venv_directory / OWNERSHIP_MARKER_NAME).write_text(
            OWNERSHIP_MARKER_CONTENT,
            encoding="utf-8",
        )
    except (OSError, UnicodeError) as error:
        print(
            f"Launcher-Umgebung kann nicht vorbereitet werden / "
            f"Cannot prepare launcher environment: {error}",
            file=sys.stderr,
        )
        return False
    return True


def _venv_is_healthy(
    venv_python_path: Path,
    repository_root: Path,
    runner: CommandRunner,
) -> bool:
    if not venv_python_path.is_file():
        return False

    venv_python = str(venv_python_path)
    if runner([venv_python, "-c", VENV_VERSION_CHECK], repository_root, True):
        return False
    return runner([venv_python, "-m", "pip", "--version"], repository_root, True) == 0


def run_command(command: list[str], cwd: Path, quiet: bool = False) -> int:
    """Run one setup or launcher command and return its exit code."""
    try:
        output_target = subprocess.DEVNULL if quiet else None
        return subprocess.run(
            command,
            cwd=cwd,
            check=False,
            stdout=output_target,
            stderr=output_target,
        ).returncode
    except OSError as error:
        print(f"Start fehlgeschlagen / Failed to start: {error}", file=sys.stderr)
        return 1


def prepare_and_launch(
    *,
    repository_root: Path,
    base_python: str,
    launcher_arguments: Sequence[str],
    system_name: str | None = None,
    runner: CommandRunner = run_command,
) -> int:
    """Create or repair the venv, then start the shared guided launcher."""
    active_system = system_name or platform.system()
    venv_directory = repository_root / LAUNCHER_VENV_NAME
    environment_existed = venv_directory.exists() or venv_directory.is_symlink()
    if _is_link_or_junction(venv_directory):
        print(
            "Verknüpfte Launcher-Umgebung wird aus Sicherheitsgründen abgelehnt. / "
            "Refusing a linked launcher environment for safety.",
            file=sys.stderr,
        )
        return 1
    if environment_existed and not _environment_is_owned(venv_directory):
        print(
            "Die vorhandene Launcher-Umgebung gehört nicht Python Tools. / "
            "The existing launcher environment is not owned by Python Tools.",
            file=sys.stderr,
        )
        return 1
    if not environment_existed and not _write_ownership_marker(venv_directory):
        return 1

    venv_python_path = _venv_python(repository_root, active_system)
    venv_python = str(venv_python_path)
    requirements_path = repository_root / "requirements.txt"
    requirements_marker = venv_directory / ".python-tools-requirements.sha256"

    if not _venv_is_healthy(venv_python_path, repository_root, runner):
        print("Ersteinrichtung wird vorbereitet / Preparing first-time setup ...")
        venv_command = [base_python, "-m", "venv"]
        if environment_existed:
            venv_command.append("--clear")
        venv_command.append(str(venv_directory))
        result = runner(
            venv_command,
            repository_root,
            False,
        )
        if result:
            return result
        if not _write_ownership_marker(venv_directory):
            return 1

    import_check = dependency_import_check(active_system)
    dependencies_ready = runner([venv_python, "-c", import_check], repository_root, True) == 0
    requirements_current = _requirements_are_current(requirements_path, requirements_marker)
    if not dependencies_ready or not requirements_current:
        print("Pakete werden installiert / Installing packages ...")
        result = runner(
            [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
            repository_root,
            False,
        )
        if result:
            return result
        result = runner(
            [
                venv_python,
                "-m",
                "pip",
                "install",
                "-r",
                str(requirements_path),
            ],
            repository_root,
            False,
        )
        if result:
            return result
        _save_requirements_fingerprint(requirements_path, requirements_marker)

    return runner(
        [venv_python, "-m", "projects.launcher", *launcher_arguments],
        repository_root,
        False,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Validate the base interpreter and run the setup workflow."""
    if not python_version_is_supported((sys.version_info.major, sys.version_info.minor)):
        print(
            "Python 3.11 oder neuer wird benötigt. / Python 3.11 or newer is required.",
            file=sys.stderr,
        )
        return 2

    return prepare_and_launch(
        repository_root=REPOSITORY_ROOT,
        base_python=sys.executable,
        launcher_arguments=list(argv) if argv is not None else sys.argv[1:],
    )


if __name__ == "__main__":
    raise SystemExit(main())
