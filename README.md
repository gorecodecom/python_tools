# Python Tools Collection

This repository contains a collection of Python utilities for file management and media tasks.

## Tools Overview

### 1. editCreationDate.py

A utility to modify file creation dates based on dates encoded in filenames.

#### Features

- Updates creation dates of PDF files based on dates in their filenames
- Supports multiple filename patterns:
  - `YYYYMMDD_*.pdf` (e.g., 20230415_document.pdf)
  - `YYYY-MM-DD_*.pdf` (e.g., 2023-04-15_document.pdf)
  - `*_YYYYMMDD.pdf` (e.g., invoice_20230415.pdf)
- Cross-platform support (Windows, macOS, Linux)
- Recursive directory processing
- Progress bars for better user experience
- Detailed logging of operations
- Dry-run mode to preview changes
- Command-line interface with various options

#### Usage

```
usage: editCreationDate.py [-h] [-r] [-m] [-d] [-v] [folders [folders ...]]

Update PDF file creation dates based on filename patterns

positional arguments:
  folders              Folders to process (optional, can input during execution)

options:
  -h, --help           show this help message and exit
  -r, --recursive      Process subfolders recursively
  -m, --modified-date  Also update modified date
  -d, --dry-run        Don't make changes, just preview
  -v, --verbose        Enable verbose logging
```

Examples:

```
# Process a specific folder
python editCreationDate.py /path/to/folder

# Process multiple folders recursively
python editCreationDate.py -r /path/to/folder1 /path/to/folder2

# Preview changes without modifying files
python editCreationDate.py -d /path/to/folder

# Run interactively
python editCreationDate.py
```

### 2. pdfRename.py

Renames PDF files by extracting dates and titles from the PDF content.

#### Features

- Extracts dates and titles from PDF text content
- Renames files to a standardized format (YYYYMMDD_title.pdf)
- Handles various date formats using dateparser
- Can process entire folders of PDF files

#### Usage
Run the script in your terminal. You will be prompted to enter a folder path. The script processes all PDF files in that folder, extracting dates and titles to rename them in a structured format.

### 3. ytVideoDownloader.py

A simple YouTube video downloader.

#### Features

- Downloads YouTube videos at the highest available resolution
- Simple command-line interface
- Progress tracking during download

#### Usage
Run the script in your terminal. When prompted, enter a YouTube link, and the script will download the video at the highest available resolution.

## Installation

### Prerequisites

- Python 3.6 or higher

### Required Packages
Different tools require different packages:

#### For editCreationDate.py

```
pip install tqdm
# For Windows only:
pip install pywin32
```

#### For pdfRename.py

```
pip install pdfplumber dateparser
```

#### For ytVideoDownloader.py

```
pip install pytube
```

### All Dependencies
To install all dependencies:

```
pip install tqdm pywin32 pdfplumber dateparser pytube
```

## Author

These scripts were created by Heiko Goretzki.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.

