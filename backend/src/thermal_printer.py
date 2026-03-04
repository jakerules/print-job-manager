import win32print
import win32api
import logging
import time
import os
import tempfile
import io

class ThermalPrinter:
    """A class to handle thermal receipt printer operations."""
    
    def __init__(self, printer_name):
        self.printer_name = printer_name
        self.logger = logging.getLogger(__name__)
    
    def generate_barcode_escpos(self, job_id):
        """Generate ESC/POS commands for Code128 barcode.
        
        Args:
            job_id (str): Job ID to encode in barcode
            
        Returns:
            bytes: ESC/POS commands for barcode, or empty bytes if generation fails
        """
        try:
            import barcode
            from barcode.writer import ImageWriter
            from PIL import Image
            
            # Generate Code128 barcode
            code128 = barcode.get_barcode_class('code128')
            barcode_image = code128(job_id, writer=ImageWriter())
            
            # Render to bytes
            buffer = io.BytesIO()
            barcode_image.write(buffer, options={
                'module_height': 10,  # Barcode height in mm
                'module_width': 0.3,  # Barcode width per module in mm
                'quiet_zone': 2,      # Quiet zone width in mm
                'font_size': 8,       # Font size for text below barcode
                'text_distance': 2,   # Distance between barcode and text in mm
                'write_text': True    # Show Job ID text below barcode
            })
            
            # Get the image
            buffer.seek(0)
            img = Image.open(buffer)
            
            # Convert to monochrome for thermal printer
            img = img.convert('1')  # Convert to 1-bit black and white
            
            # Resize if needed to fit receipt width (typically 384 pixels for 80mm thermal)
            max_width = 384
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Center the barcode on the receipt
            if img.width < max_width:
                # Calculate padding for centering
                left_padding = (max_width - img.width) // 2
                new_img = Image.new('1', (max_width, img.height), 1)  # White background
                new_img.paste(img, (left_padding, 0))
                img = new_img
            
            # Convert image to ESC/POS raster bitmap commands
            escpos_data = self._image_to_escpos(img)
            
            return escpos_data
            
        except ImportError as e:
            self.logger.error(f"Barcode libraries not available: {e}")
            self.logger.error("Install with: pip install python-barcode pillow")
            return b''
        except Exception as e:
            self.logger.error(f"Error generating barcode: {e}")
            return b''
    
    def _image_to_escpos(self, img):
        """Convert PIL Image to ESC/POS raster bitmap commands.
        
        Args:
            img: PIL Image object (1-bit monochrome)
            
        Returns:
            bytes: ESC/POS bitmap commands
        """
        try:
            # ESC/POS raster bitmap command: GS v 0
            # Format: GS v 0 m xL xH yL yH d1...dk
            # m = mode (0 = normal, 1 = double-width, 2 = double-height, 3 = quadruple)
            # xL, xH = width in bytes (little endian)
            # yL, yH = height in dots (little endian)
            
            width_bytes = (img.width + 7) // 8  # Round up to nearest byte
            height = img.height
            
            # Create bitmap data
            bitmap_data = bytearray()
            for y in range(height):
                row_data = 0
                bit_pos = 7
                for x in range(img.width):
                    pixel = img.getpixel((x, y))
                    # Invert: 0 = white (print), 1 = black (no print) for thermal printers
                    if pixel == 0:  # Black pixel
                        row_data |= (1 << bit_pos)
                    bit_pos -= 1
                    if bit_pos < 0:
                        bitmap_data.append(row_data)
                        row_data = 0
                        bit_pos = 7
                # Add last byte if not complete
                if bit_pos != 7:
                    bitmap_data.append(row_data)
            
            # Build ESC/POS command
            escpos_cmd = bytearray()
            escpos_cmd.extend(b'\x1D\x76\x30')  # GS v 0 - print raster bitmap
            escpos_cmd.append(0)  # m = normal size
            escpos_cmd.append(width_bytes & 0xFF)  # xL
            escpos_cmd.append((width_bytes >> 8) & 0xFF)  # xH
            escpos_cmd.append(height & 0xFF)  # yL
            escpos_cmd.append((height >> 8) & 0xFF)  # yH
            escpos_cmd.extend(bitmap_data)
            
            return bytes(escpos_cmd)
            
        except Exception as e:
            self.logger.error(f"Error converting image to ESC/POS: {e}")
            return b''
    
    def print_receipt(self, text):
        """Print a receipt to the thermal printer using raw data.
        
        Args:
            text (str): The text content to print
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # List all printers to verify
            printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
            if self.printer_name not in printers:
                self.logger.error(f"Printer {self.printer_name} not found!")
                return False
            
            # Method 1: Try raw printing first (most reliable for thermal printers)
            try:
                return self._print_receipt_raw(text)
            except Exception as raw_error:
                self.logger.warning(f"Raw printing failed: {raw_error}, trying file method...")
                
            # Method 2: Fallback to file-based printing
            return self._print_receipt_file(text)
                
        except Exception as e:
            self.logger.error(f"Error printing receipt to {self.printer_name}: {e}")
            return False
    
    def _print_receipt_raw(self, text, barcode_data=None):
        """Print receipt using raw data method with optional barcode."""
        handle = win32print.OpenPrinter(self.printer_name)
        
        try:
            # Start a document
            job_info = ("Receipt", "", "RAW")
            job_id = win32print.StartDocPrinter(handle, 1, job_info)
            
            # Start a page
            win32print.StartPagePrinter(handle)
            
            # Prepare raw data with proper ESC/POS commands for CITIZEN CT-S310II
            raw_data = (
                b'\x1B@'  # ESC @ - Initialize printer
                b'\x1B!\x00'  # ESC ! - Reset text formatting
            )
            
            # Add the text content
            raw_data += text.encode('ascii', errors='replace')
            
            # Add barcode section if provided
            if barcode_data:
                # Add spacing and header before barcode
                raw_data += b'\n\n'
                raw_data += b'SCAN TO TRACK:\n'.encode('ascii')
                # Center alignment for barcode
                raw_data += b'\x1B\x61\x01'  # ESC a 1 - Center alignment
                # Add the barcode image data
                raw_data += barcode_data
                # Reset alignment
                raw_data += b'\x1B\x61\x00'  # ESC a 0 - Left alignment
                self.logger.info("Barcode integrated into receipt")
            
            # Add final commands
            raw_data += (
                b'\n\n\n'  # Line feeds
                b'\x1D\x56\x41\x10'  # GS V A - Cut paper (CITIZEN specific)
            )
            
            # Send raw data to printer
            win32print.WritePrinter(handle, raw_data)
            
            # End page and document
            win32print.EndPagePrinter(handle)
            win32print.EndDocPrinter(handle)
            
            self.logger.info(f"Receipt sent via raw data to {self.printer_name}")
            return True
            
        finally:
            win32print.ClosePrinter(handle)
    
    def _print_receipt_file(self, text, barcode_data=None):
        """Print receipt using file-based method (fallback) with optional barcode."""
        # Get current default printer
        default_printer = win32print.GetDefaultPrinter()
        
        try:
            # Set our printer as default
            win32print.SetDefaultPrinter(self.printer_name)
            
            # Create a temporary file for the receipt
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as temp_file:
                temp_filename = temp_file.name
                
                # ESC @ - Initialize printer
                temp_file.write(b'\x1B@')
                
                # Add text content
                temp_file.write(text.encode('ascii', errors='replace'))
                
                # Add barcode section if provided
                if barcode_data:
                    temp_file.write(b'\n\n')
                    temp_file.write(b'SCAN TO TRACK:\n'.encode('ascii'))
                    temp_file.write(b'\x1B\x61\x01')  # Center alignment
                    temp_file.write(barcode_data)
                    temp_file.write(b'\x1B\x61\x00')  # Reset alignment
                
                # Add some line feeds and cut command
                temp_file.write(b'\n\n\n')
                temp_file.write(b'\x1D\x56\x41\x10')  # CITIZEN cut command
            
            # Print the temporary file
            win32api.ShellExecute(0, 'print', temp_filename, '', '.', 0)
            self.logger.info(f"Receipt sent via file to {self.printer_name}")
            
            # Clean up the temporary file after a short delay
            time.sleep(2)
            try:
                os.unlink(temp_filename)
            except OSError:
                pass  # File might still be in use by the print spooler
            
            return True
            
        finally:
            # Restore original default printer
            win32print.SetDefaultPrinter(default_printer)
    
    def is_available(self):
        """Check if the thermal printer is available.
        
        Returns:
            bool: True if printer is available, False otherwise
        """
        try:
            printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
            return self.printer_name in printers
        except Exception as e:
            self.logger.error(f"Error checking printer availability: {e}")
            return False
    
    def get_status(self):
        """Get the status of the thermal printer.
        
        Returns:
            dict: Printer status information
        """
        try:
            if not self.is_available():
                return {"status": "not_found", "message": f"Printer {self.printer_name} not found"}
            
            # Try to get printer handle
            handle = win32print.OpenPrinter(self.printer_name)
            try:
                printer_info = win32print.GetPrinter(handle, 2)
                status = printer_info['Status']
                
                status_messages = {
                    0: "Ready",
                    win32print.PRINTER_STATUS_PAUSED: "Paused",
                    win32print.PRINTER_STATUS_ERROR: "Error",
                    win32print.PRINTER_STATUS_PENDING_DELETION: "Pending Deletion",
                    win32print.PRINTER_STATUS_PAPER_JAM: "Paper Jam",
                    win32print.PRINTER_STATUS_PAPER_OUT: "Paper Out",
                    win32print.PRINTER_STATUS_MANUAL_FEED: "Manual Feed",
                    win32print.PRINTER_STATUS_PAPER_PROBLEM: "Paper Problem",
                    win32print.PRINTER_STATUS_OFFLINE: "Offline",
                    win32print.PRINTER_STATUS_IO_ACTIVE: "IO Active",
                    win32print.PRINTER_STATUS_BUSY: "Busy",
                    win32print.PRINTER_STATUS_PRINTING: "Printing",
                    win32print.PRINTER_STATUS_OUTPUT_BIN_FULL: "Output Bin Full",
                    win32print.PRINTER_STATUS_NOT_AVAILABLE: "Not Available",
                    win32print.PRINTER_STATUS_WAITING: "Waiting",
                    win32print.PRINTER_STATUS_PROCESSING: "Processing",
                    win32print.PRINTER_STATUS_INITIALIZING: "Initializing",
                    win32print.PRINTER_STATUS_WARMING_UP: "Warming Up",
                    win32print.PRINTER_STATUS_TONER_LOW: "Toner Low",
                    win32print.PRINTER_STATUS_NO_TONER: "No Toner",
                    win32print.PRINTER_STATUS_PAGE_PUNT: "Page Punt",
                    win32print.PRINTER_STATUS_USER_INTERVENTION: "User Intervention Required",
                    win32print.PRINTER_STATUS_OUT_OF_MEMORY: "Out of Memory",
                    win32print.PRINTER_STATUS_DOOR_OPEN: "Door Open"
                }
                
                status_message = status_messages.get(status, f"Unknown status: {status}")
                
                return {
                    "status": "available",
                    "message": status_message,
                    "printer_name": printer_info['pPrinterName'],
                    "location": printer_info.get('pLocation', ''),
                    "comment": printer_info.get('pComment', '')
                }
                
            finally:
                win32print.ClosePrinter(handle)
                
        except Exception as e:
            self.logger.error(f"Error getting printer status: {e}")
            return {"status": "error", "message": str(e)}
