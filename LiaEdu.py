import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import regex as re
from pymongo import MongoClient
import urllib.request as urllib
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm.auto import tqdm
from utils import *

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly", 
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]
SPREADSHEET_ID = "1hgeCw-L_RsuevKQf6sgC4J2-qcG00X9kwmENU2jMCCw"
RANGE_NAME = "Fatti"


def read_google_sheet(spreadsheet_id, range_name):
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        values = result.get("values", [])

        if not values:
            print("No data found.")
            return
        else:
            return pd.DataFrame(values[1:], columns=values[0])

    except HttpError as error:
        print(f"An error occurred: {error}")


def lookup_google_pages(event_list):

    driver = webdriver.Chrome()
    length_threshold = 1000
    results = []
    for event in tqdm(event_list):
        count = 0
        offset = 0
        query = event.replace(" ", "+") + "+documenti"
        while count < 10:
            driver.get(f"https://www.google.com/search?q={query}&start={offset}&lr=lang_it&cr=countryIT")
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            search = soup.find_all('div', class_="yuRUbf")
            links = [a['href'] for s in search for a in s.find_all('a', href=True)]
            offset += len(links)
            
            for link in links:
                if link.endswith(".doc") or link.endswith(".docx") or any([s in link for s in {"prodotto", "catalogo", "amazon", "ibs.it", "libreria", "documentario", "film", "video", "podcast", "www.comune.", ".edu.it", ".wordpress", ".altervista"}]):
                    continue
                elif link.endswith(".pdf"):
                    results.extend(download_pdf_content(link))
                    count += 1

                else:
                    try:
                        with urllib.urlopen(link) as response:
                            html = response.read()
                        
                    except Exception as exc:
                        print(f"Error reading {link}: {exc}")
                        continue
                    
                    page = BeautifulSoup(html, 'html.parser')
                    text = page.get_text()
                    text = re.sub(r'[^\u0000-\u007Fà-ù]+', '', text)
                    text = re.sub(r"\n{2,}", "\n", text)
                    if len(text) < length_threshold:
                        print(f"Skipping {link} because it has too short text")
                        continue
                    results.append({"Topic": event, "Link": link, "Format": "html", "Text": text})
                    count += 1

    driver.quit()
    return results

if __name__ == "__main__":
    sheet_data = read_google_sheet(SPREADSHEET_ID, RANGE_NAME)
    print(sheet_data)
    events = sheet_data["Evento"].tolist()
    data_to_insert = lookup_google_pages(events)
    insert_into_mongodb(data_to_insert, "LIA-Edu", "demo", drop_previous = True)