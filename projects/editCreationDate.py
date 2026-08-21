# SPDX-License-Identifier: MIT
"""Update PDF timestamps from dates embedded in their filenames."""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import platform
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("file_date_editor")

DATE_PATTERNS = (
    re.compile(r"^(\d{4})(\d{2})(\d{2})_.*\.pdf$", re.IGNORECASE),
    re.compile(r"^(\d{4})-(\d{2})-(\d{2})_.*\.pdf$", re.IGNORECASE),
    re.compile(r"^.*_(\d{4})(\d{2})(\d{2})\.pdf$", re.IGNORECASE),
)


def extract_date_from_filename(path: str | Path) -> datetime.datetime | None:
    """Return a validated date from a supported PDF filename."""
    filename = Path(path).name

    for pattern in DATE_PATTERNS:
        match = pattern.match(filename)
        if match is None:
            continue

        try:
            # Filename dates represent local wall-clock time for filesystem tools.
            return datetime.datetime(  # noqa: DTZ001
                *(int(part) for part in match.groups())
            )
        except ValueError:
            logger.warning("Invalid date in filename: %s", filename)
            return None

    logger.info("Filename %s doesn't match any supported pattern", filename)
    return None


def _set_modified_date(path: Path, date: datetime.datetime) -> None:
    """Set mtime while preserving the file's existing access time."""
    access_time_ns = path.stat().st_atime_ns
    modified_time_ns = int(date.timestamp() * 1_000_000_000)
    os.utime(path, ns=(access_time_ns, modified_time_ns))


def _supports_date_update(system_name: str, modify_modified_date: bool) -> bool:
    """Return whether the platform can perform the requested timestamp update."""
    if system_name == "Linux" and not modify_modified_date:
        logger.error(
            "Linux does not support setting file creation time; "
            "use --modified-date to update mtime instead"
        )
        return False
    if system_name not in {"Darwin", "Windows", "Linux"}:
        logger.error("Unsupported operating system: %s", system_name)
        return False
    return True


def set_file_dates(
    path: str | Path,
    date: datetime.datetime,
    modify_modified_date: bool = False,
    system: str | None = None,
) -> bool:
    """Set supported file timestamps for the selected operating system."""
    file_path = Path(path)
    if file_path.is_symlink():
        logger.error("Refusing to update symbolic link: %s", file_path)
        return False

    system_name = system or platform.system()
    if not _supports_date_update(system_name, modify_modified_date):
        return False

    try:
        if system_name == "Darwin":
            date_string = date.strftime("%m/%d/%Y %H:%M:%S")
            subprocess.run(["SetFile", "-d", date_string, str(file_path)], check=True)
            if modify_modified_date:
                _set_modified_date(file_path, date)
            return True

        if system_name == "Windows":
            import pywintypes
            import win32file

            file_time = pywintypes.Time(date)
            handle = win32file.CreateFile(
                str(file_path),
                win32file.GENERIC_WRITE,
                win32file.FILE_SHARE_READ
                | win32file.FILE_SHARE_WRITE
                | win32file.FILE_SHARE_DELETE,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None,
            )
            try:
                last_write_time = file_time if modify_modified_date else None
                win32file.SetFileTime(handle, file_time, None, last_write_time)
            finally:
                handle.Close()
            return True

        _set_modified_date(file_path, date)
        return True
    except (ImportError, OSError, ValueError, OverflowError, subprocess.SubprocessError) as error:
        logger.error("Error updating %s: %s", file_path.name, error)
        return False


def update_file_creation_date(
    filepath: str | Path,
    dry_run: bool = False,
    modify_modified_date: bool = False,
    system: str | None = None,
) -> bool:
    """Update a file's supported timestamps based on its filename."""
    file_path = Path(filepath)
    if file_path.is_symlink():
        logger.error("Refusing to process symbolic link: %s", file_path)
        return False

    date = extract_date_from_filename(file_path)
    if date is None:
        return False

    system_name = system or platform.system()
    if dry_run:
        if not _supports_date_update(system_name, modify_modified_date):
            return False
        logger.info("Would update dates of %s to %s", file_path.name, date.strftime("%Y-%m-%d"))
        return True

    success = set_file_dates(
        file_path,
        date,
        modify_modified_date=modify_modified_date,
        system=system_name,
    )
    if success:
        logger.debug("Updated dates for %s to %s", file_path.name, date.strftime("%Y-%m-%d"))
    return success


def process_folder(
    folder_path: str | Path,
    recursive: bool = False,
    modify_modified_date: bool = False,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Process all PDF files in a directory and optionally its subdirectories."""
    folder = Path(folder_path)

    if not folder.is_dir():
        logger.error("Not a directory: %s", folder_path)
        return 0, 1

    try:
        paths = folder.rglob("*") if recursive else folder.iterdir()
        pdf_files = sorted(
            path
            for path in paths
            if path.suffix.lower() == ".pdf" and (path.is_symlink() or path.is_file())
        )
    except OSError as error:
        logger.error("Error accessing folder %s: %s", folder_path, error)
        return 0, 1

    if not pdf_files:
        logger.info("No PDF files found in %s", folder_path)
        return 0, 0

    success_count = 0
    fail_count = 0
    for pdf_file in tqdm(pdf_files, desc=f"Processing {folder_path}"):
        if pdf_file.is_symlink():
            logger.error("Refusing to process symbolic link: %s", pdf_file)
            fail_count += 1
            continue

        success = update_file_creation_date(
            pdf_file,
            dry_run=dry_run,
            modify_modified_date=modify_modified_date,
        )
        if success:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count


def main(argv: Sequence[str] | None = None) -> int:
    """Run the date editor and return a shell-compatible exit status."""
    parser = argparse.ArgumentParser(
        description="Update PDF file creation dates based on filename patterns"
    )
    parser.add_argument("folders", nargs="*", help="Folders to process")
    parser.add_argument("-r", "--recursive", action="store_true", help="Process subfolders")
    parser.add_argument(
        "-m", "--modified-date", action="store_true", help="Also update modified date"
    )
    parser.add_argument("-d", "--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    print("\nEdit Creation Date Tool\n")
    if args.dry_run:
        print("*** DRY RUN MODE - No files will be modified ***\n")

    total_processed = 0
    total_failed = 0

    def process(path: str) -> None:
        nonlocal total_processed, total_failed
        success, failed = process_folder(
            path,
            recursive=args.recursive,
            modify_modified_date=args.modified_date,
            dry_run=args.dry_run,
        )
        total_processed += success
        total_failed += failed

    if args.folders:
        for folder in args.folders:
            process(folder)
    else:
        print("Type 'exit' to quit the program.\n")
        while True:
            try:
                folder_path = input("Folder path (or 'exit' to quit): ")
            except EOFError:
                print()
                break
            if folder_path.lower() == "exit":
                break
            if folder_path.strip():
                process(folder_path)

    print(f"\nSummary: Total files processed: {total_processed}, Failed: {total_failed}")
    print("Program completed.")
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
