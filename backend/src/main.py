# main.py
# This script will monitor a Google Sheet for new rows, process the data,
# and then print a cover sheet and a receipt.

import os.path
import time
import threading
import io
import shutil
import tempfile

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import configparser
import logging
import subprocess
import argparse
import win32print
import win32api

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]

# Get project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Set up command line argument parsing
parser = argparse.ArgumentParser(description='Monitor Google Sheet for print jobs.')
parser.add_argument('--start-row', type=int, help='Starting row number for first time launch (optional)', default=None)
parser.add_argument('--run-once', action='store_true', help='Process available jobs once and exit instead of continuous monitoring')

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config_path = os.path.join(PROJECT_ROOT, 'config', 'config.ini')
if not os.path.exists(config_path):
    logging.error("config.ini not found. Please copy config.ini.example to config.ini and fill in your details.")
    exit()
config.read(config_path)

def create_temp_copy_for_printing(file_path, job_id=None):
    """
    Creates a temporary copy of a file with just the job ID + extension as filename.
    This helps Adobe Acrobat/Reader use a clean filename in print job names instead of full paths.
    
    Args:
        file_path: Full path to the source file
        job_id: Optional job ID to use as filename (defaults to original filename)
        
    Returns:
        str: Path to temporary file, or original path if no job_id provided
    """
    if not job_id:
        return file_path
        
    try:
        # Get the file extension
        _, extension = os.path.splitext(file_path)
        
        # Create downloads directory if it doesn't exist
        downloads_dir = os.path.join(PROJECT_ROOT, "downloads")
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
        
        # Create a print jobs directory for cleaner organization
        print_jobs_dir = os.path.join(downloads_dir, "print_jobs")
        if not os.path.exists(print_jobs_dir):
            os.makedirs(print_jobs_dir)
        
        # Create the new filename with just job_id + extension - no temp subdirectory
        # This makes the path shorter and cleaner for print job names
        temp_filename = f"JOB_{job_id}{extension}"
        temp_file_path = os.path.join(print_jobs_dir, temp_filename)
        
        # Copy the file
        shutil.copy2(file_path, temp_file_path)
        
        logging.info(f"Created temporary copy for printing: {temp_filename}")
        return temp_file_path
        
    except Exception as e:
        logging.warning(f"Failed to create temporary copy, using original file: {e}")
        return file_path

def find_adobe_executable():
    """
    Find Adobe Acrobat or Adobe Reader executable on the system.

    Returns:
        str: Path to Adobe executable, or None if not found
    """
    # Common paths for Adobe Acrobat and Reader
    possible_paths = [
        r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
        r"C:\Program Files\Adobe\Acrobat 2020\Acrobat\Acrobat.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat 2020\Acrobat\Acrobat.exe",
        r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        r"C:\Program Files\Adobe\Acrobat Reader 2020\Reader\AcroRd32.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat Reader 2020\Reader\AcroRd32.exe"
    ]

    for path in possible_paths:
        if os.path.exists(path):
            logging.info(f"Found Adobe executable: {path}")
            return path

    logging.warning("Adobe Acrobat or Reader not found in standard locations")
    return None

def detect_pdf_page_size(pdf_path):
    """Detect PDF page size from the first page.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: Dictionary with width, height, and formatted_size
              None if detection fails or file is not a PDF
    """
    try:
        # Check if file exists and is likely a PDF
        if not os.path.exists(pdf_path):
            logging.warning(f"File not found for page size detection: {pdf_path}")
            return None
            
        # Check file extension
        file_extension = os.path.splitext(pdf_path)[1].lower()
        if file_extension != '.pdf':
            logging.debug(f"Skipping page size detection for non-PDF file: {pdf_path}")
            return None
        
        # Try to import PyPDF2 for PDF analysis
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            logging.warning("PyPDF2 not available for page size detection")
            return None
        
        # Read the PDF and get first page dimensions
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            if len(pdf_reader.pages) > 0:
                page = pdf_reader.pages[0]
                # Get page dimensions - convert Decimal to float for arithmetic operations
                width_points = float(page.mediabox.width)
                height_points = float(page.mediabox.height)
                
                # Convert points to inches (72 points per inch)
                width_inches = width_points / 72.0
                height_inches = height_points / 72.0
                
                # Standard page sizes mapping (width, height) in points
                page_sizes = {
                    (612, 792): "Letter (8.5\" x 11\")",
                    (792, 612): "Letter Landscape (11\" x 8.5\")",
                    (612, 1008): "Legal (8.5\" x 14\")",
                    (1008, 612): "Legal Landscape (14\" x 8.5\")",
                    (595, 842): "A4 (8.27\" x 11.69\")",
                    (842, 595): "A4 Landscape (11.69\" x 8.27\")",
                    (842, 1191): "A3 (11.69\" x 16.54\")",
                    (1191, 842): "A3 Landscape (16.54\" x 11.69\")",
                    (720, 1008): "Tabloid (10\" x 14\")",
                    (1008, 720): "Tabloid Landscape (14\" x 10\")"
                }
                
                # Try to match known page size (with some tolerance)
                dimensions_key = (round(width_points), round(height_points))
                if dimensions_key in page_sizes:
                    formatted_size = page_sizes[dimensions_key]
                else:
                    # Custom size - format as inches
                    formatted_size = f"Custom ({width_inches:.2f}\" x {height_inches:.2f}\")"
                
                logging.info(f"Detected PDF page size: {formatted_size}")
                return {
                    'width_points': width_points,
                    'height_points': height_points,
                    'width_inches': width_inches,
                    'height_inches': height_inches,
                    'formatted_size': formatted_size
                }
            else:
                logging.warning(f"PDF {pdf_path} has no pages")
                return None
                
    except Exception as e:
        logging.warning(f"Failed to detect PDF page size for {pdf_path}: {e}")
        return None

