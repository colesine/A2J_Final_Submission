#!/usr/bin/env python3
"""
Google OAuth Authentication Setup

This script helps set up OAuth authentication for Google Sheets.
Run this script locally to generate a token.pickle file, then upload
the token.pickle file to PythonAnywhere.
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Path to your client secrets file
CLIENT_SECRET_FILE = 'client_secret.json'
# Scopes required for Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# Path to save the credentials
TOKEN_PATH = 'token.pickle'

def main():
    """Run the OAuth flow and save the credentials."""
    # Check if client secret file exists
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"Error: {CLIENT_SECRET_FILE} not found.")
        print("Please download your OAuth client secrets file from the Google Cloud Console")
        print("and save it as 'client_secret.json' in the same directory as this script.")
        return
    
    # Run the OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE, SCOPES)
    
    # Run the local server flow
    print("Opening browser for OAuth authentication...")
    creds = flow.run_local_server(port=8080)
    
    # Save the credentials for later use
    with open(TOKEN_PATH, 'wb') as token:
        pickle.dump(creds, token)
    
    print(f"Credentials saved to {TOKEN_PATH}")
    print("\nInstructions:")
    print("1. Upload this token.pickle file to your PythonAnywhere project directory")
    print("2. Make sure the sheets_integration.py file is updated to use the token")
    print("3. Your application should now be able to access Google Sheets without browser authentication")

if __name__ == '__main__':
    main()
