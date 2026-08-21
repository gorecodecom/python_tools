import argparse
import logging
import os
import re
from pathlib import Path
from string import Formatter

import dateparser
import pdfplumber

DEFAULT_KEYWORDS_FILE = Path(__file__).resolve().parent / "components" / "keywords.txt"
MAX_FILENAME_LENGTH = 240
ALLOWED_FORMAT_FIELDS = {"date", "title"}
LOGGER = logging.getLogger(__name__)


def extract_date(text, filename=None):
    patterns = [
        # Ort, Datum
        r'(?:Ort\s*,\s*D[au]tum)\s*[:\-]?\s*(\d{1,2}\.\s*[A-Za-zäÄöÖüÜß]+\s*\d{4}|\d{1,2}\.\d{1,2}\.\d{4})',
        # Datum
        r'(?:D[au]tum\s*,\s*Ort)\s*[:\-]?\s*(\d{1,2}\.\s*[A-Za-zäÄöÖüÜß]+\s*\d{4}|\d{1,2}\.\d{1,2}\.\d{4})',
        # Unterschriftenfeld mit Datum
        r'(?:Unterschrift(?:en)?)\s*[:\-]?\s*(\d{1,2}\.\s*[A-Za-zäÄöÖüÜß]+\s*\d{4}|\d{1,2}\.\d{1,2}\.\d{4})',
        # DD.MM.YYYY
        r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b',
        # DD. Month YYYY
        r'\b(\d{1,2}\.\s*[A-Za-zäÄöÖüÜß]+\s*\d{4})\b',
        # YYYY-MM-DD
        r'\b(\d{4}-\d{1,2}-\d{1,2})\b',
        # DD/MM/YYYY
        r'\b(\d{1,2}/\d{1,2}/\d{4})\b',
    ]

    # Try to find date in text
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            if isinstance(matches[0], tuple):  # für die ersten drei Muster
                return dateparser.parse(matches[0][0], languages=['de'])
            else:  # für die letzten vier Muster
                return dateparser.parse(matches[0], languages=['de'])

    # Fallback: Try to extract date from filename
    if filename:
        # Try to find YYYYMMDD at start of filename
        filename_match = re.search(r'^(\d{8})_', os.path.basename(filename))
        if filename_match:
            date_str = filename_match.group(1)
            return dateparser.parse(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}")
        
        # Try other date formats in filename
        date_patterns = [
            # YYYY-MM-DD
            r'(\d{4}-\d{2}-\d{2})',
            # DD.MM.YYYY
            r'(\d{2}\.\d{2}\.\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, os.path.basename(filename))
            if match:
                return dateparser.parse(match.group(1))

    return None


def load_keywords_from_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            keywords = [line.strip() for line in file.readlines()]
        return keywords
    except FileNotFoundError:
        logging.error(f"Keywords file not found: {filename}")
        return []
    except Exception as e:
        logging.error(f"Error loading keywords file: {e}")
        return []


def extract_title(text, keywords):
    if not keywords:
        return "Unknown"
    
    # Sort keywords by length (longest first) to prioritize more specific matches
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    
    for keyword in sorted_keywords:
        # First try to find a complete title with numbers and special characters
        # Look for up to 5 words before and after the keyword
        title_pattern = r'(?:[\w\d][^\n\r.]{0,30}\s+){0,5}' + re.escape(keyword) + r'(?:\s+[^\n\r.]{0,30}[\w\d]){0,5}'
        title_match = re.search(title_pattern, text, re.IGNORECASE)
        
        if title_match:
            # Clean up the title: remove excess whitespace and truncate if too long
            title = title_match.group(0).strip()
            
            # Handle titles that are too long (cap at 80 chars)
            if len(title) > 80:
                # Try to find a natural break point
                last_space = title[:80].rfind(' ')
                if last_space > 40:  # Only truncate if we have a reasonable title length
                    title = title[:last_space]
            
            # Replace problematic characters and multiple spaces
            title = re.sub(r'\s+', ' ', title)  # Replace multiple spaces with single space
            title = title.replace('/', '_').replace('\\', '_')
            title = title.replace(':', '_').replace(';', '_')
            title = title.replace('"', '').replace("'", "")
            title = title.replace(' ', '_')
            
            return title
        
        # Fallback to the original simple pattern if the complex one doesn't match
        simple_pattern = r"\b{}\w*\b".format(keyword)
        simple_match = re.search(simple_pattern, text, re.IGNORECASE)
        if simple_match:
            return simple_match.group(0).replace(" ", "_")
            
    return "Unknown"


def sanitize_filename(value):
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value))
    sanitized = sanitized.replace('..', '').strip().strip('.').lstrip('_')
    return sanitized or 'untitled'


def _truncate_utf8(value, maximum_bytes):
    encoded = bytearray()
    for character in value:
        character_bytes = character.encode("utf-8")
        if len(encoded) + len(character_bytes) > maximum_bytes:
            break
        encoded.extend(character_bytes)
    return encoded.decode("utf-8")


def _build_filename(stem, extension, counter=None):
    collision_suffix = f"_{counter}" if counter is not None else ""
    reserved_bytes = len(f"{collision_suffix}{extension}".encode())
    return f"{_truncate_utf8(stem, MAX_FILENAME_LENGTH - reserved_bytes)}{collision_suffix}{extension}"