def detect_pdf_page_count(pdf_path):
    """Detect the number of pages in a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        int: Number of pages in the PDF, or None if detection fails or file is not a PDF
    """
    try:
        # Check if file exists and is likely a PDF
        if not os.path.exists(pdf_path):
            logging.warning(f"File not found for page count detection: {pdf_path}")
            return None
            
        # Check file extension
        file_extension = os.path.splitext(pdf_path)[1].lower()
        if file_extension != '.pdf':
            logging.debug(f"Skipping page count detection for non-PDF file: {pdf_path}")
            return None
        
        # Try to import PyPDF2 for PDF analysis
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            logging.warning("PyPDF2 not available for page count detection")
            return None
        
        # Read the PDF and get page count
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            page_count = len(pdf_reader.pages)
            
            if page_count > 0:
                logging.info(f"Detected PDF page count: {page_count} pages")
                return page_count
            else:
                logging.warning(f"PDF {pdf_path} has no pages")
                return None
                
    except Exception as e:
        logging.warning(f"Failed to detect PDF page count for {pdf_path}: {e}")
        return None

def print_document(file_path, printer_name, is_pdf=False, job_id=None, 
                   quantity=None, paper_size=None, duplex=None, staple=None, hole_punch=None):
    """Prints a document to a specified printer on Windows with print options.
    
    Args:
        file_path (str): Path to the file to print
        printer_name (str): Name of the printer
        is_pdf (bool): Whether the file is a PDF/document file for Adobe processing
        job_id (str, optional): Job ID for footer text
        quantity (str/int, optional): Number of copies to print
        paper_size (str, optional): Paper size setting
        duplex (str, optional): Duplex/two-sided setting
        staple (str, optional): Staple setting
        hole_punch (str, optional): Hole punch setting
    """
    temp_file_path = None
    try:
        if not os.path.exists(file_path):
            logging.error(f"Cannot print file, it does not exist: {file_path}")
            return False

        abs_file_path = os.path.abspath(file_path)
        
        # Import printer utilities
        from printer_utils import print_pdf_document, print_text_document
        from thermal_printer import ThermalPrinter
        
        if is_pdf:
            # For PDFs and documents, create a temporary copy with clean filename
            # to prevent Adobe from using full paths in print job names
            temp_file_path = create_temp_copy_for_printing(abs_file_path, job_id)

            logging.info(f"Printing document: {os.path.basename(temp_file_path)} to {printer_name}")
            adobe_path = find_adobe_executable()

            if not adobe_path:
                logging.error("Adobe Acrobat/Reader not found in any of the expected locations")
                return False

            # Detect PDF orientation if not already provided
            orientation = None
            try:
                from printer_utils import detect_pdf_orientation
                orientation = detect_pdf_orientation(temp_file_path)
                logging.info(f"Detected PDF orientation: {orientation}")
            except Exception as e:
                logging.warning(f"Could not detect PDF orientation: {e}")

            # Use the PDF printing utility with the temporary file and print options
            print_pdf_document(
                temp_file_path, printer_name, adobe_path, 
                job_id=job_id, add_footer=ENABLE_FOOTER,
                quantity=quantity, paper_size=paper_size, duplex=duplex, 
                staple=staple, hole_punch=hole_punch, orientation=orientation
            )
            logging.info("Document printing completed successfully")
        else:
            # For text files, use original path (no need for temp copy)
            logging.info(f"Printing text file: {abs_file_path} to {printer_name}")
            
            if "CT-S310" in printer_name:
                # Use thermal printer for receipts
                printer = ThermalPrinter(printer_name)
                try:
                    # Try UTF-8 first
                    with open(abs_file_path, 'r', encoding='ascii', errors='replace') as f:
                        content = f.read()
                    if printer.print_receipt(content):
                        logging.info("Receipt printed successfully")
                    else:
                        logging.error("Failed to print receipt")
                        return False
                except UnicodeError:
                    logging.error("Failed to read receipt file with ASCII encoding")
                    return False
            else:
                # For regular text files
                print_text_document(abs_file_path, printer_name, is_receipt=False)
                logging.info("Text printing completed successfully")
        
        return True

    except FileNotFoundError:
        logging.error(f"Error: File or printing command not found. File: {file_path}")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Error printing {file_path} to {printer_name}: {e}")
        return False
    except subprocess.TimeoutExpired:
        logging.error(f"Printing command timed out for file: {file_path}")
        return False
    except Exception as e:
        logging.error(f"Error printing {file_path} to {printer_name}: {e}")
        return False
        
    finally:
        # Clean up temporary file if created (with delay for Adobe processing)
        if temp_file_path and temp_file_path != file_path:
            try:
                # Add delay to allow Adobe Acrobat time to process the file
                cleanup_delay = 5  # seconds - configurable delay for Adobe processing
                logging.info(f"Waiting {cleanup_delay} seconds before cleanup to allow Adobe processing...")
                time.sleep(cleanup_delay)
                
                # Clean up the temporary file and directory
                temp_dir = os.path.dirname(temp_file_path)
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                logging.info(f"Cleaned up temporary printing files after {cleanup_delay}s delay")
            except Exception as e:
                logging.warning(f"Failed to clean up temporary file: {e}")

# Google Sheet settings
SPREADSHEET_ID = config.get('Google', 'spreadsheet_id')
SHEET_NAME = config.get('Google', 'sheet_name')
RANGE_NAME = f"{SHEET_NAME}!A:Z"

# Printing settings
PDF_PRINTER_NAME = config.get('Printing', 'pdf_printer')
RECEIPT_PRINTER_NAME = config.get('Printing', 'receipt_printer')
# Bypass settings
BYPASS_RECEIPT_PRINTER = config.getboolean('Printing', 'bypass_receipt_printer', fallback=False)
BYPASS_PDF_PRINTER = config.getboolean('Printing', 'bypass_pdf_printer', fallback=False)

# Footer settings
ENABLE_FOOTER = config.getboolean('Footer', 'enable_footer', fallback=True)
FOOTER_FONT_SIZE = config.getint('Footer', 'footer_font_size', fallback=6)
FOOTER_FONT_FAMILY = config.get('Footer', 'footer_font_family', fallback='Times-Roman')

# Script settings
POLL_INTERVAL = config.getint('Script', 'poll_interval', fallback=10)
CLEANUP_AFTER_PROCESSING = config.getboolean('Script', 'cleanup_after_processing', fallback=True)
CLEANUP_DELAY_MINUTES = config.getint('Script', 'cleanup_delay_minutes', fallback=10)

