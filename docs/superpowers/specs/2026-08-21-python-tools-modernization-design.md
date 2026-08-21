# Python Tools Modernization Design

## Goal

Modernize the three existing utilities without breaking their script entry points, make installation reproducible, correct the known functional bugs, and leave the repository ready for daily local use on maintained Python versions.

## Supported Environment

- Python 3.11 or newer, including Python 3.14.
- macOS, Windows, and Linux where the underlying operating system supports the requested operation.
- Stable package releases available on 2026-08-21.
- FFmpeg is an external runtime requirement for media conversion and merged high-resolution video downloads.

## Architecture

The utilities remain independent scripts in `projects/` so existing direct invocations continue to work. Each script exposes small, typed functions that can be tested without network access or real platform-specific file mutation. Command-line parsing and interactive prompting stay at the boundary.

Dependency versions are pinned in `requirements.txt` and `requirements-dev.txt` for a reproducible setup tomorrow. `pyproject.toml` contains pytest and Ruff configuration only; this repository remains a script collection rather than pretending to be an installable library.

## YouTube Downloader

Replace `pytubefix`, `pydub`, the custom URL regex, and the custom progress bar with the maintained `yt-dlp` Python API. The CLI accepts one or more URLs, supports video or audio output, handles playlists natively, permits a maximum video resolution, and supports MP3, M4A, WAV, and FLAC audio. With no URL it falls back to a short interactive prompt.

The downloader builds deterministic `yt-dlp` options in a pure function. A separate boundary invokes `YoutubeDL`, making option behavior testable without network calls. Audio conversion always uses the requested codec and FFmpeg; missing FFmpeg produces a clear error before work starts. `yt-dlp` owns safe output naming, playlist handling, retries, progress, merging, and post-processing.

## PDF Renamer

Keep the existing date and keyword extraction behavior, but load keywords once per run, resolve the default keyword file relative to the script, discover `.pdf` case-insensitively, join page text safely, and sanitize generated names on all supported platforms. Custom formats may use only `{date}` and `{title}` and cannot move files outside their source directory.

Renaming returns an explicit success state. Permission errors and other failed filesystem operations no longer count as successful processing. Existing files receive a numeric suffix rather than being overwritten.

## File Date Editor

Extract filename date parsing from platform mutation. On macOS, `SetFile` sets the creation date and `os.utime` optionally sets the modification date. On Windows, `pywin32` `SetFileTime` sets creation time and optionally last-write time. Linux does not expose a portable creation-time setter; the tool reports that limitation and only succeeds when `--modified-date` explicitly requests an mtime update.

Positional folders run non-interactively. Interactive mode is used only when no folder argument is supplied. PDF discovery is case-insensitive, invalid folders are rejected, and the process returns a non-zero exit code when any file fails.

## Quality and Documentation

Pytest regression tests cover the reproduced bugs and core pure functions. Ruff supplies linting and formatting with a Python 3.11 target. The README documents setup, FFmpeg, every CLI, platform limitations, update commands, test commands, responsible download usage, and the MIT license. The existing MIT license text remains authoritative.