def format_pdf_name(date, title, template):
    for _, field_name, format_spec, conversion in Formatter().parse(template):
        if field_name is not None and (
            field_name not in ALLOWED_FORMAT_FIELDS or format_spec or conversion
        ):
            raise ValueError(f"Unsupported format field: {field_name}")

    filename = sanitize_filename(
        template.format(date=sanitize_filename(date), title=sanitize_filename(title))
    )
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'

    filename_path = Path(filename)
    return _build_filename(filename_path.stem, filename_path.suffix)


def rename_pdf(source, name, dry_run=False):
    source_path = Path(source)
    source_directory = source_path.parent.resolve()
    name_path = Path(sanitize_filename(name))
    target_path = source_directory / _build_filename(name_path.stem, name_path.suffix)

    try:
        target_path.resolve().relative_to(source_directory)
    except ValueError:
        LOGGER.error(f"Refusing to rename outside source directory: {source_path}")
        return False, source_path
    
    if source_path.resolve() == target_path.resolve():
        return True, source_path
    
    if dry_run:
        counter = 1
        while os.path.lexists(target_path):
            target_path = source_directory / _build_filename(
                name_path.stem, name_path.suffix, counter
            )
            counter += 1
        LOGGER.info(f"Would rename: {source_path} -> {target_path}")
        return True, target_path
    
    counter = 1
    while True:
        try:
            os.link(source_path, target_path, follow_symlinks=False)
        except FileExistsError:
            target_path = source_directory / _build_filename(
                name_path.stem, name_path.suffix, counter
            )
            counter += 1
            continue
        except PermissionError:
            LOGGER.error(f"Permission denied when renaming {source_path}")
            return False, source_path
        except OSError as error:
            LOGGER.error(f"Error renaming {source_path}: {error}")
            return False, source_path

        try:
            source_path.unlink()
        except OSError as error:
            LOGGER.error(f"Could not remove source after linking {source_path}: {error}")
            return False, source_path

        LOGGER.info(f"Renamed: {source_path} -> {target_path}")
        return True, target_path


def process_pdf(pdf_path, keywords, name_format="{date}_{title}", dry_run=False):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages[:3])
            
            # Pass filename to extract_date as fallback
            date = extract_date(text, pdf_path)
            title = extract_title(text, keywords)
            
        if date:
            date_str = date.strftime('%Y%m%d')
            new_pdf_name = format_pdf_name(date_str, title, name_format)
                
            # Skip if the file already has the correct name format
            if os.path.basename(pdf_path) == new_pdf_name:
                logging.info(f"File already has correct name: {pdf_path}")
                return True, pdf_path
                
            return rename_pdf(pdf_path, new_pdf_name, dry_run)
        else:
            logging.warning(f"No date found in {pdf_path}")
            return False, pdf_path
            
    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {e}")
        return False, pdf_path


def list_pdf_files(folder, recursive=False):
    folder_path = Path(folder)
    if not folder_path.exists():
        logging.error(f"Folder not found: {folder}")
        return []
        
    if recursive:
        files = folder_path.rglob('*')
    else:
        files = folder_path.iterdir()

    return [str(pdf) for pdf in files if pdf.is_file() and pdf.suffix.lower() == '.pdf']


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Rename PDF files based on content')
    parser.add_argument('folder', nargs='?', help='Folder containing PDF files')
    parser.add_argument('-k', '--keywords', default=str(DEFAULT_KEYWORDS_FILE),
                        help='Path to keywords file')
    parser.add_argument('-r', '--recursive', action='store_true', 
                        help='Process folders recursively')
    parser.add_argument('-f', '--format', default='{date}_{title}',
                        help='Filename format (default: {date}_{title})')
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='Preview changes without renaming files')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    return parser.parse_args(argv)


def main():
    args = parse_args()
    setup_logging(args.verbose)
    
    print("\nPDF Rename Tool\n")
    print("===============")
    
    if args.dry_run:
        print("Running in DRY RUN mode - no files will be renamed")
    
    # If folder is provided as argument, process it directly
    if args.folder:
        folder_path = args.folder
    else:
        # Interactive mode
        print("Type 'exit' to quit the program.")
        print("===============\n")
        folder_path = input("Folder Path: ")
    
    while folder_path.lower() != 'exit':
        pdf_files = list_pdf_files(folder_path, args.recursive)
        
        if not pdf_files:
            logging.warning(f"No PDF files found in {folder_path}")
        else:
            logging.info(f"Found {len(pdf_files)} PDF files")
            keywords = load_keywords_from_file(args.keywords)
            
            success_count = 0
            for i, pdf_path in enumerate(pdf_files, 1):
                logging.info(f"Processing file {i}/{len(pdf_files)}: {pdf_path}")
                success, _ = process_pdf(
                    pdf_path, 
                    keywords,
                    args.format,
                    args.dry_run
                )
                if success:
                    success_count += 1
            
            logging.info(f"Successfully processed {success_count} out of {len(pdf_files)} files")
        
        # Only ask for new input in interactive mode
        if not args.folder:
            folder_path = input("Folder Path: ")
        else:
            break


if __name__ == '__main__':
    main()