# Column mapping
try:
    COLUMN_MAP = {
        'google_drive_link': config.getint('Columns', 'google_drive_link'),
        'quantity': config.getint('Columns', 'quantity'),
        'two_sided': config.getint('Columns', 'two_sided'),
        'paper_size': config.getint('Columns', 'paper_size'),
        'staples': config.getint('Columns', 'staples'),
        'hole_punch': config.getint('Columns', 'hole_punch'),
        'date_submitted': config.getint('Columns', 'date_submitted'),
        'job_deadline': config.getint('Columns', 'job_deadline'),
        'processed': config.getint('Columns', 'processed'),
        'acknowledged': config.getint('Columns', 'acknowledged', fallback=12),
        'completed': config.getint('Columns', 'completed', fallback=13),
        'error_log': config.getint('Columns', 'error_log', fallback=21),
    }
    # The minimum number of columns a row must have to be processed
    # Only consider essential columns for processing, not optional ones like error_log, acknowledged, completed
    essential_columns = {k: v for k, v in COLUMN_MAP.items() if k not in ['error_log', 'acknowledged', 'completed']}
    MIN_COLUMNS = max(essential_columns.values()) + 1
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    logging.error(f"Configuration error in [Columns] section: {e}")
    logging.error("Please ensure config.ini has a [Columns] section with all required fields.")
    exit()

def get_sheet_id(sheets_service, spreadsheet_id, sheet_name):
    """Get the sheet ID for a given sheet name.
    
    Args:
        sheets_service: Google Sheets API service object
        spreadsheet_id: The ID of the spreadsheet
        sheet_name: The name of the sheet to find
        
    Returns:
        int: The sheet ID, or None if not found
    """
    try:
        # Get spreadsheet metadata
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        # Find the sheet with the matching name
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        logging.error(f"Sheet '{sheet_name}' not found in spreadsheet")
        return None
        
    except Exception as e:
        logging.error(f"Error getting sheet ID: {e}")
        return None

def get_google_creds():
    """Shows basic usage of the Sheets API.
    Prints the names and majors of students in a sample spreadsheet.
    """
    creds = None
    # Get paths relative to project root
    token_path = os.path.join(PROJECT_ROOT, "token.json")
    credentials_path = os.path.join(PROJECT_ROOT, "credentials.json")
    
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return creds

def mark_row_as_processed(sheets_service, row_number):
    """Mark a specific row as processed in the Google Sheet using a checkbox.
    
    Args:
        sheets_service: Google Sheets API service object
        row_number: 1-based row number to mark as processed
    """
    try:
        # Convert to 1-based row number for Google Sheets API
        sheet_row = row_number + 1
        
        # Get the column index for the processed column (0-based)
        processed_col_index = COLUMN_MAP['processed']
        
        # Get the actual sheet ID dynamically
        sheet_id = get_sheet_id(sheets_service, SPREADSHEET_ID, SHEET_NAME)
        if sheet_id is None:
            logging.error(f"Could not find sheet '{SHEET_NAME}' in spreadsheet")
            return False
        
        # Create batch update request to format cell as checkbox and set to TRUE
        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": sheet_row - 1,  # 0-based for API
                        "endRowIndex": sheet_row,
                        "startColumnIndex": processed_col_index,
                        "endColumnIndex": processed_col_index + 1
                    },
                    "cell": {
                        "dataValidation": {
                            "condition": {
                                "type": "BOOLEAN"
                            }
                        },
                        "userEnteredValue": {
                            "boolValue": True
                        }
                    },
                    "fields": "dataValidation,userEnteredValue"
                }
            }
        ]
        
        # Execute the batch update
        body = {
            'requests': requests
        }
        
        result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        
        # Verify the update was successful by reading the cell value
        time.sleep(1)  # Brief pause to ensure update propagates
        verification_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!{chr(65 + processed_col_index)}{sheet_row}'
        ).execute()
        
        # Check if the cell now shows TRUE
        if verification_result.get('values'):
            cell_value = verification_result['values'][0][0]
            if str(cell_value).upper() == 'TRUE':
                logging.info(f"Marked row {sheet_row} as processed with checkbox in Google Sheet")
                return True
            else:
                logging.error(f"Failed to mark row {sheet_row}: Cell shows '{cell_value}' instead of TRUE")
                return False
        else:
            logging.error(f"Failed to mark row {sheet_row}: Could not read cell value after update")
            return False
        
    except Exception as e:
        logging.error(f"Failed to mark row {row_number} as processed: {e}")
        return False

def log_error_to_sheet(sheets_service, row_number, error_message):
    """Log an error message to column V for a specific row in the Google Sheet.
    
    Args:
        sheets_service: Google Sheets API service object
        row_number: 1-based row number to log error for (0-based internally)
        error_message: Error message to log
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Convert to 1-based row number for Google Sheets API
        sheet_row = row_number + 1 if isinstance(row_number, int) and row_number >= 0 else row_number
        
        # Get error log column index
        error_log_col_index = COLUMN_MAP['error_log']
        
        # Prepare the range for the error log column
        col_letter = chr(ord('A') + error_log_col_index)  # Convert index to column letter
        range_name = f"{SHEET_NAME}!{col_letter}{sheet_row}"
        
        # Prepare the error message with timestamp
        timestamp = time.strftime("%H:%M:%S")
        formatted_error = f"[{timestamp}] {error_message}"
        
        # Update the cell with the error message
        body = {'values': [[formatted_error]]}
        
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logging.info(f"Logged error to row {sheet_row}, column {col_letter}: {formatted_error}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to log error to sheet for row {row_number}: {e}")
        return False

def update_script_status(sheets_service, status_message):
    """Update the script status in cell V1.
    
    Args:
        sheets_service: Google Sheets API service object
        status_message: Current status message to display
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get error log column index (V = column 21)
        error_log_col_index = COLUMN_MAP['error_log']
        col_letter = chr(ord('A') + error_log_col_index)  # Convert index to column letter
        
        # V1 is always the first row of the error log column
        range_name = f"{SHEET_NAME}!{col_letter}1"
        
        # Prepare the status message with timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_status = f"[{timestamp}] SCRIPT: {status_message}"
        
        # Update the cell with the status message
        body = {'values': [[formatted_status]]}
        
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logging.info(f"Updated script status in {col_letter}1: {status_message}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to update script status: {e}")
        return False

