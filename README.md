# A2J Legal Case Analysis

An automated system for scraping, analyzing, and extracting key information from legal cases using LLMs (Gemini and OpenAI).

## Overview

This project automates the process of:
1. Scraping legal cases from the e-litigation website
2. Processing case texts with LLMs (Gemini and OpenAI)
3. Extracting structured data about matrimonial assets division and family law
4. Exporting results to Excel and Google Sheets

## Quick Start

### Local Installation

1. Clone the repository
2. Set up a virtual environment and install dependencies:
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   python -m pip install -r requirements.txt
   ```
   
   Alternatively, use the provided setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Configure your environment:
   - Create a `.env` file with your API keys:
     ```
     GEMINI_API_KEY=your_gemini_api_key
     OPENAI_API_KEY=your_openai_api_key
     SPREADSHEET_ID=your_google_spreadsheet_id
     ```
   - Place your Google API client secrets file in the project directory as `client_secret.json`
   - Run the auth setup script to generate OAuth tokens:
     ```bash
     python auth_setup.py
     ```

### Running the Application

The application provides several command-line options:

```bash
# Run all steps: scrape cases, process with LLMs, and export to Google Sheets
python main.py --all

# Only scrape cases and process them (without exporting to Google Sheets)
python main.py --scrape

# Process existing cases from an Excel file
python main.py --process --excel path/to/existing/excel.xlsx

# Export an existing Excel file to Google Sheets
python main.py --export --excel path/to/existing/excel.xlsx
```

## PythonAnywhere Deployment Guide

### 1. Prepare Your Local Environment

Before deploying to PythonAnywhere, prepare the following locally:

1. Generate the OAuth token for Google Sheets:
   ```bash
   python auth_setup.py
   ```
   This will create a `token.pickle` file that you'll need to upload to PythonAnywhere.

2. Ensure your `client_secret.json` file is ready for upload.

### 2. Set Up on PythonAnywhere

1. **Create a PythonAnywhere Account**:
   - Sign up at [https://www.pythonanywhere.com/](https://www.pythonanywhere.com/)

2. **Upload Your Code**:
   - Option A: Using Git (if your code is in a repository)
     ```bash
     git clone https://github.com/yourusername/your-repo-name.git
     ```
   - Option B: Upload a ZIP file through the Files tab
     - Create a ZIP file of your project locally
     - Upload it to PythonAnywhere via the Files tab
     - Unzip it using the command: `unzip your-project.zip`

3. **Set Up a Virtual Environment**:
   ```bash
   cd your-project-directory
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Upload Configuration Files**:
   - Upload your `client_secret.json` file
   - Upload the `token.pickle` file generated locally
   - Create a `.env` file with your API keys:
     ```
     GEMINI_API_KEY=your_gemini_api_key
     OPENAI_API_KEY=your_openai_api_key
     SPREADSHEET_ID=your_google_spreadsheet_id
     ```

5. **Configure Selenium for PythonAnywhere**:
   - The application is already configured to detect PythonAnywhere environment
   - PythonAnywhere provides a Selenium server at `http://localhost:4444/wd/hub`
   - Ensure your PythonAnywhere account has Selenium enabled (available in paid accounts)
   - If using a free account, you can still use the `--process` and `--export` options with pre-scraped data

6. **Create Required Directories**:
   ```bash
   mkdir -p logs case_archive
   ```

7. **Set Up a Scheduled Task** (Optional):
   - Go to the "Tasks" tab
   - Add a new scheduled task with the command:
     ```bash
     cd /home/yourusername/your-project-directory && /home/yourusername/your-project-directory/venv/bin/python main.py --all
     ```

### 3. Running on PythonAnywhere

You can run the application manually from a Bash console:

```bash
cd your-project-directory
source venv/bin/activate
python main.py --all
```

For free accounts or if you want to avoid Selenium:
```bash
# Process existing Excel file and export to Google Sheets
python main.py --process --excel case_archive/your_excel_file.xlsx --export
```

### 4. Troubleshooting PythonAnywhere Deployment

1. **Selenium Issues**:
   - Selenium is only available on paid PythonAnywhere accounts
   - For free accounts, use the `--process` and `--export` options with pre-scraped data
   - If you have a paid account but encounter Selenium errors, check PythonAnywhere's Selenium server status

2. **Memory Limits**:
   - Free accounts have memory limits; process smaller batches of cases
   - Use the `--process` option with specific Excel files to handle subsets of data

3. **File Permissions**:
   - Ensure your script has permissions to read/write in your directory
   - Check file paths are correct for PythonAnywhere's environment

4. **API Rate Limits**:
   - Add delays between API calls if you hit rate limits
   - The code already includes retry mechanisms for API calls

5. **Token Expiration**:
   - If Google Sheets integration stops working, your OAuth token may have expired
   - Generate a new token locally and upload it to PythonAnywhere

## Project Structure

- `a2j_legal/`: Main package with modular components
  - `scraper.py`: Case scraping functions
  - `llm_processor.py`: LLM integration for text analysis
  - `excel_utils.py`: Excel file operations
  - `sheets_integration.py`: Google Sheets integration
- `main.py`: Command line interface and entry point
- `config.py`: Configuration settings
- `auth_setup.py`: Script to set up Google OAuth authentication
- `setup.sh`: Setup script for local environment
- `requirements.txt`: Project dependencies
- `case_archive/`: Directory for storing Excel output files
- `logs/`: Directory for log files

## License

Copyright (c) 2023-2025. All rights reserved.
