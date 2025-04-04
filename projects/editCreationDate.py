import os
import re
import datetime
import platform
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('file_date_editor')

# Platform-specific imports
if platform.system() == 'Windows':
    try:
        import win32file
        import win32con
        from win32com.propsys import propsys
    except ImportError:
        logger.error("Required package 'pywin32' is not installed. Please install it using: pip install pywin32")
        raise SystemExit(1)
elif platform.system() == 'Darwin':  # macOS
    import subprocess

def update_file_creation_date(filepath, dry_run=False):
    """Update a file's creation date based on its filename."""
    filename = os.path.basename(filepath)

    # Support multiple filename patterns
    patterns = [
        r'^(\d{4})(\d{2})(\d{2})_.*\.pdf$',  # YYYYMMDD_*.pdf
        r'^(\d{4})-(\d{2})-(\d{2})_.*\.pdf$',  # YYYY-MM-DD_*.pdf
        r'^.*_(\d{4})(\d{2})(\d{2})\.pdf$'    # *_YYYYMMDD.pdf
    ]
    
    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))

            # Validate date
            try:
                date_time = datetime.datetime(year, month, day)
            except ValueError:
                logger.warning(f"Invalid date in filename: {filename}")
                return False

            if dry_run:
                logger.info(f"Would set creation date of {filename} to {date_time.strftime('%Y-%m-%d')}")
                return True

            try:
                if platform.system() == 'Windows':
                    filetime = win32file.CreateFileTime(date_time)
                    handle = win32file.CreateFile(
                        str(filepath),
                        win32file.GENERIC_WRITE,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
                        None,
                        win32file.OPEN_EXISTING,
                        win32file.FILE_ATTRIBUTE_NORMAL,
                        None
                    )
                    win32file.SetFileTime(handle, filetime, None, None)
                    handle.close()
                elif platform.system() == 'Darwin':  # macOS
                    # Format date for SetFile command
                    date_str = date_time.strftime("%m/%d/%Y %H:%M:%S")
                    subprocess.run(['SetFile', '-d', date_str, str(filepath)], check=True)
                else:  # Unix/Linux
                    epoch_time = date_time.timestamp()
                    os.utime(filepath, (epoch_time, epoch_time))
                
                logger.debug(f"Updated creation date for {filename} to {date_time.strftime('%Y-%m-%d')}")
                return True
            except Exception as e:
                logger.error(f"Error updating {filename}: {str(e)}")
                return False
                
    logger.info(f"Filename {filename} doesn't match any supported pattern")
    return False

def process_folder(folder_path, recursive=False, modify_modified_date=False, dry_run=False):
    """Process all PDF files in the given folder and optionally its subfolders."""
    try:
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"Folder not found: {folder_path}")
            return 0, 0
            
        # Get all PDF files
        if recursive:
            pdf_files = list(folder.glob('**/*.pdf'))
        else:
            pdf_files = list(folder.glob('*.pdf'))
            
        if not pdf_files:
            logger.info(f"No PDF files found in {folder_path}")
            return 0, 0
            
        success_count = 0
        fail_count = 0
        
        # Use tqdm for progress bar
        for pdf_file in tqdm(pdf_files, desc=f"Processing {folder_path}"):
            success = update_file_creation_date(pdf_file, dry_run)
            if success:
                success_count += 1
            else:
                fail_count += 1
                
        return success_count, fail_count
        
    except PermissionError:
        logger.error(f"Permission denied accessing folder: {folder_path}")
        return 0, 0
    except Exception as e:
        logger.error(f"Error processing folder {folder_path}: {str(e)}")
        return 0, 0

def main():
    parser = argparse.ArgumentParser(description='Update PDF file creation dates based on filename patterns')
    parser.add_argument('folders', nargs='*', help='Folders to process (optional, can input during execution)')
    parser.add_argument('-r', '--recursive', action='store_true', help='Process subfolders recursively')
    parser.add_argument('-m', '--modified-date', action='store_true', help='Also update modified date')
    parser.add_argument('-d', '--dry-run', action='store_true', help="Don't make changes, just preview")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    print("\nEdit Creation Date Tool (Improved)\n")
    print("===============")
    print("Type 'exit' to quit the program.")
    print("===============\n")
    
    if args.dry_run:
        print("*** DRY RUN MODE - No files will be modified ***\n")
    
    total_processed = 0
    total_failed = 0
    
    # Process folders from command line arguments
    if args.folders:
        for folder in args.folders:
            success, failed = process_folder(
                folder, 
                recursive=args.recursive,
                modify_modified_date=args.modified_date,
                dry_run=args.dry_run
            )
            total_processed += success
            total_failed += failed
    
    # Interactive mode
    folder_path = input("Folder path (or 'exit' to quit): ")
    
    while folder_path.lower() != 'exit':
        if folder_path.strip():
            success, failed = process_folder(
                folder_path, 
                recursive=args.recursive,
                modify_modified_date=args.modified_date,
                dry_run=args.dry_run
            )
            total_processed += success
            total_failed += failed
            
            print(f"Files processed: {success}, Failed: {failed}\n")
            
        folder_path = input("Folder path (or 'exit' to quit): ")
    
    print(f"\nSummary: Total files processed: {total_processed}, Failed: {total_failed}")
    print("Program completed.")

if __name__ == '__main__':
    main()
