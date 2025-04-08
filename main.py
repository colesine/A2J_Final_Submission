#!/usr/bin/env python3
"""
A2J Legal Case Analysis

Main entry point for the A2J Legal Case Analysis application.
"""

import os
import re
import sys
import time
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

from a2j_legal.scraper import Case, CaseScraper
from a2j_legal.llm_processor import LLMProcessor
from a2j_legal.excel_utils import ExcelManager
from a2j_legal.sheets_integration import SheetsManager
from config import (
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    SPREADSHEET_ID,
    TARGET_SHEET_TITLE,
    CASE_ARCHIVE_FOLDER,
    CLIENT_SECRET_FILE,
    TOKEN_LIMIT
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', f'a2j_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def scrape_cases() -> List[Case]:
    """
    Scrape cases from the e-litigation website.
    
    Returns:
        A list of Case objects
    """
    logger.info("Starting case scraping...")
    scraper = CaseScraper(headless=True, case_archive_folder=CASE_ARCHIVE_FOLDER)
    try:
        cases = scraper.scrape_all()
        logger.info(f"Scraped {len(cases)} cases")
        return cases
    except Exception as e:
        logger.error(f"Error scraping cases: {e}")
        return []
    finally:
        scraper.close()

def process_cases(cases: List[Case]) -> Dict[str, Dict[str, Any]]:
    """
    Process cases with LLMs.
    
    Args:
        cases: List of Case objects
        
    Returns:
        Dictionary of LLM results for each case
    """
    logger.info("Starting case processing with LLMs...")
    processor = LLMProcessor(
        gemini_api_key=GEMINI_API_KEY,
        openai_api_key=OPENAI_API_KEY,
        token_limit=TOKEN_LIMIT
    )
    
    results = {}
    for i, case in enumerate(cases, 1):
        logger.info(f"Processing case {i}/{len(cases)}: {case.title}")
        try:
            result = processor.process_case(case.title, case.details)
            results[case.unique_title] = result
            logger.info(f"Successfully processed {case.title}")
        except Exception as e:
            logger.error(f"Error processing {case.title}: {e}")
        
        # Add a small delay between API calls to avoid rate limits
        if i < len(cases):
            time.sleep(1)
    
    logger.info(f"Processed {len(results)} cases with LLMs")
    return results

def save_to_excel(cases: List[Case], llm_results: Dict[str, Dict[str, Any]]) -> str:
    """
    Save cases and LLM results to Excel.
    
    Args:
        cases: List of Case objects
        llm_results: Dictionary of LLM results for each case
        
    Returns:
        Path to the saved Excel file
    """
    logger.info("Saving results to Excel...")
    excel_manager = ExcelManager(case_archive_folder=CASE_ARCHIVE_FOLDER)
    excel_path = excel_manager.process_and_save_cases(cases, llm_results)
    if excel_path:
        logger.info(f"Results saved to {excel_path}")
    else:
        logger.error("Failed to save results to Excel")
    return excel_path

def export_to_sheets(excel_path: str) -> bool:
    """
    Export Excel file to Google Sheets.
    
    Args:
        excel_path: Path to the Excel file
        
    Returns:
        True if the export was successful, False otherwise
    """
    logger.info("Exporting to Google Sheets...")
    sheets_manager = SheetsManager(
        client_secret_file=CLIENT_SECRET_FILE,
        spreadsheet_id=SPREADSHEET_ID,
        target_sheet_title=TARGET_SHEET_TITLE
    )
    success = sheets_manager.export_excel_to_sheets(excel_path)
    if success:
        logger.info("Successfully exported to Google Sheets")
    else:
        logger.error("Failed to export to Google Sheets")
    return success

def load_cases_from_excel(excel_path: str) -> List[Case]:
    """
    Load cases from an Excel file.
    
    Args:
        excel_path: Path to the Excel file
        
    Returns:
        A list of Case objects
    """
    logger.info(f"Loading cases from {excel_path}...")
    import pandas as pd
    
    try:
        df = pd.read_excel(excel_path)
        cases = []
        for _, row in df.iterrows():
            case = Case(
                title=row['Case Name'],
                unique_title=row['Unique Name'],
                url='',  # URL not available from Excel
                citation=row['Citation'],
                date=row['Date of Judgment'],
                details=''  # Details not available from Excel
            )
            cases.append(case)
        
        logger.info(f"Loaded {len(cases)} cases from Excel")
        return cases
    except Exception as e:
        logger.error(f"Error loading cases from Excel: {e}")
        return []

def main():
    """Main entry point for the application."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='A2J Legal Case Analysis')
    parser.add_argument('--all', action='store_true', help='Run all steps: scrape, process, and export')
    parser.add_argument('--scrape', action='store_true', help='Scrape cases from the e-litigation website')
    parser.add_argument('--process', action='store_true', help='Process cases with LLMs')
    parser.add_argument('--export', action='store_true', help='Export Excel file to Google Sheets')
    parser.add_argument('--excel', type=str, help='Path to an existing Excel file')
    args = parser.parse_args()
    
    # Check if any arguments were provided
    if not (args.all or args.scrape or args.process or args.export):
        parser.print_help()
        sys.exit(1)
    
    # Run all steps
    if args.all:
        cases = scrape_cases()
        if cases:
            llm_results = process_cases(cases)
            excel_path = save_to_excel(cases, llm_results)
            if excel_path:
                export_to_sheets(excel_path)
        return
    
    # Run individual steps
    if args.scrape:
        cases = scrape_cases()
        if cases:
            llm_results = process_cases(cases)
            save_to_excel(cases, llm_results)
        return
    
    if args.process:
        if not args.excel:
            logger.error("--excel argument is required for --process")
            sys.exit(1)
        
        cases = load_cases_from_excel(args.excel)
        if cases:
            llm_results = process_cases(cases)
            save_to_excel(cases, llm_results)
        return
    
    if args.export:
        if not args.excel:
            logger.error("--excel argument is required for --export")
            sys.exit(1)
        
        export_to_sheets(args.excel)
        return

if __name__ == '__main__':
    main()
