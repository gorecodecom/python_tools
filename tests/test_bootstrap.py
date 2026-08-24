"""Behavior tests for first-run environment setup."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from projects import bootstrap


def test_windows_reparse_point_is_rejected_on_python_311_compatible_path() -> None:
    """Windows junction detection must not depend on Path.is_junction from Python 3.12."""

    class ReparsePointPath:
        def is_symlink(self) -> bool:
            return False

        def lstat(self) -> SimpleNamespace:
            return SimpleNamespace(st_file_attributes=0x400)

    assert bootstrap._is_link_or_junction(ReparsePointPath()) is True


def test_quiet_command_hides_expected_dependency_probe_error(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """A missing dependency probe must not expose a Python traceback to normal users."""
    result = bootstrap.run_command(
        [sys.executable, "-c", "raise SystemExit('expected probe failure')"],
        tmp_path,
        quiet=True,
    )

    assert result == 1
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_new_environment_is_created_installed_and_launched(tmp_path: Path) -> None:
    """A first start must create the venv, install runtime packages, and open the menu."""
    calls: list[tuple[list[str], Path]] = []
    base_python = "/usr/bin/python3.14"
    venv_python = str(tmp_path / ".python-tools-venv" / "bin" / "python")
    base_import_check = "import dateparser, deno, pdfplumber, tqdm, yt_dlp"
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("dateparser==1.4.2\n", encoding="utf-8")

    def runner(command: list[str], cwd: Path, _quiet: bool) -> int:
        calls.append((command, cwd))
        if command == [venv_python, "-c", base_import_check]:
            return 1
        return 0

    result = bootstrap.prepare_and_launch(
        repository_root=tmp_path,
        base_python=base_python,
        launcher_arguments=["--language", "en"],
        system_name="Linux",
        runner=runner,
    )

    assert result == 0
    assert calls == [
        ([base_python, "-m", "venv", str(tmp_path / ".python-tools-venv")], tmp_path),
        ([venv_python, "-c", base_import_check], tmp_path),
        ([venv_python, "-m", "pip", "install", "--upgrade", "pip"], tmp_path),
        (
            [
                venv_python,
                "-m",
                "pip",
                "install",
                "-r",
                str(tmp_path / "requirements.txt"),
            ],
            tmp_path,
        ),
        (
            [venv_python, "-m", "projects.launcher", "--language", "en"],
            tmp_path,
        ),
    ]
    assert (tmp_path / ".python-tools-venv" / ".python-tools-requirements.sha256").read_text(
        encoding="utf-8"
    ).strip() == hashlib.sha256(requirements.read_bytes()).hexdigest()
    assert (tmp_path / ".python-tools-venv" / ".python-tools-owned").read_text(
        encoding="utf-8"
    ) == "Managed by Python Tools.\n"


def test_ready_environment_skips_creation_and_installation(tmp_path: Path) -> None:
    """Normal starts must avoid unnecessary setup work once dependencies are ready."""
    calls: list[tuple[list[str], Path]] = []
    venv_python_path = tmp_path / ".python-tools-venv" / "Scripts" / "python.exe"
    venv_python_path.parent.mkdir(parents=True)
    venv_python_path.touch()
    venv_python = str(venv_python_path)
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("dateparser==1.4.2\n", encoding="utf-8")
    (tmp_path / ".python-tools-venv" / ".python-tools-owned").write_text(
        "Managed by Python Tools.\n",
        encoding="utf-8",
    )
    (tmp_path / ".python-tools-venv" / ".python-tools-requirements.sha256").write_text(
        f"{hashlib.sha256(requirements.read_bytes()).hexdigest()}\n",
        encoding="utf-8",
    )

    def runner(command: list[str], cwd: Path, _quiet: bool) -> int:
        calls.append((command, cwd))
        return 0

    result = bootstrap.prepare_and_launch(
        repository_root=tmp_path,
        base_python="C:\\Python314\\python.exe",
        launcher_arguments=["--check"],
        system_name="Windows",
        runner=runner,
    )

    assert result == 0
    assert calls == [
        (
            [
                venv_python,
                "-c",
                "import sys; raise SystemExit(sys.version_info < (3, 11))",
            ],
            tmp_path,
        ),
        ([venv_python, "-m", "pip", "--version"], tmp_path),
        (
            [
                venv_python,
                "-c",
                "import dateparser, deno, pdfplumber, tqdm, yt_dlp, pywintypes, win32file",
            ],
            tmp_path,
        ),
        ([venv_python, "-m", "projects.launcher", "--check"], tmp_path),
    ]


def test_failed_environment_creation_stops_before_installation(tmp_path: Path) -> None:
    """A failed venv creation must return its error and never run later commands."""
    calls: list[list[str]] = []

    def failing_runner(command: list[str], _cwd: Path, _quiet: bool) -> int:
        calls.append(command)
        return 7

    result = bootstrap.prepare_and_launch(
        repository_root=tmp_path,
        base_python="python3",
        launcher_arguments=[],
        system_name="Linux",
        runner=failing_runner,
    )

    assert result == 7
    assert calls == [["python3", "-m", "venv", str(tmp_path / ".python-tools-venv")]]


def test_unhealthy_existing_environment_is_recreated_before_installation(
    tmp_path: Path,
) -> None:
    """An interrupted or stale venv must be repaired instead of reused forever."""
    venv_python_path = tmp_path / ".python-tools-venv" / "bin" / "python"
    venv_python_path.parent.mkdir(parents=True)
    venv_python_path.touch()
    (tmp_path / ".python-tools-venv" / ".python-tools-owned").write_text(
        "Managed by Python Tools.\n",
        encoding="utf-8",
    )
    venv_python = str(venv_python_path)
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("dateparser==1.4.2\n", encoding="utf-8")
    base_python = "/usr/bin/python3.14"
    health_check = "import sys; raise SystemExit(sys.version_info < (3, 11))"
    calls: list[list[str]] = []

    def runner(command: list[str], _cwd: Path, _quiet: bool) -> int:
        calls.append(command)
        if command == [venv_python, "-c", health_check]:
            return 1
        if command == [
            venv_python,
            "-c",
            "import dateparser, deno, pdfplumber, tqdm, yt_dlp",
        ]:
            return 1
        return 0

    result = bootstrap.prepare_and_launch(
        repository_root=tmp_path,
        base_python=base_python,
        launcher_arguments=[],
        system_name="Linux",
        runner=runner,
    )

    assert result == 0
    assert calls == [
        [venv_python, "-c", health_check],
        [
            base_python,
            "-m",
            "venv",
            "--clear",
            str(tmp_path / ".python-tools-venv"),
        ],
        [venv_python, "-c", "import dateparser, deno, pdfplumber, tqdm, yt_dlp"],
        [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
        [venv_python, "-m", "pip", "install", "-r", str(requirements)],
        [venv_python, "-m", "projects.launcher"],
    ]


def test_changed_requirements_are_installed_before_launch(tmp_path: Path) -> None:
    """Updated pinned dependencies must be applied even when old imports still succeed."""
    venv_python_path = tmp_path / ".python-tools-venv" / "bin" / "python"
    venv_python_path.parent.mkdir(parents=True)
    venv_python_path.touch()
    marker = tmp_path / ".python-tools-venv" / ".python-tools-requirements.sha256"
    (tmp_path / ".python-tools-venv" / ".python-tools-owned").write_text(
        "Managed by Python Tools.\n",
        encoding="utf-8",
    )
    old_fingerprint = hashlib.sha256(b"dateparser==1.0.0\n").hexdigest()
    marker.write_text(
        f"{old_fingerprint}\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("dateparser==1.4.2\n", encoding="utf-8")
    calls: list[list[str]] = []

    def successful_runner(command: list[str], _cwd: Path, _quiet: bool) -> int:
        calls.append(command)
        return 0

    result = bootstrap.prepare_and_launch(
        repository_root=tmp_path,
        base_python="python3.14",
        launcher_arguments=[],
        system_name="Linux",
        runner=successful_runner,
    )

    assert result == 0
    assert calls == [
        [
            str(venv_python_path),
            "-c",
            "import sys; raise SystemExit(sys.version_info < (3, 11))",
        ],
        [str(venv_python_path), "-m", "pip", "--version"],
        [
            str(venv_python_path),
            "-c",
            "import dateparser, deno, pdfplumber, tqdm, yt_dlp",
        ],
        [str(venv_python_path), "-m", "pip", "install", "--upgrade", "pip"],
        [
            str(venv_python_path),
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements),
        ],
        [str(venv_python_path), "-m", "projects.launcher"],
    ]
    assert (
        marker.read_text(encoding="utf-8").strip()
        == hashlib.sha256(requirements.read_bytes()).hexdigest()
    )


def test_broken_pip_recreates_owned_launcher_environment(tmp_path: Path) -> None:
    """A venv with a working interpreter but broken pip must be rebuilt before use."""
    venv_python_path = tmp_path / ".python-tools-venv" / "bin" / "python"
    venv_python_path.parent.mkdir(parents=True)
    venv_python_path.touch()
    owner_marker = tmp_path / ".python-tools-venv" / ".python-tools-owned"
    owner_marker.write_text("Managed by Python Tools.\n", encoding="utf-8")
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("dateparser==1.4.2\n", encoding="utf-8")
    venv_python = str(venv_python_path)
    health_check = "import sys; raise SystemExit(sys.version_info < (3, 11))"
    calls: list[list[str]] = []

    def runner(command: list[str], _cwd: Path, _quiet: bool) -> int:
        calls.append(command)
        if command == [venv_python, "-m", "pip", "--version"]:
            return 1
        if command == [
            venv_python,
            "-c",
            "import dateparser, deno, pdfplumber, tqdm, yt_dlp",
        ]:
            return 1
        return 0

    result = bootstrap.prepare_and_launch(
        repository_root=tmp_path,
        base_python="python3.14",
        launcher_arguments=[],
        system_name="Linux",
        runner=runner,
    )

    assert result == 0
    assert calls[:3] == [
        [venv_python, "-c", health_check],
        [venv_python, "-m", "pip", "--version"],
        [
            "python3.14",
            "-m",
            "venv",
            "--clear",
            str(tmp_path / ".python-tools-venv"),
        ],
    ]
    assert [venv_python, "-m", "pip", "install", "-r", str(requirements)] in calls


def test_symlinked_launcher_environment_is_refused_without_touching_target(
    tmp_path: Path,
) -> None:
    """Automatic repair must never clear a directory reached through a symlink."""
    external_target = tmp_path / "external-environment"
    external_target.mkdir()
    sentinel = external_target / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    (tmp_path / ".python-tools-venv").symlink_to(external_target, target_is_directory=True)
    calls: list[list[str]] = []

    def runner(command: list[str], _cwd: Path, _quiet: bool) -> int:
        calls.append(command)
        return 0

    result = bootstrap.prepare_and_launch(
        repository_root=tmp_path,
        base_python="python3.14",
        launcher_arguments=[],
        system_name="Linux",
        runner=runner,
    )

    assert result == 1
    assert calls == []
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_unowned_launcher_environment_is_refused_without_clearing(tmp_path: Path) -> None:
    """Automatic repair must not clear a pre-existing directory it did not create."""
    environment = tmp_path / ".python-tools-venv"
    environment.mkdir()
    sentinel = environment / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command: list[str], _cwd: Path, _quiet: bool) -> int:
        calls.append(command)
        return 0

    result = bootstrap.prepare_and_launch(
        repository_root=tmp_path,
        base_python="python3.14",
        launcher_arguments=[],
        system_name="Linux",
        runner=runner,
    )

    assert result == 1
    assert calls == []
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_supported_python_version_requires_311_or_newer() -> None:
    """The bootstrap must reject Python versions outside the documented support range."""
    assert bootstrap.python_version_is_supported((3, 11)) is True
    assert bootstrap.python_version_is_supported((3, 14)) is True
    assert bootstrap.python_version_is_supported((3, 10)) is False
    assert bootstrap.python_version_is_supported((2, 7)) is False


def test_windows_dependency_check_includes_timestamp_modules() -> None:
    """A Windows venv without pywin32 must be repaired before opening the menu."""
    assert bootstrap.dependency_import_check("Windows") == (
        "import dateparser, deno, pdfplumber, tqdm, yt_dlp, pywintypes, win32file"
    )
    assert bootstrap.dependency_import_check("Linux") == (
        "import dateparser, deno, pdfplumber, tqdm, yt_dlp"
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX starters require /bin/sh")
@pytest.mark.parametrize("starter_name", ["python-tools.sh", "Python Tools.command"])
def test_posix_starter_dispatches_to_bootstrap_without_real_setup(
    starter_name: str,
    tmp_path: Path,
) -> None:
    """Both POSIX entry points must dispatch without touching the repository venv."""
    repository_root = Path(__file__).resolve().parent.parent
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    recorded_arguments = tmp_path / "arguments.txt"
    fake_python = fake_bin / "python3.14"
    fake_python.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-c" ]; then\n'
        "    exit 0\n"
        "fi\n"
        ': > "$PYTHON_TOOLS_ARGS_FILE"\n'
        'for argument in "$@"; do\n'
        '    printf \'%s\\n\' "$argument" >> "$PYTHON_TOOLS_ARGS_FILE"\n'
        "done\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}:/usr/bin:/bin"
    environment["PYTHON_TOOLS_ARGS_FILE"] = str(recorded_arguments)

    completed = subprocess.run(
        ["/bin/sh", str(repository_root / starter_name), "--check"],
        cwd=repository_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert recorded_arguments.read_text(encoding="utf-8").splitlines() == [
        "-m",
        "projects.bootstrap",
        "--check",
    ]
