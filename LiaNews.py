from selenium import webdriver
from bs4 import BeautifulSoup
import re
import time
from tqdm.auto import tqdm
from utils import *

def lookup_documents(url: str):

    results = []

    driver = webdriver.Chrome()
    driver.get(url)

    pdf_regex = re.compile(r"\S+\.pdf\b")

    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = soup.find_all('a', {'href': pdf_regex})
    url_base = re.split(r"\/\w(?!ww)", url)[0]

    for link in tqdm(links):

        page = url_base + link['href']

        page_results = download_pdf_content(page, url_base, page_limit=100, length_threshold=100)

        results.extend(page_results)

    return results

if __name__ == "__main__":

    url = "https://www.comune.bergamo.it/pianificazione/piano-di-governo-del-territorio-pgt-vigente#edit-group-documenti"

    results = lookup_documents(url)

    insert_into_mongodb(results, "LIA-News", "demo", drop_previous=True)