#!/usr/bin/env python3
"""Fix date format in Google Sheets - change to D/M/YYYY, H:MM:SS"""

import gspread
from gspread.utils import rowcol_to_a1

# Config
SERVICE_ACCOUNT_PATH = "/Users/ngs/.config/google-sheets-mcp/service-account.json"
SPREADSHEET_ID = "1NXa_R0m4aYEFbd4pLiVS8t8voMlDHfOw5lAtpNtKVSg"
SHEET_NAME = "บันทึกการเข้างาน"

# Connect
gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)

try:
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    print(f"✓ Connected to: {spreadsheet.title}")
    
    worksheet = spreadsheet.worksheet(SHEET_NAME)
    print(f"✓ Found sheet: {SHEET_NAME}")
    
    # Get all values to find data range
    all_values = worksheet.get_all_values()
    num_rows = len(all_values)
    print(f"✓ Total rows: {num_rows}")
    
    # Date format: D/M/YYYY, H:MM:SS (no leading zeros, with seconds)
    date_format = {
        "numberFormat": {
            "type": "DATE_TIME",
            "pattern": "d/M/yyyy, H:mm:ss"
        }
    }
    
    # Apply format to column B (เข้างาน) and C (ออกงาน) - rows 2 to end
    if num_rows > 1:
        # Column B (index 1) and C (index 2)
        range_b = f"B2:B{num_rows}"
        range_c = f"C2:C{num_rows}"
        
        worksheet.format(range_b, date_format)
        print(f"✓ Applied format to column B (เข้างาน): {range_b}")
        
        worksheet.format(range_c, date_format)
        print(f"✓ Applied format to column C (ออกงาน): {range_c}")
        
        print("\n✅ Done! Date format changed to: D/M/YYYY, H:MM:SS")
    else:
        print("No data rows found")
        
except gspread.exceptions.SpreadsheetNotFound:
    print("❌ Spreadsheet not found. Make sure the service account has access.")
    print("   Share the spreadsheet with: ai-agent@gen-lang-client-0656533828.iam.gserviceaccount.com")
except Exception as e:
    print(f"❌ Error: {e}")
