"""Regression tests for safe, predictable PDF renaming."""

import logging
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

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


def test_load_keywords_filters_blank_lines_and_preserves_literals(tmp_path: Path) -> None:
    """Blank lines must not become match-all keywords or alter literal entries."""
    keywords_file = tmp_path / "keywords.txt"
    keywords_file.write_text("\nC++\n   \nAnnual report\n", encoding="utf-8")

    assert pdf_rename.load_keywords_from_file(keywords_file) == ["C++", "Annual report"]


def test_simple_title_match_treats_metacharacters_literally() -> None:
    """The simple fallback must not interpret a configured keyword as regex syntax."""
    assert pdf_rename._extract_simple_title("C++", "C++") == "C++"


def test_sanitize_filename_removes_cross_platform_invalid_characters() -> None:
    """Windows-invalid and control characters must not reach generated names."""

    assert pdf_rename.sanitize_filename('Report<>:"/\\|?*\x00') == "Report__________"


@pytest.mark.parametrize(
    "reserved_name",
    [
        "CON",
        "prn.pdf",
        "Aux.PDF",
        "nul.txt",
        "CONIN$",
        "conout$.pdf",
        "COM1.pdf",
        "com2.PDF",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1.pdf",
        "lpt2.PDF",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ],
)
def test_sanitize_filename_neutralizes_windows_reserved_device_stems(
    reserved_name: str,
) -> None:
    """Windows device names must be made safe regardless of case or extension."""
    sanitized = pdf_rename.sanitize_filename(reserved_name)

    assert sanitized.startswith("_")
    assert Path(sanitized).suffix == Path(reserved_name).suffix


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


def test_process_pdf_propagates_unsupported_format_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Invalid caller input must not be mislabeled as a malformed PDF."""
    source = tmp_path / "20260131_source.pdf"
    source.touch()
    parsed_pdf = SimpleNamespace(pages=[])
    monkeypatch.setattr(pdf_rename.pdfplumber, "open", lambda _path: nullcontext(parsed_pdf))

    with pytest.raises(ValueError, match="Unsupported format field"):
        pdf_rename.process_pdf(source, [], "{date}_{category}", dry_run=True)


def test_process_pdf_dry_run_preserves_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A dry run must report a target without changing the source directory."""
    source = tmp_path / "incoming.pdf"
    source.write_bytes(b"original PDF bytes")
    page = SimpleNamespace(extract_text=lambda: "31.01.2026 Annual report")
    parsed_pdf = SimpleNamespace(pages=[page])
    monkeypatch.setattr(pdf_rename.pdfplumber, "open", lambda _path: nullcontext(parsed_pdf))

    success, target = pdf_rename.process_pdf(source, ["Annual"], dry_run=True)

    assert success is True
    assert source.read_bytes() == b"original PDF bytes"
    assert target != source
    assert not target.exists()


def test_process_pdf_joins_only_the_first_three_pages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Title/date extraction must see newline-separated text from at most three pages."""
    source = tmp_path / "incoming.pdf"
    source.touch()
    pages = [
        SimpleNamespace(extract_text=lambda: "31.01."),
        SimpleNamespace(extract_text=lambda: "2026"),
        SimpleNamespace(extract_text=lambda: None),
        SimpleNamespace(extract_text=lambda: pytest.fail("the fourth page must not be extracted")),
    ]
    parsed_pdf = SimpleNamespace(pages=pages)

    monkeypatch.setattr(pdf_rename.pdfplumber, "open", lambda _path: nullcontext(parsed_pdf))

    assert pdf_rename.process_pdf(source, ["Annual"], dry_run=True) == (False, source)


def test_main_returns_nonzero_for_unsupported_format(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Invalid CLI formats must produce a concise usage error before file processing."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["pdfRename.py", "--format", "{date}_{category}", str(tmp_path)],
    )

    with caplog.at_level(logging.ERROR):
        result = pdf_rename.main()

    assert result == 2
    assert "Invalid filename format: Unsupported format field: category" in caplog.text


def test_main_missing_keywords_aborts_before_processing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A missing keyword source must be a usage error before any PDF is processed."""
    source = tmp_path / "incoming.pdf"
    source.touch()
    missing_keywords = tmp_path / "missing-keywords.txt"
    monkeypatch.setattr(
        sys,
        "argv",
        ["pdfRename.py", "--keywords", str(missing_keywords), str(tmp_path)],
    )
    monkeypatch.setattr(
        pdf_rename.pdfplumber,
        "open",
        lambda _path: pytest.fail("PDF processing must not start"),
    )

    with caplog.at_level(logging.ERROR):
        result = pdf_rename.main()

    assert result == 2
    assert source.exists()
    assert "Keywords file not found" in caplog.text


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_main_invalid_folder_returns_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    kind: str,
) -> None:
    """A missing path or regular file must produce a clear usage error."""
    path = tmp_path / kind
    if kind == "file":
        path.touch()
    keywords = tmp_path / "keywords.txt"
    keywords.write_text("Annual\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["pdfRename.py", "--keywords", str(keywords), str(path)],
    )

    with caplog.at_level(logging.ERROR):
        result = pdf_rename.main()

    assert result == 2
    assert "Not a directory" in caplog.text


def test_main_returns_nonzero_when_any_pdf_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A per-file parsing failure must produce a processing-error exit status."""
    source = tmp_path / "broken.pdf"
    source.touch()
    keywords = tmp_path / "keywords.txt"
    keywords.write_text("Annual\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["pdfRename.py", "--keywords", str(keywords), str(tmp_path)],
    )
    monkeypatch.setattr(
        pdf_rename.pdfplumber,
        "open",
        lambda _path: (_ for _ in ()).throw(ValueError("invalid PDF")),
    )

    assert pdf_rename.main() == 1
    assert source.exists()


def test_main_loads_keywords_once_per_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """All PDFs in one CLI batch must share one keyword-file read."""
    (tmp_path / "one.pdf").touch()
    (tmp_path / "two.pdf").touch()
    keywords = tmp_path / "keywords.txt"
    keywords.write_text("Annual\n", encoding="utf-8")
    page = SimpleNamespace(extract_text=lambda: "31.01.2026 Annual report")
    parsed_pdf = SimpleNamespace(pages=[page])
    parse_count = 0

    def open_pdf(_path: str) -> nullcontext[SimpleNamespace]:
        nonlocal parse_count
        parse_count += 1
        if parse_count == 1:
            keywords.unlink()
        return nullcontext(parsed_pdf)

    monkeypatch.setattr(
        sys,
        "argv",
        ["pdfRename.py", "--dry-run", "--keywords", str(keywords), str(tmp_path)],
    )
    monkeypatch.setattr(pdf_rename.pdfplumber, "open", open_pdf)

    assert pdf_rename.main() == 0
    assert parse_count == 2
    assert not keywords.exists()


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
