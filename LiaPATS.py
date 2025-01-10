from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as SEC
from pymongo import MongoClient
from bs4 import BeautifulSoup
from time import sleep
from tqdm.auto import tqdm
from datetime import datetime as dt


def lookup_normattiva():

    date = dt.today().strftime("%Y-%m-%d")

    client = MongoClient("mongodb://localhost:27017/")
    db = client["LIA-PATS"]
    collection = db["demo"]

    data = collection.aggregate([
        {"$project": {"_id":0, "title": 1, "article": 1}}
    ])
    previous = [tuple(d.values()) for d in data]

    driver = webdriver.Chrome()
    driver.get("https://www.normattiva.it/staticPage/codici")
    div = driver.find_element(By.XPATH, "/html/body/div[5]/div/div[2]")
    links = [
        (a.get_attribute("href"), a.get_attribute("text").strip()) 
    for a in div.find_elements(By.XPATH, ".//a[contains(@href, 'uri-res')]")]

    checkpoint = 30

    files = []
    sleep_time = 10
    i = 0

    for link, title in tqdm(links):

        if i > 0:
            collection.insert_many(files)
            files = []
            i = 0

        driver.get(link)
        print(driver.current_url)
        sidebar = driver.find_element(By.ID, "albero")

        for item in sidebar.find_elements(By.CLASS_NAME, "numero_articolo"):

            art_num = item.get_attribute("text")

            if (title, f"Art. {art_num}") in previous:
                print(f"({title}, Art. {art_num}) already in db")
                continue

            try:
                item.click()
            except ElementNotInteractableException:
                continue
            except ElementClickInterceptedException:
                WebDriverWait(driver, sleep_time).until(SEC.element_to_be_clickable(item))
                try:
                    item.click()
                except ElementClickInterceptedException:
                    print(f"Error clicking on article {art_num} in {title}")
                    continue

            sleep(sleep_time)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            alert = soup.find("div", class_ = "alert alert-danger")
            if alert is not None:
                return 1

            art_title = soup.find("h2", class_ = "article-num-akn")
            if art_title is None:
                print(f"No title found for article {art_num} in {title}")
            else:
                print(art_title.get_text())

            textarea = soup.find("span", class_ = "art-just-text-akn")
            if textarea is None:
                textarea = soup.find("span", class_ = "attachment-just-text")
                if textarea is None:
                    print(f"No text found for article {art_num} in {title}")
                    continue

            text = textarea.get_text()

            files.append({
                "title": title,
                "article": f"Art. {art_num}",
                "text": text,
                "date_retrieved": date
            })        

            i += 1

            if i % checkpoint == 0:
                collection.insert_many(files)
                files = []

    return 0

if __name__ == "__main__":

    exit_code = 1

    while exit_code:
        exit_code = lookup_normattiva()
        sleep(600)
    

