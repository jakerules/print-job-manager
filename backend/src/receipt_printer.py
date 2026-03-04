import win32print
import win32api
import logging
import time

logging.basicConfig(level=logging.INFO)

RECEIPT_PRINTER = "CITIZEN CT-S310II"

def print_receipt(text):
    try:
        # List all printers to verify
        printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
        if RECEIPT_PRINTER not in printers:
            logging.error(f"Printer {RECEIPT_PRINTER} not found!")
            return False
            
        # Get current default printer
        default_printer = win32print.GetDefaultPrinter()
        
        try:
            # Set our printer as default
            win32print.SetDefaultPrinter(RECEIPT_PRINTER)
            
            # Create receipt content with ESC/POS commands
            with open('receipt.txt', 'wb') as f:
                # ESC @ - Initialize printer
                f.write(b'\x1B@')
                
                # Add text content
                f.write(text.encode('ascii', errors='replace'))
                
                # Add some line feeds
                f.write(b'\n\n\n\n')
                
                # ESC i - Cut paper
                f.write(b'\x1B\x69')
            
            # Print it
            win32api.ShellExecute(0, 'print', 'receipt.txt', '', '.', 0)
            logging.info("Receipt sent to printer")
            return True
            
        finally:
            # Restore original default printer
            win32print.SetDefaultPrinter(default_printer)
            
    except Exception as e:
        logging.error(f"Error printing receipt: {e}")
        return False

if __name__ == "__main__":
    # Test receipt
    test_text = """
RECEIPT TEST
===========

Testing ESC/POS commands
via simple print method

Date: {}
""".format(time.strftime('%Y-%m-%d %H:%M:%S'))

    print_receipt(test_text)
