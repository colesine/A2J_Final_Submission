import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Google Sheets
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
TARGET_SHEET_TITLE = "Case Data"

# File paths
CASE_ARCHIVE_FOLDER = "case_archive"
CLIENT_SECRET_FILE = "client_secret.json"

# LLM configuration
TOKEN_LIMIT = 2_000_000
