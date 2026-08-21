# ruff: noqa: DTZ001
"""Tests for cross-platform PDF timestamp updates."""

import datetime
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from projects import editCreationDate as date_editor


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("20260821_report.pdf", datetime.datetime(2026, 8, 21)),
        ("2026-08-21_report.pdf", datetime.datetime(2026, 8, 21)),
        ("annual_report_20260821.pdf", datetime.datetime(2026, 8, 21)),
    ],
)
def test_extract_date_from_filename_supports_documented_patterns(
    filename: str, expected: datetime.datetime
) -> None:
    """Each documented filename shape must produce its embedded calendar date."""

    assert date_editor.extract_date_from_filename(Path(filename)) == expected


def test_extract_date_from_filename_rejects_invalid_calendar_date() -> None:
    """A syntactically matching but impossible date must not be applied."""

    assert date_editor.extract_date_from_filename(Path("20260230_report.pdf")) is None


def test_set_file_dates_on_macos_uses_setfile_without_changing_mtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A creation-only macOS request must use SetFile and leave mtime untouched."""
    pdf = tmp_path / "20260821_report.pdf"
    pdf.touch()
    original_atime_ns = 1_700_000_000_123_456_789
    original_mtime_ns = 1_700_000_100_987_654_321
    os.utime(pdf, ns=(original_atime_ns, original_mtime_ns))
    commands: list[tuple[list[str], bool]] = []

    def record_command(command: list[str], *, check: bool) -> None:
        commands.append((command, check))

    monkeypatch.setattr(date_editor.subprocess, "run", record_command)

    assert date_editor.set_file_dates(pdf, datetime.datetime(2026, 8, 21), system="Darwin") is True
    assert commands == [(["SetFile", "-d", "08/21/2026 00:00:00", str(pdf)], True)]
    assert pdf.stat().st_atime_ns == original_atime_ns
    assert pdf.stat().st_mtime_ns == original_mtime_ns


def test_set_file_dates_on_macos_optionally_updates_mtime_and_preserves_atime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An explicit macOS mtime request must preserve the file's access time."""
    pdf = tmp_path / "20260821_report.pdf"
    pdf.touch()
    original_atime_ns = 1_700_000_000_123_456_789
    os.utime(pdf, ns=(original_atime_ns, 1_700_000_100_987_654_321))
    monkeypatch.setattr(date_editor.subprocess, "run", lambda *_args, **_kwargs: None)
    target = datetime.datetime(2026, 8, 21)

    assert (
        date_editor.set_file_dates(pdf, target, modify_modified_date=True, system="Darwin") is True
    )
    assert pdf.stat().st_atime_ns == original_atime_ns
    assert pdf.stat().st_mtime_ns == int(target.timestamp() * 1_000_000_000)


def test_set_file_dates_on_linux_refuses_creation_only_request(tmp_path: Path) -> None:
    """Linux must not claim it can update a creation timestamp."""
    pdf = tmp_path / "20260821_report.pdf"
    pdf.touch()
    original_atime_ns = 1_700_000_000_123_456_789
    original_mtime_ns = 1_700_000_100_987_654_321
    os.utime(pdf, ns=(original_atime_ns, original_mtime_ns))

    assert date_editor.set_file_dates(pdf, datetime.datetime(2026, 8, 21), system="Linux") is False
    assert pdf.stat().st_atime_ns == original_atime_ns
    assert pdf.stat().st_mtime_ns == original_mtime_ns


def test_set_file_dates_on_linux_updates_requested_mtime_and_preserves_atime(
    tmp_path: Path,
) -> None:
    """Linux may update mtime only when the caller explicitly requests it."""
    pdf = tmp_path / "20260821_report.pdf"
    pdf.touch()
    original_atime_ns = 1_700_000_000_123_456_789
    os.utime(pdf, ns=(original_atime_ns, 1_700_000_100_987_654_321))
    target = datetime.datetime(2026, 8, 21)

    assert (
        date_editor.set_file_dates(pdf, target, modify_modified_date=True, system="Linux") is True
    )
    assert pdf.stat().st_atime_ns == original_atime_ns
    assert pdf.stat().st_mtime_ns == int(target.timestamp() * 1_000_000_000)


