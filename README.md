# Various Python Tools

This repository contains a collection of Python scripts serving different purposes:

editCreationDate.py - Updates the creation date of files based on their name.
pdfRename.py - Renames PDF files by extracting a date and a title from the text of the PDF.
ytVideoDownloader.py - Allows for downloading YouTube videos by entering the corresponding link.
Usage
Each script can be run directly. You will be prompted for the path to the corresponding folder or the YouTube link.

1. editCreationDate.py
Run the script in your terminal. You will be prompted to enter a folder path. The script will then process all PDF files in that folder, looking for a date in the format YYYYMMDD at the start of each filename. If it finds such a date, it will update the file's creation date to match.

2. pdfRename.py
Run the script in your terminal. You will be prompted to enter a folder path. The script will then process all PDF files in that folder. It will try to extract a date and a title from the text of each PDF. If it finds a date, it will rename the file to be "YYYYMMDD_title.pdf".

3. ytVideoDownloader.py
Run the script in your terminal. You will be prompted to enter a YouTube link. The script will then download the video at the highest available resolution.

## Prerequisites
The scripts require Python 3.6 or higher and the following packages:

- os
- re
- datetime
- platform
- pywintypes
- win32file
- pdfplumber
- dateparser
- pytube

These packages can be installed with pip:

pip install pywintypes win32file pdfplumber dateparser pytube

## Author
The scripts were created by Heiko Goretzki.

## License
These projects are licensed under the MIT License - see the LICENSE.md file for details.
