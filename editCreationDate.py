import os
import re
import datetime
import platform
import pywintypes
import win32file

def update_file_creation_date(folder_path, filename):
    filepath = os.path.join(folder_path, filename)
    pattern = r'^(\d{4})(\d{2})(\d{2})_.*\.pdf$'
    match = re.match(pattern, filename)
    
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        
        date_time = datetime.datetime(year, month, day)
        
        if platform.system() == 'Windows':
            handle = win32file.CreateFile(filepath, win32file.GENERIC_WRITE, win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE, None, win32file.OPEN_EXISTING, win32file.FILE_ATTRIBUTE_NORMAL, None)
            win32file.SetFileTime(handle, pywintypes.Time(date_time), None, None)
            handle.close()
        else:
            epoch_time = date_time.timestamp()
            os.utime(filepath, (epoch_time, epoch_time))

    else:
        print(f"Dateiname {filename} entspricht nicht dem erwarteten Format")


def process_folder(folder_path):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            update_file_creation_date(folder_path, filename)


# Beispielaufruf der Funktion
folder_path = r"C:\Users\Shadow\Desktop\Python\Test"
process_folder(folder_path)