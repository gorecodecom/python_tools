# Python Tools Collection

Small command-line utilities for downloading YouTube media and organizing PDF files.

## Requirements

- Python 3.11 or newer
- FFmpeg on your `PATH` for `ytVideoDownloader.py`; it is required for audio conversion and video merging
- On macOS, `SetFile` for changing PDF creation dates (it is provided by Xcode Command Line Tools)

Install FFmpeg with your platform package manager, for example:

```bash
# macOS (Homebrew)
brew install ffmpeg

# Debian/Ubuntu
sudo apt install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

## Setup

Create and activate a virtual environment for your platform. Then run the shared installation commands to install the pinned runtime, test, and lint dependencies.

### macOS and Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install pinned dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements.txt` pins the runtime packages: `dateparser`, `pdfplumber`, `tqdm`, and `yt-dlp[default]`. `pywin32` is installed only on Windows. `requirements-dev.txt` additionally pins `pytest` and `ruff`.

## Tools

Run every command from the repository root after activating `.venv`.

### YouTube downloader

`projects/ytVideoDownloader.py` downloads YouTube audio or video with `yt-dlp`. Files are written to the current directory unless `--output` is supplied. Existing files are not overwritten.

```bash
# Display the available options
python projects/ytVideoDownloader.py --help

# Download a video directly, limiting the height to 1080 pixels
python projects/ytVideoDownloader.py --resolution 1080 --output downloads \
  'https://www.youtube.com/watch?v=VIDEO_ID'

# Extract MP3 audio from one URL
python projects/ytVideoDownloader.py --audio --audio-format mp3 --audio-quality 192 \
  --single --output downloads 'https://www.youtube.com/watch?v=VIDEO_ID'

# Start the interactive URL and media-type prompts
python projects/ytVideoDownloader.py
```

Pass multiple URLs to process several videos or playlists. Use `--single` to download only one item from a playlist, and `--verbose` to show `yt-dlp` debug output.

Only download media when you have the necessary rights and comply with the service's terms, copyright law, and local regulations.

### PDF renamer

`projects/pdfRename.py` extracts dates and titles from PDF text, then renames files. By default it uses `projects/components/keywords.txt` and creates names in the `{date}_{title}` format.

```bash
# Preview non-recursive changes before applying them
python projects/pdfRename.py --dry-run /path/to/pdfs

# Rename PDFs recursively with a custom keyword list and filename format
python projects/pdfRename.py --recursive --keywords /path/to/keywords.txt \
  --format '{title}_{date}' /path/to/pdfs

# Start interactive folder selection; type "exit" to quit
python projects/pdfRename.py
```

Use `--verbose` for additional logging. The `--format` value accepts only `{date}` and `{title}` fields.

### PDF date editor

`projects/editCreationDate.py` reads a date from PDF filenames and updates file timestamps. Supported filename patterns include `YYYYMMDD_name.pdf`, `YYYY-MM-DD_name.pdf`, and `name_YYYYMMDD.pdf`.

```bash
# Preview timestamp changes
python projects/editCreationDate.py --dry-run /path/to/pdfs

# Process folders recursively and also update modification dates
python projects/editCreationDate.py --recursive --modified-date \
  /path/to/pdfs /path/to/more-pdfs

# Start interactive folder selection; type "exit" to quit
python projects/editCreationDate.py
```

On macOS, the tool uses `SetFile` to update creation time and can additionally update modification time with `--modified-date`. On Windows it requires the platform-specific `pywin32` dependency. Linux filesystems generally cannot set creation time; on Linux, use `--modified-date` to update modification time instead. The tool does not support other operating systems.

## Verification and maintenance

Run the command-line help checks, tests, and linter from the activated environment:

```bash
python projects/ytVideoDownloader.py --help
python projects/pdfRename.py --help
python projects/editCreationDate.py --help
python -m pytest
python -m ruff check .
```

Dependencies are intentionally pinned for repeatable installs. To update one, change its pinned version in `requirements.txt` or `requirements-dev.txt`, reinstall with `python -m pip install -r requirements-dev.txt`, and run the verification commands above before committing the updated lock-style files.

## License

This repository is licensed under the [MIT License](LICENSE.md). The repository license applies to this project only; third-party dependencies retain their own licenses.
