#!/usr/bin/env python3
"""
Final Sex Offender Registry Scraper for New Jersey State Police
Uses Selenium to bypass DataDome protection and extract structured data
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import json
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional
import requests
from urllib.parse import urljoin
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinalSexOffenderScraper:
    def __init__(self, headless: bool = False, delay: float = 2.0):
        self.delay = delay
        self.driver = None
        self.base_url = "https://www.icrimewatch.net"
        
        # Create output directories
        self.output_dir = Path("sex-offenders")
        self.images_dir = self.output_dir / "images"
        self.data_dir = self.output_dir / "data"
        
        for dir_path in [self.output_dir, self.images_dir, self.data_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Setup Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        
        # Add options to make the browser look more like a real user
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    def setup_driver(self):
        """Initialize the Chrome driver"""
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("Chrome driver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return False
    
    def wait_for_page_load(self, timeout: int = 30):
        """Wait for page to load completely"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)  # Additional wait for dynamic content
            return True
        except TimeoutException:
            logger.warning("Page load timeout")
            return False
    
    def navigate_to_search_results(self, search_url: str) -> bool:
        """Navigate to the search results page"""
        try:
            logger.info(f"Navigating to: {search_url}")
            self.driver.get(search_url)
            
            if not self.wait_for_page_load():
                return False
            
            # Check if we're blocked
            if "403" in self.driver.title or "Access Denied" in self.driver.page_source:
                logger.error("Access denied - DataDome protection active")
                return False
            
            # Check if we're on the right page
            if "results" in self.driver.current_url.lower() or "offender" in self.driver.page_source.lower():
                logger.info("Successfully loaded search results page")
                return True
            else:
                logger.warning("Page may not have loaded correctly")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to search results: {e}")
            return False
    
    def extract_offender_data(self) -> List[Dict[str, str]]:
        """Extract offender data from the current page using a more targeted approach"""
        offenders = []
        
        try:
            # Find all offender detail links first
            offender_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'offenderdetails.php')]")
            logger.info(f"Found {len(offender_links)} offender detail links")
            
            # Extract data from each link
            for i, link in enumerate(offender_links):
                try:
                    # Get the link text and URL
                    name = link.text.strip()
                    detail_url = link.get_attribute("href")
                    
                    if not name or not detail_url:
                        continue
                    
                    # Extract offender ID from URL
                    offender_id = None
                    if "OfndrID=" in detail_url:
                        offender_id = detail_url.split("OfndrID=")[1].split("&")[0]
                    
                    if not offender_id:
                        continue
                    
                    # Find the parent row to extract other data
                    row = link.find_element(By.XPATH, "./ancestor::tr")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) < 8:
                        continue
                    
                    offender_data = {
                        'offender_id': offender_id,
                        'name': name,
                        'detail_url': detail_url
                    }
                    
                    # Extract data from each cell
                    for j, cell in enumerate(cells):
                        cell_text = cell.text.strip()
                        
                        # Extract image from first cell
                        if j == 0:
                            try:
                                img_tag = cell.find_element(By.TAG_NAME, "img")
                                if img_tag:
                                    img_src = img_tag.get_attribute("src")
                                    if img_src and "pictures" in img_src:
                                        offender_data['image_url'] = img_src
                            except NoSuchElementException:
                                pass
                        
                        # Extract number (usually in second cell)
                        elif j == 1 and cell_text.isdigit():
                            offender_data['number'] = cell_text
                        
                        # Extract alert level (contains "Tier" or "Level")
                        elif "Tier" in cell_text or "Level" in cell_text:
                            offender_data['alert_level'] = cell_text
                        
                        # Extract address (contains numbers and street names)
                        elif re.search(r'\d+.*(?:ST|AVE|BLVD|DR|RD|PL|CT|WAY)', cell_text, re.IGNORECASE):
                            offender_data['address'] = cell_text
                        
                        # Extract city (all caps, no numbers)
                        elif cell_text.isupper() and not any(char.isdigit() for char in cell_text) and len(cell_text) > 3:
                            offender_data['city'] = cell_text
                        
                        # Extract ZIP (5 digits)
                        elif cell_text.isdigit() and len(cell_text) == 5:
                            offender_data['zip'] = cell_text
                        
                        # Extract address type
                        elif "Home Address" in cell_text or "Work Address" in cell_text:
                            offender_data['address_type'] = cell_text
                    
                    offenders.append(offender_data)
                    logger.info(f"Extracted data for offender {len(offenders)}: {name}")
                    
                except Exception as e:
                    logger.error(f"Error extracting data from link {i+1}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting offender data: {e}")
        
        return offenders
    
    def download_image(self, image_url: str, offender_id: str) -> Optional[str]:
        """Download offender image"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            else:
                ext = '.jpg'
            
            filename = f"{offender_id}{ext}"
            filepath = self.images_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded image: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {e}")
            return None
    
    def scrape_offender_details(self, detail_url: str) -> Dict[str, str]:
        """Scrape detailed information from individual offender page"""
        details = {}
        
        try:
            logger.info(f"Scraping details from: {detail_url}")
            self.driver.get(detail_url)
            
            if not self.wait_for_page_load():
                return details
            
            # Extract basic information from the page
            try:
                # Look for the offender name in the page title or headers
                name_element = self.driver.find_element(By.XPATH, "//h1[contains(text(), 'Offender Details')] | //h2[contains(text(), 'Offender Details')]")
                if name_element:
                    details['page_title'] = name_element.text
            except NoSuchElementException:
                pass
            
            # Extract information from tables
            try:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                for table in tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            key = cells[0].text.strip().lower().replace(':', '')
                            value = cells[1].text.strip()
                            if key and value:
                                details[key] = value
            except Exception as e:
                logger.error(f"Error extracting table data: {e}")
            
            # Extract image from detail page - try multiple selectors
            try:
                # Try different selectors for the offender image
                selectors = [
                    "//img[contains(@src, 'pictures')]",
                    "//img[contains(@src, 'offender')]",
                    "//img[contains(@src, 'photo')]",
                    "//img[contains(@src, 'mugshot')]",
                    "//img[contains(@alt, 'offender')]",
                    "//img[contains(@alt, 'photo')]",
                    "//img[contains(@alt, 'mugshot')]"
                ]
                
                for selector in selectors:
                    try:
                        img_elements = self.driver.find_elements(By.XPATH, selector)
                        for img in img_elements:
                            src = img.get_attribute("src")
                            if src and not any(skip in src.lower() for skip in ['button', 'icon', 'logo', 'header', 'nav']):
                                # Check if this looks like an offender photo
                                if any(keyword in src.lower() for keyword in ['pictures', 'offender', 'photo', 'mugshot']) or \
                                   (len(src) > 50 and any(char.isdigit() for char in src)):  # Likely has offender ID
                                    details['detail_image_url'] = src
                                    logger.info(f"Found detail page image: {src}")
                                    break
                        if 'detail_image_url' in details:
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.error(f"Error extracting image from detail page: {e}")
            
        except Exception as e:
            logger.error(f"Error scraping offender details: {e}")
        
        return details
    
    def scrape_all_offenders(self, search_url: str) -> List[Dict[str, str]]:
        """Main method to scrape all offenders"""
        if not self.setup_driver():
            return []
        
        try:
            # Navigate to search results
            if not self.navigate_to_search_results(search_url):
                return []
            
            # Extract offender data
            offenders = self.extract_offender_data()
            
            if not offenders:
                logger.warning("No offenders found on the page")
                return []
            
            # Process each offender
            for i, offender in enumerate(offenders, 1):
                logger.info(f"Processing offender {i}/{len(offenders)}: {offender.get('name', 'Unknown')}")
                
                # Download image if available
                if 'image_url' in offender:
                    image_path = self.download_image(offender['image_url'], offender.get('offender_id', f'offender_{i}'))
                    if image_path:
                        offender['local_image_path'] = image_path
                
                # Scrape detailed information
                if 'detail_url' in offender:
                    details = self.scrape_offender_details(offender['detail_url'])
                    offender.update(details)
                    
                    # Download detail page image if different
                    if 'detail_image_url' in offender and 'image_url' not in offender:
                        image_path = self.download_image(offender['detail_image_url'], offender.get('offender_id', f'offender_{i}'))
                        if image_path:
                            offender['local_image_path'] = image_path
                
                time.sleep(self.delay)  # Rate limiting
            
            return offenders
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def save_to_csv(self, offenders: List[Dict[str, str]], filename: str = "offenders.csv"):
        """Save offenders data to CSV file"""
        if not offenders:
            logger.warning("No offenders data to save")
            return
        
        filepath = self.data_dir / filename
        
        # Get all unique keys from all offenders
        all_keys = set()
        for offender in offenders:
            all_keys.update(offender.keys())
        
        fieldnames = sorted(list(all_keys))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(offenders)
        
        logger.info(f"Saved {len(offenders)} offenders to {filepath}")
    
    def save_to_json(self, offenders: List[Dict[str, str]], filename: str = "offenders.json"):
        """Save offenders data to JSON file"""
        if not offenders:
            logger.warning("No offenders data to save")
            return
        
        filepath = self.data_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(offenders, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(offenders)} offenders to {filepath}")


def main():
    """Main function to run the scraper"""
    # Your specific search URL
    search_url = "https://www.icrimewatch.net/results.php?AgencyID=55260&SubmitAddrSearch=1&AddrStreet=5+Seminary+Place&AddrCity=New+Brunswick&AddrState=31&AddrZip=08901&AddrZipPlus=08901&whichaddr=home_addr%7Ctemp_addr&excludeIncarcerated=0&radius=5"
    
    # Initialize scraper (set headless=True to run without browser window)
    scraper = FinalSexOffenderScraper(headless=False, delay=3.0)
    
    try:
        # Scrape the data
        offenders = scraper.scrape_all_offenders(search_url)
        
        if offenders:
            # Save to both CSV and JSON
            scraper.save_to_csv(offenders)
            scraper.save_to_json(offenders)
            
            # Print summary
            print(f"\nScraping completed successfully!")
            print(f"Found {len(offenders)} offenders")
            print(f"Images saved to: {scraper.images_dir}")
            print(f"Data saved to: {scraper.data_dir}")
            
            # Show sample data
            if offenders:
                print(f"\nSample offender data:")
                sample = offenders[0]
                for key, value in sample.items():
                    if key not in ['local_image_path', 'detail_image_url', 'image_url']:
                        print(f"  {key}: {value}")
        else:
            print("No offenders found or scraping failed")
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
