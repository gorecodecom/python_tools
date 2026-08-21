# Python Tools Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a maintained, tested, and documented version of all three Python utilities for daily local use.

**Architecture:** Preserve the three script entry points, move external effects behind small functions, use `yt-dlp` for media handling, and describe platform limitations honestly. Pin runtime and development dependencies while keeping the repository a simple script collection.

**Tech Stack:** Python 3.11+, yt-dlp 2026.8.19, yt-dlp-ejs through the default extra, pdfplumber 0.11.10, dateparser 1.4.2, tqdm 4.70.0, pywin32 312 on Windows, pytest 9.1.1, Ruff 0.16.4, FFmpeg.

**Spec:** `docs/superpowers/specs/2026-08-21-python-tools-modernization-design.md`

## Global Constraints

- Keep `projects/ytVideoDownloader.py`, `projects/pdfRename.py`, and `projects/editCreationDate.py` directly executable.
- Support Python 3.11 and newer, including Python 3.14.
- Use stable package releases current on 2026-08-21 and pin them exactly for reproducibility.
- Do not perform real network downloads in automated tests.
- Never overwrite an existing user file silently.
- Keep source comments and documentation in English.
- Keep the repository under the MIT license.
- Do not push the branch.

---

### Task 1: Reproducible project foundation

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pyproject.toml`
- Create: `projects/__init__.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: importable `projects` modules, pinned dependency installation, `pytest` discovery, and Ruff configuration used by all later tasks.

- [ ] **Step 1: Add pinned runtime dependencies**

Create `requirements.txt` with `dateparser==1.4.2`, `pdfplumber==0.11.10`, `tqdm==4.70.0`, `yt-dlp[default]==2026.8.19`, and `pywin32==312` guarded by `sys_platform == "win32"`.

- [ ] **Step 2: Add pinned development dependencies**

Create `requirements-dev.txt` that includes `-r requirements.txt`, `pytest==9.1.1`, and `ruff==0.16.4`.

- [ ] **Step 3: Configure tools and ignored artifacts**

Configure pytest with `testpaths = ["tests"]`, Ruff with target `py311` and 100-character lines, and ignore `.venv`, bytecode, pytest, Ruff, coverage, build, and editor artifacts.

- [ ] **Step 4: Verify configuration parsing**

Run: `python3 -c 'import pathlib, tomllib; tomllib.loads(pathlib.Path("pyproject.toml").read_text())'`

Expected: exit code 0.

- [ ] **Step 5: Commit**

```bash
git add .gitignore requirements.txt requirements-dev.txt pyproject.toml projects/__init__.py tests/conftest.py
git commit -m "Add reproducible Python tool configuration" -m "- Pin maintained runtime and development dependencies\n- Configure pytest, Ruff, and generated-file exclusions"
```

### Task 2: Modernize the YouTube downloader

**Files:**
- Create: `tests/test_yt_video_downloader.py`
- Modify: `projects/ytVideoDownloader.py`

**Interfaces:**
- Produces: `DownloadRequest`, `build_ydl_options(request)`, `download(request)`, `parse_args(argv=None)`, and `main(argv=None) -> int`.
- Consumes: `yt_dlp.YoutubeDL`, FFmpeg on `PATH`, and the pinned project configuration.

- [ ] **Step 1: Write failing option and CLI tests**

Cover these literal behaviors: MP3 requests contain an `FFmpegExtractAudio` postprocessor with `preferredcodec == "mp3"`; WAV requests use `"wav"`; 1080p video requests use a height-limited format selector; playlists are allowed by default; `--single` sets `noplaylist`; multiple positional URLs are accepted; no URLs trigger interactive request construction.

- [ ] **Step 2: Run tests to verify RED**

Run: `python3 -m pytest tests/test_yt_video_downloader.py -q`

Expected: failures because the new request model and option builder do not exist.

- [ ] **Step 3: Implement the request model and yt-dlp boundary**