def mark_job_status(sheets_service, row_number, status_type='acknowledged'):
    """Mark a job as acknowledged or completed in the Google Sheet using a checkbox.
    
    Args:
        sheets_service: The Google Sheets API service instance
        row_number (int): Row number in the sheet (0-based index)
        status_type (str): Either 'acknowledged' or 'completed'
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Convert to 1-based row number for Google Sheets API
        sheet_row = row_number + 1
        
        # Get the column index for the status column (0-based)
        if status_type == 'acknowledged':
            status_col_index = COLUMN_MAP['acknowledged']
        elif status_type == 'completed':
            status_col_index = COLUMN_MAP['completed']
        else:
            logging.error(f"Invalid status_type: {status_type}. Must be 'acknowledged' or 'completed'")
            return False
        
        # Get the actual sheet ID dynamically
        sheet_id = get_sheet_id(sheets_service, SPREADSHEET_ID, SHEET_NAME)
        if sheet_id is None:
            logging.error(f"Could not find sheet '{SHEET_NAME}' in spreadsheet")
            return False
        
        # Prepare the batch update request to set checkbox to TRUE
        requests = [{
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': row_number,
                    'endRowIndex': row_number + 1,
                    'startColumnIndex': status_col_index,
                    'endColumnIndex': status_col_index + 1
                },
                'cell': {
                    'userEnteredValue': {
                        'boolValue': True
                    }
                },
                'fields': 'userEnteredValue'
            }
        }]
        
        body = {'requests': requests}
        response = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        
        # Verify the update was successful
        if 'replies' in response:
            # Read back the value to confirm
            col_letter = chr(ord('A') + status_col_index)
            range_name = f"{SHEET_NAME}!{col_letter}{sheet_row}"
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name,
                valueRenderOption='UNFORMATTED_VALUE'
            ).execute()
            
            values = result.get('values', [])
            if values and len(values) > 0 and len(values[0]) > 0:
                actual_value = values[0][0]
                if actual_value is True or actual_value == 'TRUE':
                    logging.info(f"Marked row {sheet_row} as {status_type} with checkbox in Google Sheet")
                    return True
                else:
                    logging.warning(f"Checkbox update verification failed for row {sheet_row} {status_type}. Expected TRUE, got: {actual_value}")
                    return False
            else:
                logging.warning(f"Could not verify checkbox for row {sheet_row} {status_type} - no value returned")
                return False
        else:
            logging.error(f"Failed to mark row {sheet_row} as {status_type} - no response from API")
            return False
            
    except HttpError as error:
        logging.error(f"HTTP error marking row {row_number + 1} as {status_type}: {error}")
        return False
    except Exception as e:
        logging.error(f"Error marking row {row_number + 1} as {status_type}: {e}")
        return False

def get_job_status(row_data):
    """Check the acknowledged and completed status of a job.
    
    Args:
        row_data (list): The row data from Google Sheets
        
    Returns:
        dict: Dictionary with 'acknowledged' and 'completed' boolean values
    """
    try:
        acknowledged_col_index = COLUMN_MAP['acknowledged']
        completed_col_index = COLUMN_MAP['completed']
        
        status = {
            'acknowledged': False,
            'completed': False
        }
        
        # Check acknowledged status
        if len(row_data) > acknowledged_col_index:
            ack_value = row_data[acknowledged_col_index]
            if isinstance(ack_value, bool):
                status['acknowledged'] = ack_value
            elif isinstance(ack_value, str):
                status['acknowledged'] = ack_value.strip().upper() in ['TRUE', 'YES', '1', 'CHECKED', '✓']
        
        # Check completed status
        if len(row_data) > completed_col_index:
            comp_value = row_data[completed_col_index]
            if isinstance(comp_value, bool):
                status['completed'] = comp_value
            elif isinstance(comp_value, str):
                status['completed'] = comp_value.strip().upper() in ['TRUE', 'YES', '1', 'CHECKED', '✓']
        
        return status
        
    except Exception as e:
        logging.error(f"Error getting job status: {e}")
        return {'acknowledged': False, 'completed': False}

def is_row_processed(row_data):
    """Check if a row has already been processed based on the processed column checkbox.
    
    Args:
        row_data: List containing the row data from Google Sheets
        
    Returns:
        bool: True if row is marked as processed (checkbox checked), False otherwise
    """
    try:
        processed_col_index = COLUMN_MAP['processed']
        
        # Check if row has enough columns and if processed column is truthy
        if len(row_data) > processed_col_index:
            processed_value = row_data[processed_col_index]
            
            # Handle different types of values that indicate "processed"
            if isinstance(processed_value, bool):
                # Direct boolean from checkbox
                return processed_value
            elif isinstance(processed_value, str):
                # String representation - check for various true values
                processed_str = processed_value.strip().upper()
                return processed_str in ['TRUE', 'YES', '1', 'CHECKED', '✓']
            else:
                # For any other type, convert to string and check
                processed_str = str(processed_value).strip().upper()
                return processed_str in ['TRUE', 'YES', '1', 'CHECKED', '✓']
        
        return False
        
    except Exception as e:
        logging.error(f"Error checking if row is processed: {e}")
        return False

def is_column_18_processed(row_data):
    """Check if status column (index 18) indicates the row is processed.
    Based on user requirement - checking index 18 for completion status.
    
    Args:
        row_data: List containing the row data from Google Sheets
        
    Returns:
        bool: True if status column indicates row is processed, False otherwise
    """
    try:
        status_index = 18  # Index 18 - the status/checkbox column
        
        # Check if row has enough columns and if status column has a value
        if len(row_data) > status_index:
            status_value = row_data[status_index]
            
            # Handle different types of values that indicate "processed"
            if isinstance(status_value, bool):
                # Direct boolean from checkbox
                return status_value
            elif isinstance(status_value, str):
                # String representation - check for various true values
                processed_str = status_value.strip().upper()
                return processed_str in ['TRUE', 'YES', '1', 'CHECKED', '✓']
            else:
                # For any other type, convert to string and check
                processed_str = str(status_value).strip().upper()
                return processed_str in ['TRUE', 'YES', '1', 'CHECKED', '✓']
        
        return False
        
    except Exception as e:
        logging.error(f"Error checking if status column (index 18) is processed: {e}")
        return False

def get_unprocessed_rows(values):
    """Get all unprocessed rows from the sheet data.
    
    Args:
        values: List of lists containing all sheet data
        
    Returns:
        list: List of tuples (row_index, row_data) for unprocessed rows
        tuple: (None, "wait_for_update") if we should wait for file updates
    """
    unprocessed_rows = []
    
    for i, row in enumerate(values):
        # Skip header row (assuming first row is headers)
        if i == 0:
            continue
            
        # Check if row has minimum required columns
        if len(row) < MIN_COLUMNS:
            continue
            
        # Check if row has required data
        if not (row[COLUMN_MAP['google_drive_link']] and row[COLUMN_MAP['quantity']]):
            continue
            
        # Check job_id column (index 14) and status column (index 18) based on actual data structure
        # Note: User mentioned "column 14" and "column 18" but likely meant indices, not spreadsheet column numbers
        job_id_value = row[14] if len(row) > 14 else ""      # Index 14 - contains job_id like "9E8B7BBF"
        status_value = row[18] if len(row) > 18 else ""      # Index 18 - contains status/checkbox values
        
        # First, check if status column (index 18) indicates the row is already processed
        if is_column_18_processed(row):
            logging.info(f"Skipping row {i + 1}: Status column (index 18) indicates row is already processed")
            continue
        
        # Skip row if job_id (index 14) is empty - don't process rows without job ID
        if not job_id_value:
            logging.info(f"Skipping row {i + 1}: No job_id (index 14) - waiting for job ID to be populated")
            
            # For empty rows (both job_id and status empty), check if next 2 rows are also empty
            if not status_value:
                # Check if the next 2 rows are the same (also empty in the same columns)
                if i + 2 < len(values):  # Make sure we have at least 2 more rows to check
                    next_row_1 = values[i + 1] if i + 1 < len(values) else []
                    next_row_2 = values[i + 2] if i + 2 < len(values) else []
                    
                    # Check if next 2 rows also have empty job_id and status columns
                    next1_job_id = next_row_1[14] if len(next_row_1) > 14 else ""
                    next1_status = next_row_1[18] if len(next_row_1) > 18 else ""
                    next2_job_id = next_row_2[14] if len(next_row_2) > 14 else ""
                    next2_status = next_row_2[18] if len(next_row_2) > 18 else ""
                    
                    # If next 2 rows are also empty in the same columns, wait for file update
                    if (not next1_job_id and not next1_status and 
                        not next2_job_id and not next2_status):
                        logging.info(f"Next 2 rows ({i + 2}, {i + 3}) are also empty. Returning to first empty row {i + 1} and waiting for file update.")
                        return [(None, "wait_for_update")]
            
            continue
            
        # Row has data and is not processed - add to unprocessed list
        # Note: We don't need to check the old 'processed' column since column 18 is our status column
        unprocessed_rows.append((i, row))
    
    return unprocessed_rows

from googleapiclient.http import MediaIoBaseDownload

def extract_file_id_from_link(link):
    """Extracts the Google Drive file ID from a shareable link."""
    if "open?id=" in link:
        return link.split("open?id=")[1]
    elif "file/d/" in link:
        return link.split("file/d/")[1].split("/")[0]
    else:
        logging.warning(f"Could not extract file ID from link: {link}")
        return None

def download_file_from_drive(file_id, drive_service, job_id=None):
    """Downloads a file from Google Drive and optionally renames it to job_id with original extension.
    
    Args:
        file_id: Google Drive file ID
        drive_service: Google Drive service object
        job_id: Optional job ID to rename the file to {job_id}.{original_extension}
        
    Returns:
        tuple: (file_path, original_filename) if successful, (None, None) if failed
    """
    try:
        request = drive_service.files().get_media(fileId=file_id)

        # Create a 'downloads' directory if it doesn't exist
        downloads_dir = os.path.join(PROJECT_ROOT, "downloads")
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)

        # Get the file metadata to get the original filename
        file_metadata = drive_service.files().get(fileId=file_id).execute()
        original_filename = file_metadata.get("name", f"{file_id}.pdf")
        
        # Determine the final filename - use job_id if provided, otherwise original
        if job_id:
            # Preserve the original file extension
            _, original_extension = os.path.splitext(original_filename)
            final_filename = f"{job_id}{original_extension}"
            logging.info(f"Renaming file from '{original_filename}' to '{final_filename}' using job ID")
        else:
            final_filename = original_filename
            
        file_path = os.path.join(downloads_dir, final_filename)

        with io.FileIO(file_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logging.info(f"Download {int(status.progress() * 100)}%.")

        logging.info(f"File downloaded successfully: {file_path}")
        return file_path, original_filename
    except HttpError as error:
        logging.error(f"An error occurred while downloading the file: {error}")
        return None, None

class PrintJob:
    """A class to hold the print job information."""
    def __init__(self, drive_link, quantity, two_sided, paper_size, staples, hole_punch, 
                 date_submitted, job_deadline, downloaded_file_path, notes="", email="", 
                 room="", additional_notes="", job_id="", original_filename="", detected_page_size="", page_count=None):
        self.drive_link = drive_link
        self.quantity = quantity
        self.two_sided = two_sided
        self.paper_size = paper_size
        self.staples = staples
        self.hole_punch = hole_punch
        self.date_submitted = date_submitted
        self.job_deadline = job_deadline
        self.downloaded_file_path = downloaded_file_path
        self.notes = notes
        self.email = email
        self.room = room
        self.additional_notes = additional_notes
        self.job_id = job_id
        self.original_filename = original_filename
        self.detected_page_size = detected_page_size
        self.page_count = page_count

def delayed_cleanup(file_paths, delay_minutes):
    """
    Delete files after a specified delay to allow print spooling to complete.
    
    Args:
        file_paths (list): List of file paths to delete
        delay_minutes (int): Minutes to wait before deletion
    """
    def cleanup_worker():
        try:
            delay_seconds = delay_minutes * 60
            logging.info(f"Scheduled cleanup in {delay_minutes} minutes for {len(file_paths)} files")
            time.sleep(delay_seconds)
            
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logging.info(f"Delayed cleanup: Removed {file_path}")
                    else:
                        logging.warning(f"Delayed cleanup: File not found {file_path}")
                except OSError as e:
                    logging.error(f"Delayed cleanup: Error removing {file_path}: {e}")
            
            logging.info("Delayed cleanup completed")
            
        except Exception as e:
            logging.error(f"Error in delayed cleanup worker: {e}")
    
    # Start cleanup in a separate thread
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()

def generate_cover_sheet(job):
    """Generates the cover sheet content as a string."""
    # Use original filename for display, fall back to downloaded filename if not available
    display_filename = job.original_filename if job.original_filename else os.path.basename(job.downloaded_file_path)
    
    content = f"""
    **************************************************
    *                  COVER SHEET                   *
    **************************************************

    Job ID: {job.job_id}
    Submitted by: {job.email}
    Room: {job.room}

    Job Submitted: {job.date_submitted}
    Job Deadline:  {job.job_deadline}

    --------------------------------------------------

    Quantity: {job.quantity}
    Paper Size: {job.paper_size}
    Two-Sided: {job.two_sided}
    Staples: {job.staples}
    Hole Punch: {job.hole_punch}

    --------------------------------------------------

    File: {display_filename}

    Notes: {job.notes}
    Additional Instructions: {job.additional_notes}

    **************************************************
    """
    return content

def generate_receipt(job):
    """Generates the receipt content as a string."""
    # Use original filename for display, fall back to downloaded filename if not available
    display_filename = job.original_filename if job.original_filename else os.path.basename(job.downloaded_file_path)
    
    # ESC/POS commands for formatting
    BOLD_ON = '\x1B\x45\x01'      # ESC E 1 - Bold on
    BOLD_OFF = '\x1B\x45\x00'     # ESC E 0 - Bold off
    DOUBLE_WIDTH = '\x1B\x21\x20' # ESC ! 32 - Double width
    DOUBLE_HEIGHT = '\x1B\x21\x10' # ESC ! 16 - Double height
    DOUBLE_SIZE = '\x1B\x21\x30'   # ESC ! 48 - Double width and height
    NORMAL_SIZE = '\x1B\x21\x00'   # ESC ! 0 - Normal size
    
    content = f"""
