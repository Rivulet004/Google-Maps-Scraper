import sys
import pyperclip
import os
import time
import csv
import urllib.parse
from facebook_scraper import FacebookEmailScraper
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    TimeoutException
    # StaleElementReferenceException
)

from exception_handler import handle_stale_exception

# Color and Styles for the output

Red = "\033[31m"
Green = "\033[32m"
Yellow = "\033[33m"
Blue = "\033[34m"
Magenta = "\033[35m"
Cyan = "\033[36m"
White = "\033[37m"
Reset = "\033[0m"
Bold = "\x1b[1m"
Underline = "\x1b[4m"
blink = "\x1b[5m"
reverse = "\x1b[7m"


class ScrapGoogleMap:
    def __init__(self, query, location, business_type):
        self.query = query
        self.location = location
        self.type = business_type
        self.driver = webdriver.Firefox()
        self.all_listings = []
        self.list_info = []
        self.location_data = {}
        self.counter = 0
        self.fb_email_scraper = FacebookEmailScraper(self.driver)

    def open_google_maps(self):
        base_url = "https://www.google.com/maps/search/"
        encoded_url = urllib.parse.quote(self.query)
        url = base_url + encoded_url

        print(Yellow + f"Opening Google Maps for query: {self.query}" + Reset)
        self.driver.get(url)
        print(Green + "Google Maps opened" + Reset)

    def scroll_to_load_all_listings(self):
        try:
            div_sidebar = self.driver.find_element(
                By.CSS_SELECTOR, f"div[aria-label='Results for {self.query}']"
            )
            keep_scrolling = True
            print(Yellow + "Scrolling through listings to load all results..." + Reset)
            print(Bold + Red + "Warning: This will take a while" + Reset)
            while keep_scrolling:
                div_sidebar.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.5)
                div_sidebar.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.5)
                html = self.driver.find_element(By.TAG_NAME, "html").get_attribute(
                    "outerHTML"
                )
                if "You've reached the end of the list." in html:
                    keep_scrolling = False
            print(Green + "All listings loaded" + Reset)
        except NoSuchElementException:
            print(Red + Bold + "No listings loaded" + Reset)

    def retrieve_listings(self):
        print(f"Retrieving all listings for query: {self.query}")
        self.all_listings = self.driver.find_elements(By.CLASS_NAME, "hfpxzc")
        if self.all_listings:
            print(f"{len(self.all_listings)} listings retrieved")
            self.counter = len(self.all_listings)
        else:
            print(Yellow + "No listings found" + Reset)

    def collect_listing_data(self):
        i = 1
        if not self.all_listings:
            self.print_no_listings_message()
            return
        for listing in self.all_listings:
            self.print_collecting_message(i)
            if not self.click_listing(listing):
                i += 1
                continue

            self.initialize_location_data()
            self.extract_listing_data()
            self.assign_collected_data()

            self.list_info.append(self.location_data)
            self.print_collected_data_message(i)
            i += 1

    def print_no_listings_message(self):
        print(Red + "No listings found to collect data from." + Reset)

    def print_collecting_message(self, i):
        print(Yellow + f"Collecting data from listing {i}..." + Reset)

    def click_listing(self, listing):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", listing)
            time.sleep(0.2)
            self.driver.execute_script("arguments[0].click();", listing)
            print("Element clicked")
            time.sleep(0.3)
            return True
        except ElementClickInterceptedException:
            print(Red + "Listing is not clickable. Skipping to the next listing." + Reset)
            return False

    def initialize_location_data(self):
        self.location_data = {
            "name": "NA",
            "type": "NA",
            "email": "NA",
            "listing-url": "NA",
            "rating": "NA",
            "reviews_count": "NA",
            "location": "NA",
            "contact": "NA",
            "website": "NA",
            "claimed": "NA",
        }

    def extract_listing_data(self):
        self.name = self.get_element_text(By.CSS_SELECTOR, ".DUwDvf.lfPIob")
        self.listing_url = self.driver.current_url
        self.type_of_business = self.get_element_text(By.CLASS_NAME, "DkEaL")
        self.avg_rating = self.get_element_text(By.CSS_SELECTOR, ".F7nice > span > span[aria-hidden='true']")
        self.total_reviews = self.get_element_text(By.CSS_SELECTOR,
                                                   ".F7nice > span > span > span[aria-label*='reviews']")
        self.address = self.get_element_text(By.CSS_SELECTOR, "[data-item-id='address']")
        self.phone_number = self.get_element_text(By.CSS_SELECTOR, "[data-tooltip='Copy phone number']")
        self.website_url = self.get_website_url()
        self.is_not_claimed = self.get_element(By.CSS_SELECTOR, "a[data-item-id='merchant'] .Io6YTe")
        if self.website_url:
            if "www.facebook.com" in self.website_url:
                self.email = self.fb_email_scraper.get_email(self.website_url)
            else:
                self.email = "NA"
        else:
            self.email = "NA"

    def get_element(self, by, value):
        if value == ".DUwDvf.lfPIob":
            try:
                element = WebDriverWait(self.driver, 2).until(EC.presence_of_element_located((by, value)))
                # return self.driver.find_element(by, value)
                return element
            except (NoSuchElementException, TimeoutException) as e:
                print('No such element' + value)
                print(e)
                return None
        else:
            try:
                return self.driver.find_element(by, value)
            except NoSuchElementException as e:
                print('No such element' + value)
                print(e)
                return None

    @handle_stale_exception(3)
    def get_element_text(self, by, value):
        if element := self.get_element(by, value):
            return element.text
        else:
            return None

    @handle_stale_exception(3)
    def get_website_url(self):
        if website_element := self.get_element(By.CSS_SELECTOR, "a.lcr4fd.S9kvJb[data-tooltip='Open website']"):
            return website_element.get_attribute('href')
        else:
            return None

    def assign_collected_data(self):
        self.location_data["name"] = self.name if self.name else "NA"
        self.location_data["type"] = self.type_of_business if self.type_of_business else "NA"
        self.location_data["listing-url"] = self.listing_url if self.listing_url else "NA"
        self.location_data["rating"] = self.avg_rating if self.avg_rating else "NA"
        self.location_data["reviews_count"] = self.total_reviews if self.total_reviews else "NA"
        self.location_data["location"] = self.address if self.address else "NA"
        self.location_data["contact"] = self.phone_number if self.phone_number else "NA"
        self.location_data["website"] = self.website_url if self.website_url else "NA"
        self.location_data["claimed"] = False if self.is_not_claimed else True
        self.location_data["email"] = self.email

    def print_collected_data_message(self, i):
        print(Green + f"Collected data from listing {i}:" + Reset)
        print(Blue + f"{self.location_data}" + Reset)

    def save_data_to_csv(self):
        print(Yellow + "Saving collected data to CSV file..." + Reset)
        if not self.list_info:
            print(Red + "No data to write to CSV." + Reset)
            return
        with open(
                f"data/{self.location}/{self.query}.csv",
                mode="w",
                newline="",
                encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(file, fieldnames=self.list_info[0].keys())

            writer.writeheader()

            for row in self.list_info:
                writer.writerow(row)
        print(Green + f"Data saved to {self.query}.csv successfully." + Reset)

    def close_browser(self):
        print(Yellow + "Closing the browser..." + Reset)
        self.driver.quit()
        print(Green + "Browser closed" + Reset)


def main():
    if len(sys.argv) > 1:
        location = " ".join(sys.argv[1:])
    else:
        location = pyperclip.paste()

    # Check if the directory exists to save file if not then create the directory
    if not os.path.exists(f"data/{location}"):
        os.makedirs(f"data/{location}")

    with open("business_list.txt", "r") as file:
        business_list = file.readlines()

    cleaned_business_list = [entry.strip() for entry in business_list]
    total_counter = 0

    for business_type in cleaned_business_list:
        query = f"{business_type} in {location}"
        print(
            Cyan
            + "<――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――>"
            + Reset
        )
        print(Magenta + f"Initializing Scraper for the query: {query}" + Reset)
        scraper = ScrapGoogleMap(query, location, business_type)
        print(Green + f"Scraper initialized" + Reset)
        scraper.open_google_maps()
        scraper.scroll_to_load_all_listings()
        scraper.retrieve_listings()
        total_counter += scraper.counter
        scraper.collect_listing_data()
        scraper.save_data_to_csv()
        scraper.close_browser()
        print(Green + f"Data Scraped for the query: {query}" + Reset)
        print(Red + f"total entries as of yet {total_counter}" + Reset)
        print(
            Cyan
            + "<――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――>"
            + Reset
        )

    print(Yellow + "Terminating Program" + Reset)
    print(Red + "Program Terminated Successfully" + Reset)


if __name__ == "__main__":
    main()