Use a frozen dataclass for normalized request data. Build an output template ending in `%(title).180B [%(id)s].%(ext)s`, use `bestaudio/best` plus the requested FFmpeg audio postprocessor for audio, and use `bestvideo[height<=N]+bestaudio/best[height<=N]` with a best fallback for video. Invoke `YoutubeDL(options).download(urls)` and translate `DownloadError` into a user-facing non-zero exit code.

- [ ] **Step 4: Implement CLI and interactive fallback**

Support `URL...`, `-a/--audio`, `--audio-format {mp3,m4a,wav,flac}`, `--audio-quality`, `--resolution`, `-o/--output`, `--single`, and `--verbose`. If no URLs were supplied, ask for URL, audio/video choice, and relevant format or resolution.

- [ ] **Step 5: Run tests to verify GREEN**

Run: `python3 -m pytest tests/test_yt_video_downloader.py -q`

Expected: all downloader tests pass without network access.

- [ ] **Step 6: Commit**

```bash
git add projects/ytVideoDownloader.py tests/test_yt_video_downloader.py
git commit -m "Modernize YouTube downloads with yt-dlp" -m "- Support reliable audio conversion, playlists, and resolution limits\n- Add testable CLI and error handling without network-bound tests"
```

### Task 3: Harden PDF renaming

**Files:**
- Create: `tests/test_pdf_rename.py`
- Modify: `projects/pdfRename.py`

**Interfaces:**
- Produces: `sanitize_filename(value)`, `format_pdf_name(date, title, template)`, `rename_pdf(source, name, dry_run=False) -> tuple[bool, Path]`, case-insensitive `list_pdf_files`, and accurate `process_pdf` results.
- Consumes: pdfplumber, dateparser, and `projects/components/keywords.txt` resolved from `__file__`.

- [ ] **Step 1: Write failing regression tests**

Cover uppercase `.PDF` discovery, default keyword path independence from the current working directory, removal of Windows-invalid filename characters, rejection or neutralization of path traversal, numeric collision suffixes, and `False` when the filesystem rename raises `PermissionError`.

- [ ] **Step 2: Run tests to verify RED**

Run: `python3 -m pytest tests/test_pdf_rename.py -q`

Expected: the reproduced uppercase-discovery and false-success tests fail.

- [ ] **Step 3: Implement safe naming and explicit rename results**

Allow only `{date}` and `{title}` format fields, replace control and cross-platform invalid characters, cap the filename to a practical length, keep the target in the source directory, return a boolean result, and preserve collision suffixing.

- [ ] **Step 4: Improve extraction and batch processing boundaries**

Load keywords once, join extracted pages with newlines, resolve defaults relative to the script, process the first three pages, and count only confirmed or dry-run renames as successes.

- [ ] **Step 5: Run tests to verify GREEN**

Run: `python3 -m pytest tests/test_pdf_rename.py -q`

Expected: all PDF renamer tests pass.

- [ ] **Step 6: Commit**

```bash
git add projects/pdfRename.py tests/test_pdf_rename.py
git commit -m "Make PDF renaming safe and predictable" -m "- Sanitize generated names and prevent directory traversal\n- Report rename failures accurately and support uppercase PDF files"
```

### Task 4: Correct cross-platform file date handling

**Files:**
- Create: `tests/test_edit_creation_date.py`
- Modify: `projects/editCreationDate.py`

**Interfaces:**
- Produces: `extract_date_from_filename(path)`, `set_file_dates(path, date, modify_modified_date=False, system=None)`, corrected `update_file_creation_date`, `process_folder`, and `main(argv=None) -> int`.
- Consumes: `SetFile` on macOS, pywin32 on Windows, and `os.utime` only for requested modification dates.

- [ ] **Step 1: Write failing parsing, platform, and CLI tests**

Cover all three documented filename patterns, invalid calendar dates, macOS `SetFile -d`, optional mtime preservation/update, Linux refusal without `--modified-date`, Linux success with it, uppercase `.PDF`, and no interactive prompt after positional folders.