================================
       PRINT JOB RECEIPT
================================

Job ID: {BOLD_ON}{DOUBLE_SIZE}{job.job_id}{NORMAL_SIZE}{BOLD_OFF}

  Submitted by: {BOLD_ON}{job.email}{BOLD_OFF}
  Room: {BOLD_ON}{job.room}{BOLD_OFF}

Dates:
  Submitted: {BOLD_ON}{job.date_submitted}{BOLD_OFF}
  Deadline: {BOLD_ON}{job.job_deadline}{BOLD_OFF}

================================

Print Specifications:
  Quantity: {BOLD_ON}{DOUBLE_WIDTH}{job.quantity}{NORMAL_SIZE}{BOLD_OFF} copies
  Paper Size: {BOLD_ON}{job.paper_size}{BOLD_OFF}
  Duplex: {BOLD_ON}{job.two_sided}{BOLD_OFF}
  Stapling: {BOLD_ON}{job.staples}{BOLD_OFF}
  Hole Punch: {BOLD_ON}{job.hole_punch}{BOLD_OFF}

================================

Additional Information:
  Notes: {BOLD_ON}{job.notes}{BOLD_OFF}
  Instructions: {BOLD_ON}{job.additional_notes}{BOLD_OFF}

================================

File Information:
  {BOLD_ON}{display_filename}{BOLD_OFF}"""

    # Add PDF page size if detected
    if hasattr(job, 'detected_page_size') and job.detected_page_size:
        content += f"""
  PDF Page Size: {BOLD_ON}{job.detected_page_size}{BOLD_OFF}"""

    # Add PDF page count if detected
    if hasattr(job, 'page_count') and job.page_count:
        content += f"""
  PDF Page Count: {BOLD_ON}{job.page_count} pages{BOLD_OFF}"""

    content += """