@pytest.mark.parametrize(
    ("modify_modified_date", "expected_last_write"),
    [(False, None), (True, "win-time")],
)
def test_set_file_dates_on_windows_uses_creation_and_optional_last_write_time(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    modify_modified_date: bool,
    expected_last_write: str | None,
) -> None:
    """Windows must call SetFileTime with the creation and requested write times."""
    pdf = tmp_path / "20260821_report.pdf"
    pdf.touch()
    calls: dict[str, object] = {}

    class FakeHandle:
        def Close(self) -> None:
            calls["closed"] = True

    handle = FakeHandle()

    def create_file(*args: object) -> FakeHandle:
        calls["create_file"] = args
        return handle

    def set_file_time(*args: object) -> None:
        calls["set_file_time"] = args

    fake_win32file = SimpleNamespace(
        GENERIC_WRITE=1,
        FILE_SHARE_READ=2,
        FILE_SHARE_WRITE=4,
        FILE_SHARE_DELETE=8,
        OPEN_EXISTING=3,
        FILE_ATTRIBUTE_NORMAL=128,
        CreateFile=create_file,
        SetFileTime=set_file_time,
    )
    fake_pywintypes = SimpleNamespace(Time=lambda _date: "win-time")
    monkeypatch.setitem(sys.modules, "win32file", fake_win32file)
    monkeypatch.setitem(sys.modules, "pywintypes", fake_pywintypes)

    assert (
        date_editor.set_file_dates(
            pdf,
            datetime.datetime(2026, 8, 21),
            modify_modified_date=modify_modified_date,
            system="Windows",
        )
        is True
    )
    assert calls["create_file"] == (
        str(pdf),
        1,
        2 | 4 | 8,
        None,
        3,
        128,
        None,
    )
    assert calls["set_file_time"] == (
        handle,
        "win-time",
        None,
        expected_last_write,
    )
    assert calls["closed"] is True


def test_process_folder_discovers_uppercase_pdf_extension(tmp_path: Path) -> None:
    """PDF discovery must not depend on extension casing."""
    (tmp_path / "20260821_report.PDF").touch()

    assert date_editor.process_folder(tmp_path, dry_run=True) == (1, 0)


def test_process_folder_forwards_modified_date_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The folder processor must pass the explicit mtime option to file updates."""
    pdf = tmp_path / "20260821_report.pdf"
    pdf.touch()
    original_atime_ns = 1_700_000_000_123_456_789
    os.utime(pdf, ns=(original_atime_ns, 1_700_000_100_987_654_321))
    monkeypatch.setattr(date_editor.platform, "system", lambda: "Linux")
    target = datetime.datetime(2026, 8, 21)

    assert date_editor.process_folder(tmp_path, modify_modified_date=True) == (1, 0)
    assert pdf.stat().st_atime_ns == original_atime_ns
    assert pdf.stat().st_mtime_ns == int(target.timestamp() * 1_000_000_000)


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_process_folder_counts_invalid_directory_input_as_failure(
    tmp_path: Path, kind: str
) -> None:
    """Missing paths and regular files must produce a failed processing result."""
    path = tmp_path / kind
    if kind == "file":
        path.touch()

    assert date_editor.process_folder(path) == (0, 1)


def test_main_with_positional_folder_does_not_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Supplying positional folders must select non-interactive execution."""
    (tmp_path / "20260821_report.pdf").touch()

    def fail_if_prompted(_prompt: str) -> str:
        raise AssertionError("input() must not be called with positional folders")

    monkeypatch.setattr("builtins.input", fail_if_prompted)

    assert date_editor.main(["--dry-run", str(tmp_path)]) == 0


def test_main_returns_nonzero_when_a_folder_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Any failed folder must result in a non-zero command exit status."""
    missing = tmp_path / "missing"
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: pytest.fail("input() must not be called with positional folders"),
    )

    assert date_editor.main([str(missing)]) == 1
