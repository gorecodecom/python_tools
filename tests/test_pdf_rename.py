"""Regression tests for safe, predictable PDF renaming."""

import os
from pathlib import Path

import pytest

from projects import pdfRename as pdf_rename


def test_list_pdf_files_discovers_uppercase_pdf_extension(tmp_path: Path) -> None:
    """Uppercase PDF extensions must be included in a non-recursive scan."""
    uppercase_pdf = tmp_path / "statement.PDF"
    uppercase_pdf.touch()

    assert pdf_rename.list_pdf_files(tmp_path) == [str(uppercase_pdf)]


def test_parse_args_uses_script_relative_default_keywords_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Changing the working directory must not change the default keyword source."""
    monkeypatch.chdir(tmp_path)

    args = pdf_rename.parse_args([str(tmp_path)])

    assert Path(args.keywords) == pdf_rename.DEFAULT_KEYWORDS_FILE


def test_sanitize_filename_removes_cross_platform_invalid_characters() -> None:
    """Windows-invalid and control characters must not reach generated names."""

    assert pdf_rename.sanitize_filename('Report<>:"/\\|?*\x00') == "Report__________"


def test_format_pdf_name_neutralizes_path_traversal_in_title() -> None:
    """A title must not be able to turn a generated name into a relative path."""

    assert (
        pdf_rename.format_pdf_name("20260131", "../Annual/Report", "{date}_{title}")
        == "20260131_Annual_Report.pdf"
    )


def test_format_pdf_name_rejects_unknown_format_fields() -> None:
    """Only the documented date and title format fields are accepted."""

    with pytest.raises(ValueError, match="Unsupported format field"):
        pdf_rename.format_pdf_name("20260131", "Report", "{date}_{category}")


def test_rename_pdf_appends_a_numeric_suffix_for_existing_target(tmp_path: Path) -> None:
    """An existing destination must be preserved by choosing the next suffix."""
    source = tmp_path / "incoming.pdf"
    source.touch()
    (tmp_path / "20260131_Report.pdf").touch()

    success, target = pdf_rename.rename_pdf(source, "20260131_Report.pdf")

    assert success is True
    assert target == tmp_path / "20260131_Report_1.pdf"
    assert not source.exists()
    assert target.exists()


def test_rename_pdf_preserves_a_dangling_destination_entry(tmp_path: Path) -> None:
    """A dangling entry must force a suffix instead of being replaced by a rename."""
    source = tmp_path / "incoming.pdf"
    source.write_text("source document", encoding="utf-8")
    destination = tmp_path / "20260131_Report.pdf"
    destination.symlink_to("missing.pdf")

    success, target = pdf_rename.rename_pdf(source, destination.name)

    assert success is True
    assert target == tmp_path / "20260131_Report_1.pdf"
    assert target.read_text(encoding="utf-8") == "source document"
    assert destination.is_symlink()
    assert destination.readlink() == Path("missing.pdf")


def test_rename_pdf_keeps_multibyte_collision_names_within_byte_limit(tmp_path: Path) -> None:
    """Collision suffixes must preserve the byte limit without splitting Unicode text."""
    source = tmp_path / "incoming.pdf"
    source.touch()
    name = pdf_rename.format_pdf_name("20260131", "ä" * 120, "{date}_{title}")
    assert len(name.encode("utf-8")) <= pdf_rename.MAX_FILENAME_LENGTH
    (tmp_path / name).touch()

    success, target = pdf_rename.rename_pdf(source, name)

    assert success is True
    assert target.name == f"20260131_{'ä' * 112}_1.pdf"
    assert len(target.name.encode("utf-8")) <= pdf_rename.MAX_FILENAME_LENGTH


def test_rename_pdf_returns_false_when_filesystem_denies_rename(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A permission failure must not be reported as a successful rename."""
    source = tmp_path / "incoming.pdf"
    source.touch()

    def deny_link(_source: Path, _target: Path, *, follow_symlinks: bool) -> None:
        raise PermissionError("permission denied")

    monkeypatch.setattr(os, "link", deny_link)

    success, result_path = pdf_rename.rename_pdf(source, "20260131_Report.pdf")

    assert success is False
    assert result_path == source
    assert source.exists()