================================
"""
    
    # Add barcode at the end of receipt
    # Note: Barcode will be added as ESC/POS commands during printing
    # This placeholder helps maintain receipt structure
    return content

def generate_barcode_for_receipt(job_id):
    """Generate barcode ESC/POS commands for inclusion in receipt.
    
    Args:
        job_id (str): Job ID to encode in barcode
        
    Returns:
        bytes: ESC/POS barcode commands
    """
    try:
        from thermal_printer import ThermalPrinter
        
        # Create a temporary thermal printer instance just for barcode generation
        temp_printer = ThermalPrinter("temp")
        barcode_data = temp_printer.generate_barcode_escpos(job_id)
        
        if barcode_data:
            logging.info(f"Generated barcode for Job ID: {job_id}")
            return barcode_data
        else:
            logging.warning(f"Failed to generate barcode for Job ID: {job_id}")
            return b''
            
    except Exception as e:
        logging.error(f"Error generating barcode for receipt: {e}")
        return b''

def process_row(row, drive_service):
    """Processes a single row from the sheet.
    
    Returns:
        bool: True if processing was successful, False if there were errors
    """
    logging.info(f"Processing new row: {row}")

    try:
        # Check if the row has the expected number of columns
        if len(row) < MIN_COLUMNS:
            logging.warning(f"Skipping row with insufficient data: {row}")
            return False

        drive_link = row[COLUMN_MAP['google_drive_link']]
        file_id = extract_file_id_from_link(drive_link)

        if file_id:
            logging.info(f"Extracted file ID: {file_id}")
            
            # Get job_id first so we can use it for file naming
            job_id = row[14] if len(row) > 14 else ""
            
            # Download file with job_id for renaming
            downloaded_file_path, original_filename = download_file_from_drive(file_id, drive_service, job_id)
            
            if downloaded_file_path and original_filename:
                # Detect PDF page size for Adobe app integration
                page_size_info = detect_pdf_page_size(downloaded_file_path)
                detected_page_size = page_size_info['formatted_size'] if page_size_info else ""
                
                # Detect PDF page count for receipt information
                page_count = detect_pdf_page_count(downloaded_file_path)
                
                # Create a PrintJob instance from the row data
                job = PrintJob(
                    drive_link=drive_link,
                    quantity=row[COLUMN_MAP['quantity']],
                    two_sided=row[COLUMN_MAP['two_sided']],
                    paper_size=row[COLUMN_MAP['paper_size']],
                    staples=row[COLUMN_MAP['staples']],
                    hole_punch=row[COLUMN_MAP['hole_punch']],
                    date_submitted=row[COLUMN_MAP['date_submitted']],
                    job_deadline=row[COLUMN_MAP['job_deadline']],
                    downloaded_file_path=downloaded_file_path,
                    notes=row[1] if len(row) > 1 else "",
                    email=row[2] if len(row) > 2 else "",
                    room=row[9] if len(row) > 9 else "",
                    additional_notes=row[11] if len(row) > 11 else "",
                    job_id=job_id,
                    original_filename=original_filename,
                    detected_page_size=detected_page_size,
                    page_count=page_count
                )

                # Generate cover sheet and receipt content
                cover_sheet_content = generate_cover_sheet(job)
                receipt_content = generate_receipt(job)

                # Create file paths in the downloads directory
                # Use job_id for naming auxiliary files since the main file is now named with job_id
                base_filename = job_id if job_id else os.path.splitext(os.path.basename(downloaded_file_path))[0]
                downloads_dir = os.path.join(PROJECT_ROOT, "downloads")
                cover_sheet_path = os.path.join(downloads_dir, f"{base_filename}_cover.txt")
                receipt_path = os.path.join(downloads_dir, f"{base_filename}_receipt.txt")

                with open(cover_sheet_path, "w", encoding='utf-8') as f:
                    f.write(cover_sheet_content)
                logging.info(f"Cover sheet saved to {cover_sheet_path}")

                with open(receipt_path, "w", encoding='ascii', errors='replace') as f:
                    f.write(receipt_content)
                logging.info(f"Receipt saved to {receipt_path}")

                # --- Printing and File Transfer ---
                # 1. Print the receipt (text) with integrated barcode - check bypass setting
                if BYPASS_RECEIPT_PRINTER:
                    logging.info("Bypassing receipt printer as configured")
                else:
                    # Use thermal printer class directly for integrated barcode support
                    try:
                        from thermal_printer import ThermalPrinter
                        thermal = ThermalPrinter(RECEIPT_PRINTER_NAME)
                        
                        # Generate barcode for this job
                        barcode_data = thermal.generate_barcode_escpos(job.job_id)
                        if barcode_data:
                            logging.info(f"Generated barcode for Job ID: {job.job_id}")
                        else:
                            logging.warning("Barcode generation failed, will print receipt without barcode")
                        
                        # Print receipt with integrated barcode
                        if thermal.print_receipt(receipt_content, barcode_data=barcode_data):
                            logging.info("Receipt printed successfully with integrated barcode")
                        else:
                            logging.error("Failed to print receipt")
                    except Exception as e:
                        logging.error(f"Error printing receipt with barcode: {e}")
                        # Fallback to old method without barcode
                        print_document(receipt_path, RECEIPT_PRINTER_NAME, is_pdf=False)

                # 2. Print the actual job - auto-detect file type based on extension - check bypass setting
                if BYPASS_PDF_PRINTER:
                    logging.info("Bypassing PDF printer as configured")
                else:
                    file_extension = os.path.splitext(job.downloaded_file_path)[1].lower()
                    # Use PDF printing pathway for PDFs and document files that Adobe Acrobat/Reader can handle
                    is_pdf = file_extension in ['.pdf', '.docx', '.doc', '.xls', '.xlsx', '.ppt', '.pptx']
                    
                    # Calculate adjusted quantity (original quantity + 3)
                    try:
                        adjusted_quantity = int(job.quantity) + 3
                        logging.info(f"Adjusted quantity from {job.quantity} to {adjusted_quantity} (original + 3)")
                    except (ValueError, TypeError):
                        adjusted_quantity = job.quantity
                        logging.warning(f"Could not convert quantity '{job.quantity}' to integer, using original value")
                    
                    print_document(
                        job.downloaded_file_path, PDF_PRINTER_NAME, is_pdf=is_pdf, job_id=job.job_id,
                        quantity=adjusted_quantity, paper_size=job.paper_size, duplex=job.two_sided,
                        staple=job.staples, hole_punch=job.hole_punch
                    )

                # --- Cleanup ---
                if CLEANUP_AFTER_PROCESSING:
                    # Use delayed cleanup to allow print spooling to complete
                    files_to_cleanup = [downloaded_file_path, cover_sheet_path, receipt_path]
                    delayed_cleanup(files_to_cleanup, CLEANUP_DELAY_MINUTES)
                    logging.info(f"Scheduled delayed cleanup for {len(files_to_cleanup)} files in {CLEANUP_DELAY_MINUTES} minutes")
                
                return True
            else:
                logging.error(f"Failed to download file for row: {row}")
                return False
        else:
            logging.error(f"Could not extract file ID from drive link: {drive_link}")
            return False

    except IndexError:
        logging.warning(f"Skipping row due to missing column. Check [Columns] config and sheet. Row: {row}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error processing row: {e}")
        return False

def main():
    """Monitors the Google Sheet for new rows and processes them."""
    args = parser.parse_args()
    logging.info("Script starting up.")
    
    # Note: With Google Sheets tracking, start_row argument is less relevant
    # but we can still support it for initial processing
    if args.start_row is not None:
        logging.info(f"Manual start row specified: {args.start_row}")
        logging.info("Note: Using Google Sheets status tracking - processed column will be checked")
    
    creds = get_google_creds()

    if not creds:
        logging.error("Could not get Google credentials. Exiting.")
        return

    try:
        sheets_service = build("sheets", "v4", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)

        logging.info("Successfully connected to Google APIs.")
        
        # Update script status to show startup
        update_script_status(sheets_service, "Script started - monitoring for print jobs")
        
        if args.run_once:
            logging.info("Running in single-pass mode - will process available jobs once and exit")
            update_script_status(sheets_service, "Running in single-pass mode")
        else:
            logging.info("Monitoring Google Sheet for new jobs... Press Ctrl+C to stop.")
            update_script_status(sheets_service, "Monitoring for new jobs (continuous mode)")
        
        logging.info("Using Google Sheets status tracking via 'processed' column")

        # Main processing loop - either run once or continuously
        run_continuously = not args.run_once
        first_run = True
        
        while first_run or run_continuously:
            try:
                sheet = sheets_service.spreadsheets()
                result = (
                    sheet.values()
                    .get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME)
                    .execute()
                )
                values = result.get("values", [])

                if not values:
                    if args.run_once:
                        logging.info("No data found in the sheet. Exiting in run-once mode.")
                        update_script_status(sheets_service, "No data found - exiting")
                        break
                    else:
                        logging.info("No data found in the sheet. Waiting...")
                        update_script_status(sheets_service, "No data found - waiting for updates")
                        time.sleep(POLL_INTERVAL)
                        continue

                # Get all unprocessed rows
                unprocessed_rows = get_unprocessed_rows(values)
                
                # Check if we got a wait signal
                if (unprocessed_rows and len(unprocessed_rows) == 1 and 
                    unprocessed_rows[0][0] is None and unprocessed_rows[0][1] == "wait_for_update"):
                    if args.run_once:
                        logging.info("Multiple consecutive empty rows detected. Exiting in run-once mode.")
                        break
                    else:
                        logging.info("Multiple consecutive empty rows detected. Waiting for file update...")
                        time.sleep(POLL_INTERVAL)
                        continue
                
                if not unprocessed_rows:
                    if args.run_once:
                        logging.info("No unprocessed rows found. Exiting in run-once mode.")
                        update_script_status(sheets_service, "No unprocessed rows - exiting")
                        break
                    else:
                        logging.info("No unprocessed rows found. Waiting...")
                        update_script_status(sheets_service, "No unprocessed rows - waiting")
                        time.sleep(POLL_INTERVAL)
                        continue
                
                logging.info(f"Found {len(unprocessed_rows)} unprocessed row(s)")
                update_script_status(sheets_service, f"Processing {len(unprocessed_rows)} unprocessed row(s)")
                
                # Process only the FIRST unprocessed row, then wait and monitor
                # This ensures we stop and wait when encountering problems
                if unprocessed_rows:
                    row_index, row_data = unprocessed_rows[0]  # Take only the first row
                    
                    # Safety check for None values (from wait signals)
                    if row_index is None:
                        logging.info("Received wait signal, skipping processing")
                        time.sleep(POLL_INTERVAL)
                        continue
                    
                    try:
                        logging.info(f"Processing row {row_index + 1}")
                        update_script_status(sheets_service, f"Processing row {row_index + 1}")
                        
                        # Double-check if row is still unprocessed to prevent race conditions
                        # Re-fetch the specific row to check its current status
                        current_row_result = (
                            sheets_service.spreadsheets().values()
                            .get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!{row_index + 1}:{row_index + 1}")
                            .execute()
                        )
                        current_row_values = current_row_result.get("values", [])
                        
                        if current_row_values and is_row_processed(current_row_values[0]):
                            logging.info(f"Row {row_index + 1} was already processed by another instance. Skipping.")
                            continue
                        
                        # Process the row and check if it was successful
                        processing_successful = process_row(row_data, drive_service)
                        
                        if processing_successful:
                            # Mark row as processed in Google Sheets only if successful
                            if mark_row_as_processed(sheets_service, row_index):
                                logging.info(f"Successfully processed and marked row {row_index + 1}")
                                update_script_status(sheets_service, f"Successfully completed row {row_index + 1}")
                                
                                # Add 1-minute delay after successful processing to prevent print job pileup
                                logging.info("Waiting 10 seconds before processing next row to prevent print job pileup...")
                                update_script_status(sheets_service, "Waiting 10 seconds to prevent print queue overload")
                                time.sleep(10)
                            else:
                                logging.warning(f"Row {row_index + 1} processed but failed to mark as complete")
                                log_error_to_sheet(sheets_service, row_index, "Processed but failed to mark as complete")
                        else:
                            # Processing failed - don't mark as processed, wait and monitor
                            error_msg = f"Processing failed for row {row_index + 1}. Will retry after waiting..."
                            logging.warning(error_msg)
                            log_error_to_sheet(sheets_service, row_index, "Processing failed - will retry")
                            update_script_status(sheets_service, f"Processing failed for row {row_index + 1} - will retry")
                            logging.info("Waiting for file to be updated or fixed before retrying...")
                            
                    except Exception as e:
                        error_msg = f"Error processing row {row_index + 1}: {e}"
                        logging.error(error_msg)
                        log_error_to_sheet(sheets_service, row_index, f"Exception: {str(e)}")
                        update_script_status(sheets_service, f"Error processing row {row_index + 1}")
                        logging.info("Waiting before retrying due to processing error...")
                
                # In run-once mode, we process one row and then exit
                if args.run_once:
                    logging.info("Completed processing in run-once mode. Exiting.")
                    update_script_status(sheets_service, "Completed run-once mode - exiting")
                    break

                time.sleep(POLL_INTERVAL)
                first_run = False

            except HttpError as err:
                error_msg = f"An API error occurred: {err}"
                logging.error(error_msg)
                try:
                    update_script_status(sheets_service, f"API Error: {str(err)}")
                except:
                    pass  # If we can't update status due to API error, just continue
                time.sleep(60) # Wait a minute before retrying
            except Exception as e:
                error_msg = f"An unexpected error occurred: {e}"
                logging.error(error_msg, exc_info=True)
                try:
                    update_script_status(sheets_service, f"Unexpected Error: {str(e)}")
                except:
                    pass  # If we can't update status, just continue
                time.sleep(60)

    except HttpError as err:
        logging.error(f"A critical Google API error occurred: {err}")
    except FileNotFoundError:
        logging.error("Error: credentials.json not found. Please follow the setup instructions in README.md.")
    except Exception as e:
        logging.critical(f"A critical error occurred in main: {e}", exc_info=True)


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(PROJECT_ROOT, "activity.log")),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    main()
