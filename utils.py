import re
import urllib.request as urllib
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
from io import BytesIO
from pymongo import MongoClient
import os

NUM_WORKERS = os.cpu_count() // 2

def extract_text_from_pdf_page(pdf, page_number):
    page = pdf.pages[page_number]
    text = page.extract_text()
    text = re.sub(r"[^\u0000-\u007Fà-ù]+", '', text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text

def download_pdf_content(link, title, page_limit = 50, length_threshold = 1000, lang = "ita", num_workers = NUM_WORKERS):

    results = []

    try:
        with urllib.urlopen(link) as response:
            bytestream = BytesIO(response.read())
            pdf = PdfReader(bytestream)

    except Exception as exc:
        print(f"Error reading {link}: {exc}")
        return []

    num_pages = pdf.get_num_pages()
    print(f"PDF with {num_pages} pages found")
    if num_pages > page_limit:
        print(f"Skipping {link} because it has too many pages")
        return []
    
    bytestream.seek(0)
    native_digital = None

    front = extract_text_from_pdf_page(pdf, 0)
    if len(front) < length_threshold:
        images = convert_from_bytes(bytestream.getvalue(), last_page=1, size = (794, 1122), grayscale=True, thread_count=num_workers)
        front = ""
        for scanned_page in images:
            front += "\n" + pytesseract.image_to_string(scanned_page)
        if len(front) < length_threshold:
            print(f"Skipping {link} because it has too short text")
            return []
        else:
            native_digital = False
    else:
        native_digital = True

    results.append({"Topic": title, "Link": link, "Format": "pdf", "Page":0, "Text": front})

    if native_digital:
        for i in range(1, num_pages):
            text = extract_text_from_pdf_page(pdf, i)
            results.append({"Topic": title, "Link": link, "Format": "pdf", "Page":i, "Text": text})
    else:
        for i in range(1, num_pages):
            images = convert_from_bytes(bytestream.getvalue(), first_page=i+1, last_page=i+1, size = (794, 1122), grayscale=True, thread_count=num_workers)
            text = ""
            for scanned_page in images:
                text += "\n" + pytesseract.image_to_string(scanned_page)
            results.append({"Topic": title, "Link": link, "Format": "pdf", "Page":i, "Text": text})
    
    return results

def insert_into_mongodb(data, db_name, cll_name, drop_previous):
    client = MongoClient("mongodb://localhost:27017/")
    db = client[db_name]
    if drop_previous and cll_name in db:
        db.drop_collection(cll_name)
    collection = db[cll_name]
    collection.insert_many(data)