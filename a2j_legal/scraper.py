"""
Case Scraper Module

This module handles the scraping of legal cases from the e-litigation website.
"""

import os
import re
import math
import time
import logging
import shutil
import platform
import subprocess
from datetime import datetime
from typing import List, Set, Optional, Dict, Any

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# Configure logging
logger = logging.getLogger(__name__)

class Case:
    """Class representing a legal case with its metadata and content."""
    
    def __init__(self, title: str, unique_title: str, url: str, citation: str, date: str, details: Optional[str] = None):
        """
        Initialize a Case object.
        
        Args:
            title: The title of the case
            unique_title: A unique identifier for the case
            url: The URL where the case can be accessed
            citation: The legal citation for the case
            date: The date of the case judgment
            details: The full text of the case judgment (optional)
        """
        self.title = title
        self.unique_title = unique_title
        self.url = url
        self.citation = citation
        self.date = date
        self.details = details

    def __repr__(self) -> str:
        """Return a string representation of the Case object."""
        return f"Case(title={self.title}, url={self.url}, citation={self.citation})"


class CaseScraper:
    """Class for scraping legal cases from the e-litigation website."""
    
    def __init__(self, headless: bool = True, case_archive_folder: str = "case_archive"):
        """
        Initialize the CaseScraper.
        
        Args:
            headless: Whether to run the browser in headless mode
            case_archive_folder: The folder where case archives are stored
        """
        self.case_archive_folder = case_archive_folder
        self.driver = self._setup_driver(headless)
        
        # Create case archive folder if it doesn't exist
        os.makedirs(self.case_archive_folder, exist_ok=True)
        
    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """
        Set up and return a Chrome WebDriver compatible with PythonAnywhere.
        
        Args:
            headless: Whether to run the browser in headless mode
            
        Returns:
            A configured Chrome WebDriver
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Add additional options for PythonAnywhere compatibility
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Check if running on PythonAnywhere
        if 'PYTHONANYWHERE_DOMAIN' in os.environ:
            logger.info("Running on PythonAnywhere, using Remote WebDriver")
            # Use the PythonAnywhere Selenium server
            return webdriver.Remote(
                command_executor='http://localhost:4444/wd/hub',
                options=chrome_options
            )
        else:
            # Use local ChromeDriver
            logger.info("Running locally, using ChromeDriver")
            
            # Check if running on macOS with Apple Silicon
            is_mac = platform.system() == 'Darwin'
            is_arm = platform.machine() == 'arm64'
            
            # Clear the webdriver-manager cache to avoid using corrupted drivers
            wdm_cache_dir = os.path.expanduser('~/.wdm/drivers/chromedriver')
            if os.path.exists(wdm_cache_dir):
                logger.info(f"Clearing WebDriver Manager cache: {wdm_cache_dir}")
                try:
                    shutil.rmtree(wdm_cache_dir)
                except Exception as e:
                    logger.warning(f"Failed to clear cache: {e}")
            
            if is_mac and is_arm:
                logger.info("Detected macOS with Apple Silicon (ARM64)")
                try:
                    # For Apple Silicon Macs, we'll use a more direct approach
                    # First, try to manually download a compatible ChromeDriver
                    import urllib.request
                    import zipfile
                    import tempfile
                    
                    # Create a temporary directory for the ChromeDriver
                    temp_dir = tempfile.mkdtemp()
                    logger.info(f"Created temporary directory: {temp_dir}")
                    
                    # URL for the latest ChromeDriver for Mac ARM64
                    chromedriver_url = "https://storage.googleapis.com/chrome-for-testing-public/135.0.7049.42/mac-arm64/chromedriver-mac-arm64.zip"
                    zip_path = os.path.join(temp_dir, "chromedriver.zip")
                    
                    # Download the ChromeDriver zip file
                    logger.info(f"Downloading ChromeDriver from: {chromedriver_url}")
                    urllib.request.urlretrieve(chromedriver_url, zip_path)
                    
                    # Extract the zip file
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Find the chromedriver executable
                    chromedriver_path = None
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file == "chromedriver":
                                chromedriver_path = os.path.join(root, file)
                                break
                    
                    if not chromedriver_path:
                        raise FileNotFoundError("ChromeDriver executable not found in the downloaded zip")
                    
                    # Make the ChromeDriver executable
                    os.chmod(chromedriver_path, 0o755)
                    logger.info(f"Using ChromeDriver at: {chromedriver_path}")
                    
                    service = Service(executable_path=chromedriver_path)
                    return webdriver.Chrome(service=service, options=chrome_options)
                except Exception as e:
                    logger.error(f"Error setting up ChromeDriver for ARM64: {e}")
                    logger.info("Falling back to standard ChromeDriverManager")
                    try:
                        # Try standard ChromeDriverManager as a fallback
                        driver_path = ChromeDriverManager().install()
                        logger.info(f"Using ChromeDriver at: {driver_path}")
                        
                        service = Service(executable_path=driver_path)
                        return webdriver.Chrome(service=service, options=chrome_options)
                    except Exception as e2:
                        logger.error(f"Fallback ChromeDriverManager failed: {e2}")
                        raise
            else:
                # Standard approach for other platforms
                try:
                    driver_path = ChromeDriverManager().install()
                    logger.info(f"Using ChromeDriver at: {driver_path}")
                    
                    service = Service(executable_path=driver_path)
                    return webdriver.Chrome(service=service, options=chrome_options)
                except Exception as e:
                    logger.error(f"Error setting up ChromeDriver: {e}")
                    raise
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
    
    def get_total_pages(self, driver: webdriver.Chrome, cases_per_page: int = 10, timeout: int = 10) -> int:
        """
        Wait for the summary element and extract total number of pages.
        
        Args:
            driver: The WebDriver to use
            cases_per_page: Number of cases displayed per page
            timeout: Maximum time to wait for the element
            
        Returns:
            The total number of pages
        """
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#listview > div.row.justify-content-between.align-items-center > div.gd-csummary")
                )
            )
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            summary_div = soup.select_one("#listview > div.row.justify-content-between.align-items-center > div.gd-csummary")

            if summary_div:
                match = re.search(r"Total Judgment\(s\) Found\s*:\s*(\d+)", summary_div.text)
                if match:
                    total_cases = int(match.group(1))
                    total_pages = math.ceil(total_cases / cases_per_page)
                    logger.info(f"Found {total_cases} cases => {total_pages} page(s).")
                    return total_pages
                else:
                    logger.warning(f"Pattern not matched in summary_div.text: {summary_div.text}")
            else:
                logger.warning("Summary div not found in parsed soup.")

        except TimeoutException:
            logger.warning("Timed out waiting for summary div to load.")

        return 0
    
    def find_latest_excel_file(self) -> Optional[str]:
        """
        Find the most recent Excel file with the format DD_MM_YYYY.xlsx in the case_archive folder.
        
        Returns:
            The path to the latest Excel file, or None if no file is found
        """
        excel_files = []
        file_pattern = re.compile(r'^\d{2}_\d{2}_\d{4}\.xlsx$')
        
        # Check case_archive folder
        if not os.path.exists(self.case_archive_folder):
            logger.info("Archive folder doesn't exist yet. No previous Excel files found.")
            return None
        
        # Get all Excel files matching the pattern from the archive folder
        for file in os.listdir(self.case_archive_folder):
            if file_pattern.match(file):
                file_path = os.path.join(self.case_archive_folder, file)
                excel_files.append((file_path, os.path.getmtime(file_path)))
        
        if not excel_files:
            return None
        
        # Sort files by modification time (newest first)
        excel_files.sort(key=lambda x: x[1], reverse=True)
        return excel_files[0][0]
    
    def load_existing_cases(self, excel_path: str) -> List[str]:
        """
        Load existing case names from Excel file.
        
        Args:
            excel_path: Path to the Excel file
            
        Returns:
            A list of unique case names
        """
        try:
            df = pd.read_excel(excel_path)
            if 'Unique Name' in df.columns:
                # Create a list of existing unique case names
                return [name.strip() for name in df['Unique Name'].dropna().astype(str)]
            else:
                logger.warning(f"Warning: 'Unique Name' column not found in {excel_path}")
                return list()
        except Exception as e:
            logger.error(f"Error reading Excel file {excel_path}: {e}")
            return list()
    
    def extract_cases(self, driver: webdriver.Chrome, first_pass_cases: Optional[List[Case]] = None) -> List[Case]:
        """
        Extract case titles, URLs, citations, and dates from the current page.
        Terminates extraction if the case is already in the latest Excel file or if date is 2015 or earlier.
        Skips cases already found in first_pass_cases.
        
        Args:
            driver: The WebDriver to use
            first_pass_cases: Cases already found in a previous search
            
        Returns:
            A list of Case objects
        """
        # Find the latest Excel file in the current directory
        existing_cases = set()
        try:
            latest_excel = self.find_latest_excel_file()
            if latest_excel:
                logger.info(f"Found latest Excel file: {latest_excel}")
                existing_cases = set(self.load_existing_cases(latest_excel))
                logger.info(f"Loaded {len(existing_cases)} existing case names")
        except Exception as e:
            logger.error(f"Error loading existing cases: {e}")
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Extract all necessary elements
        cases_elements = driver.find_elements(By.CSS_SELECTOR, 'a.h5.gd-heardertext')
        citation_spans = soup.select('a.citation-num-link span.gd-addinfo-text')
        date_spans = soup.select('a.decision-date-link span.gd-addinfo-text')
        
        full_cases = []
        found_existing = False  # Flag to track if we found an existing case
        
        for i, case_elem in enumerate(cases_elements):
            # Extract citation and date
            citation = citation_spans[i].text.rstrip('|').strip() if i < len(citation_spans) else None
            raw_date = date_spans[i].text if i < len(date_spans) else ""
            date = raw_date.replace("Decision Date:", "").replace("|", "").strip()
            
            # Create unique title (for comparing against existing cases)
            title = case_elem.text.strip()
            clean_citation = re.sub(r'\[\d{4}\]\s*', '', citation) if citation else ''
            unique_title = f"{title} {clean_citation}"
            
            # Check if the date is 2015 or earlier
            if date and date[-4:].isdigit() and int(date[-4:]) <= 2015:
                logger.info(f"Stopping extraction as case date is {date} (2015 or earlier).")
                found_existing = True
                break
            
            # Check if case already exists in Excel file
            if existing_cases and (unique_title in existing_cases):
                logger.info(f"Stopping extraction as case '{unique_title}' already exists in Excel.")
                found_existing = True
                break

            if first_pass_cases and unique_title in [case.unique_title for case in first_pass_cases]:
                logger.info(f"Skipping duplicate case: '{unique_title}' (already found in first search)")
                continue  # Skip to the next case in the loop
            
            # Create a Case object
            full_cases.append(
                Case(
                    title=title,
                    unique_title=unique_title,
                    url=case_elem.get_attribute("href"),
                    citation=citation,
                    date=date
                )
            )
        
        # Return empty list if we found an existing case to signal termination
        if found_existing and not full_cases:
            return []
            
        return full_cases
    
    def process_cases(self, driver: webdriver.Chrome, cases: List[Case]) -> int:
        """
        Process cases by fetching their details.
        
        Args:
            driver: The WebDriver to use
            cases: List of Case objects to process
            
        Returns:
            Number of cases processed
        """
        cases_processed = 0
        for case in cases:
            try:
                logger.info(f"Processing: {case.title}")
                logger.info(f"Opening URL: {case.url}")
                driver.execute_script("window.open(arguments[0]);", case.url)
                driver.switch_to.window(driver.window_handles[1])
                time.sleep(1)

                soup = BeautifulSoup(driver.page_source, "html.parser")
                content_div = soup.find("div", id="divJudgement")
                if content_div:
                    case.details = content_div.get_text(separator="\n", strip=True)
                else:
                    judgement_div = driver.find_element(By.XPATH, '//*[@id="divJudgement"]')
                    case.details = judgement_div.text.strip()
                    
                logger.info(f"Date: {case.date}. Extracted {len(case.details)} characters from {case.title}")
                cases_processed += 1
            except Exception as e:
                case.details = f"Error processing case: {e}"
                logger.error(f"Error processing {case.title}: {e}")
            finally:
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
        logger.info(f"Number of cases processed on this page: {cases_processed}")
        return cases_processed
    
    def scrape_search(self, base_url: str, first_pass: Optional[List[Case]] = None) -> List[Case]:
        """
        Iterate through pages for a given search URL until a case from 2015 or earlier is found
        or until a case already in the Excel file is found.
        
        Args:
            base_url: The base URL for the search
            first_pass: Cases already found in a previous search
            
        Returns:
            A list of Case objects
        """
        self.driver.get(base_url)
        self.driver.implicitly_wait(2)
        total_pages = self.get_total_pages(self.driver)
        cases_all = []
        
        for page in range(1, total_pages + 1):
            # Replace the page number in the URL dynamically.
            page_url = re.sub(r"CurrentPage=\d+", f"CurrentPage={page}", base_url)
            self.driver.get(page_url)
            self.driver.implicitly_wait(2)

            cases = self.extract_cases(self.driver, first_pass)
            if not cases:
                logger.info(f"No new cases found on page {page} or termination condition met. Stopping search.")
                break

            self.process_cases(self.driver, cases)
            cases_all.extend(cases)
            logger.info(f"Page {page} processed. Cumulative cases: {len(cases_all)}")

        return cases_all
    
    def scrape_all(self) -> List[Case]:
        """
        Scrape cases from multiple search URLs.
        
        Returns:
            A list of unique Case objects
        """
        # First search URL.
        initial_url = "https://www.elitigation.sg/gd/Home/Index?Filter=SUPCT&YearOfDecision=All&SortBy=DateOfDecision&SearchPhrase=%22Family%20Law%20-%20Matrimonial%20Assets%20-%20Division%22%20OR%20%22Family%20Law%20-%20Custody%22&CurrentPage=1&SortAscending=False&PageSize=0&Verbose=False&SearchQueryTime=0&SearchTotalHits=0&SearchMode=False&SpanMultiplePages=False"
        cases_search1 = self.scrape_search(initial_url)

        # Second search URL.
        url_2 = "https://www.elitigation.sg/gd/Home/Index?Filter=SUPCT&YearOfDecision=All&SortBy=DateOfDecision&SearchPhrase=%22division%20of%20matrimonial%20assets%22%20OR%20%22Matrimonial%20assets%20-%20Matrimonial%20home%22&CurrentPage=1&SortAscending=False&PageSize=0&Verbose=False&SearchQueryTime=0&SearchTotalHits=0&SearchMode=False&SpanMultiplePages=False"
        cases_search2 = self.scrape_search(url_2, first_pass=cases_search1)

        # Combine both lists of cases.
        unique_cases = cases_search1 + cases_search2
        logger.info(f"Total unique cases extracted: {len(unique_cases)}")
        
        return unique_cases
