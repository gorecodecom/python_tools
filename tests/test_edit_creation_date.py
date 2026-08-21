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


def test_update_file_creation_date_linux_dry_run_rejects_creation_only_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A Linux dry-run must not preview unsupported creation-time behavior."""
    pdf = tmp_path / "20260821_report.pdf"
    pdf.touch()
    original_atime_ns = 1_700_000_000_123_456_789
    original_mtime_ns = 1_700_000_100_987_654_321
    os.utime(pdf, ns=(original_atime_ns, original_mtime_ns))
    monkeypatch.setattr(date_editor.platform, "system", lambda: "Linux")

    assert date_editor.update_file_creation_date(pdf, dry_run=True) is False
    assert "Linux does not support setting file creation time" in caplog.text
    assert pdf.stat().st_atime_ns == original_atime_ns
    assert pdf.stat().st_mtime_ns == original_mtime_ns


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

    assert date_editor.process_folder(tmp_path, modify_modified_date=True, dry_run=True) == (1, 0)


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


def test_process_folder_rejects_out_of_tree_pdf_symlink(tmp_path: Path) -> None:
    """Discovery must count a PDF symlink as a failure without touching its target."""
    target = tmp_path / "20260821_outside.pdf"
    target.touch()
    original_mtime_ns = target.stat().st_mtime_ns
    folder = tmp_path / "input"
    folder.mkdir()
    link = folder / "20260821_link.pdf"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlink creation is unsupported: {error}")

    assert date_editor.process_folder(folder, modify_modified_date=True, dry_run=True) == (0, 1)
    assert link.is_symlink()
    assert target.stat().st_mtime_ns == original_mtime_ns


def test_set_file_dates_rejects_symlink_at_mutation_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The final timestamp boundary must refuse a symlink before calling os.utime."""
    target = tmp_path / "20260821_target.pdf"
    target.touch()
    link = tmp_path / "20260821_link.pdf"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlink creation is unsupported: {error}")

    monkeypatch.setattr(
        date_editor.os,
        "utime",
        lambda *_args, **_kwargs: pytest.fail("os.utime must not follow a symlink"),
    )

    assert (
        date_editor.set_file_dates(
            link,
            datetime.datetime(2026, 8, 21),
            modify_modified_date=True,
            system="Linux",
        )
        is False
    )


@pytest.mark.parametrize("error_type", [ValueError, OverflowError])
def test_process_folder_counts_host_timestamp_conversion_failure_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_type: type[Exception],
) -> None:
    """A host timestamp conversion failure must not abort remaining files."""
    boundary_pdf = tmp_path / "19000101_boundary.pdf"
    valid_pdf = tmp_path / "20260821_valid.pdf"
    boundary_pdf.touch()
    valid_pdf.touch()
    original_utime = os.utime

    def reject_boundary_date(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *args: object,
        **kwargs: object,
    ) -> None:
        if Path(path).name == boundary_pdf.name:
            raise error_type("host timestamp is out of range")
        original_utime(path, *args, **kwargs)

    monkeypatch.setattr(date_editor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(date_editor.os, "utime", reject_boundary_date)

    assert date_editor.process_folder(tmp_path, modify_modified_date=True) == (1, 1)
    assert valid_pdf.stat().st_mtime_ns == int(
        datetime.datetime(2026, 8, 21).timestamp() * 1_000_000_000
    )


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

    assert date_editor.main(["--modified-date", "--dry-run", str(tmp_path)]) == 0


def test_main_linux_creation_only_dry_run_counts_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unsupported Linux dry-run must produce a non-zero CLI result."""
    (tmp_path / "20260821_report.pdf").touch()
    monkeypatch.setattr(date_editor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: pytest.fail("input() must not be called with positional folders"),
    )

    assert date_editor.main(["--dry-run", str(tmp_path)]) == 1
    assert "Failed: 1" in capsys.readouterr().out


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


def test_main_treats_interactive_eof_as_normal_end_and_preserves_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """EOF after interactive work must return the aggregate processing status."""
    missing = tmp_path / "missing"
    prompt_count = 0

    def provide_folder_then_eof(_prompt: str) -> str:
        nonlocal prompt_count
        prompt_count += 1
        if prompt_count == 1:
            return str(missing)
        raise EOFError

    monkeypatch.setattr("builtins.input", provide_folder_then_eof)

    assert date_editor.main([]) == 1
    assert "Summary: Total files processed: 0, Failed: 1" in capsys.readouterr().out