- [ ] **Step 2: Run tests to verify RED**

Run: `python3 -m pytest tests/test_edit_creation_date.py -q`

Expected: Linux semantics, modified-date behavior, uppercase discovery, and non-interactive CLI tests fail.

- [ ] **Step 3: Implement platform-specific setters**

Preserve access time when changing mtime. Use `SetFile` for macOS creation time and pywin32 `SetFileTime` for Windows creation and optional last-write time. On Linux, return a clear failure unless modification time was explicitly requested.

- [ ] **Step 4: Correct processing and CLI control flow**

Forward `modify_modified_date`, handle only directories, discover PDFs case-insensitively, prompt only without positional folders, and return 1 when failures occurred.

- [ ] **Step 5: Run tests to verify GREEN**

Run: `python3 -m pytest tests/test_edit_creation_date.py -q`

Expected: all date editor tests pass.

- [ ] **Step 6: Commit**

```bash
git add projects/editCreationDate.py tests/test_edit_creation_date.py
git commit -m "Correct cross-platform file date updates" -m "- Set creation and modification timestamps according to platform capabilities\n- Fix non-interactive execution and case-insensitive PDF discovery"
```

### Task 5: Update user documentation and license metadata

**Files:**
- Modify: `README.md`
- Verify: `LICENSE.md`

**Interfaces:**
- Consumes: the final CLIs and pinned dependency files.
- Produces: complete setup, usage, maintenance, testing, platform, legal, and troubleshooting instructions.

- [ ] **Step 1: Rewrite README around verified commands**

Document virtual-environment setup, pinned installation, FFmpeg installation hints, direct and interactive downloader examples, PDF renaming and date editing examples, Linux creation-time limitations, test/lint commands, dependency update guidance, and responsible media use.

- [ ] **Step 2: Verify MIT license**

Confirm `LICENSE.md` contains the complete MIT grant and warranty disclaimer and that README links to it. Do not replace dependency licenses with the repository license.

- [ ] **Step 3: Run every documented help command**

Run: `python3 projects/ytVideoDownloader.py --help`, `python3 projects/pdfRename.py --help`, and `python3 projects/editCreationDate.py --help` inside the configured environment.

Expected: each exits 0 without warnings.

- [ ] **Step 4: Commit**

```bash
git add README.md LICENSE.md
git commit -m "Document the modernized Python tools" -m "- Add current installation, usage, update, and verification commands\n- Clarify platform limitations and MIT licensing"
```

### Task 6: Full verification and review

**Files:**
- Modify only if verification or review reveals a defect.

**Interfaces:**
- Consumes: all previous task outputs.
- Produces: a clean, locally committed branch ready for user review but not pushed.

- [ ] **Step 1: Install the pinned environment**

Run: `python3 -m venv .venv` and `.venv/bin/python -m pip install -r requirements-dev.txt`.

Expected: installation succeeds with the exact pinned versions.

- [ ] **Step 2: Run format, lint, tests, and syntax checks**

Run: `.venv/bin/ruff format --check .`, `.venv/bin/ruff check .`, `.venv/bin/python -m pytest -q`, and `.venv/bin/python -m compileall -q projects tests`.

Expected: all commands exit 0 with no warnings or test failures.

- [ ] **Step 3: Run safe CLI smoke tests**

Run the three `--help` commands and dry-run the two file utilities against temporary controlled fixtures. Do not perform a real media download.

Expected: help exits 0, dry-runs report intended operations, and temporary fixtures remain unchanged.

- [ ] **Step 4: Request an independent code review**

Review the complete working diff against this plan for correctness, security, error handling, documentation accuracy, and test gaps. Fix all Critical and Important findings, then rerun Step 2.

- [ ] **Step 5: Confirm repository state**

Run: `git status --short --branch` and `git log --oneline --decorate origin/main..HEAD`.

Expected: the branch is not pushed, planned commits are local, and only intentional generated artifacts are ignored.

