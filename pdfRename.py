import os
import re
import pdfplumber
import dateparser

def extract_date(text):
    patterns = [
        r'(?:Ort\s*,\s*D[au]tum)\s*[:\-]?\s*(\d{1,2}\.\s*[A-Za-zäÄöÖüÜß]+\s*\d{4}|\d{1,2}\.\d{1,2}\.\d{4})',    # Ort, Datum
        r'(?:D[au]tum\s*,\s*Ort)\s*[:\-]?\s*(\d{1,2}\.\s*[A-Za-zäÄöÖüÜß]+\s*\d{4}|\d{1,2}\.\d{1,2}\.\d{4})',    # Datum
        r'(?:Unterschrift(?:en)?)\s*[:\-]?\s*(\d{1,2}\.\s*[A-Za-zäÄöÖüÜß]+\s*\d{4}|\d{1,2}\.\d{1,2}\.\d{4})',   # Unterschriftenfeld mit Datum
        r'\b\d{1,2}\.\s*[A-Za-zäÄöÖüÜß]+\s*\d{4}\b',                                                            # Erstes gefundenes Datum
        r'\b\d{1,2}\.\d{1,2}\.\d{4}\b'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            if isinstance(matches[0], tuple):  # für die ersten drei Muster
                return dateparser.parse(matches[0][0], languages=['de'])
            else:  # für die letzten zwei Muster
                return dateparser.parse(matches[0], languages=['de'])

    return None

def load_keywords_from_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        keywords = [line.strip() for line in file.readlines()]
    return keywords

def extract_title(text):
    keywords = load_keywords_from_file('./components/keywords.txt')
    for keyword in keywords:
        pattern = r"\b{}\w*\b".format(keyword)
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).replace(" ", "_")
    return "Unbenannt"

def rename_pdf(pdf_path, new_name):
    folder = os.path.dirname(pdf_path)
    new_pdf_path = os.path.join(folder, new_name)
    os.rename(pdf_path, new_pdf_path)
    return new_pdf_path

def process_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            date = extract_date(text)
            title = extract_title(text)
            if date:
                break

    if date:
        new_pdf_name = f"{date.strftime('%Y%m%d')}_{title}.pdf"
        new_pdf_path = rename_pdf(pdf_path, new_pdf_name)
        print(f"PDF umbenannt nach: {new_pdf_path}")
    else:
        print(f"Kein Datum gefunden in {pdf_path}.")

def list_pdf_files(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.pdf')]

pdf_folder = input(r"Folder Path: ")
pdf_files = list_pdf_files(pdf_folder)

for pdf_path in pdf_files:
    process_pdf(pdf_path)