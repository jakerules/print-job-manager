import os
import time
import logging
import subprocess
import win32print
import win32api
import threading

def detect_pdf_orientation(pdf_path):
    """Detect PDF orientation by analyzing page dimensions.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: 'landscape' if width > height, 'portrait' otherwise
    """
    try:
        # Try to import PyPDF2 for PDF analysis
        try:
            import PyPDF2
        except ImportError:
            logging.warning("PyPDF2 not available for orientation detection, defaulting to portrait")
            return 'portrait'
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            if len(pdf_reader.pages) > 0:
                page = pdf_reader.pages[0]
                # Get page dimensions
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                
                # Return orientation based on dimensions
                if width > height:
                    return 'landscape'
                else:
                    return 'portrait'
            else:
                logging.warning(f"PDF {pdf_path} has no pages, defaulting to portrait")
                return 'portrait'
                
    except Exception as e:
        logging.warning(f"Failed to detect PDF orientation for {pdf_path}: {e}, defaulting to portrait")
        return 'portrait'

def configure_printer_settings(printer_name, quantity=None, paper_size=None, duplex=None, staple=None, hole_punch=None, orientation=None):
    """Configure printer settings for print job options.
    
    Args:
        printer_name (str): Name of the printer
        quantity (str/int, optional): Number of copies
        paper_size (str, optional): Paper size setting
        duplex (str, optional): Duplex/two-sided setting
        staple (str, optional): Staple setting
        hole_punch (str, optional): Hole punch setting
        orientation (str, optional): Page orientation ("portrait" or "landscape")
        
    Returns:
        dict: Printer settings configuration for logging
    """
    settings_applied = {}
    
    try:
        # Open printer handle
        printer_handle = win32print.OpenPrinter(printer_name)
        
        try:
            # Get current printer settings
            printer_info = win32print.GetPrinter(printer_handle, 2)
            devmode = printer_info['pDevMode']
            
            # Apply quantity setting (copies)
            if quantity and str(quantity).isdigit():
                copies = int(quantity)
                if copies > 0:
                    devmode.Copies = copies
                    settings_applied['copies'] = copies
                    logging.info(f"Set printer copies to {copies}")
            
            # Apply duplex setting
            if duplex:
                duplex_lower = str(duplex).lower()
                if duplex_lower in ['yes', 'true', '1', 'on']:
                    devmode.Duplex = 2  # DMDUP_VERTICAL (long edge)
                    settings_applied['duplex'] = 'Long Edge'
                    logging.info("Set printer to duplex mode (long edge)")
                elif duplex_lower in ['short', 'horizontal']:
                    devmode.Duplex = 3  # DMDUP_HORIZONTAL (short edge)
                    settings_applied['duplex'] = 'Short Edge'
                    logging.info("Set printer to duplex mode (short edge)")
                elif duplex_lower in ['no', 'false', '0', 'off']:
                    devmode.Duplex = 1  # DMDUP_SIMPLEX (single-sided)
                    settings_applied['duplex'] = 'Single-sided'
                    logging.info("Set printer to single-sided mode")
            
            # Apply paper size setting
            if paper_size:
                paper_size_lower = str(paper_size).lower()
                if 'letter' in paper_size_lower:
                    devmode.PaperSize = 1  # DMPAPER_LETTER
                    settings_applied['paper_size'] = 'Letter'
                elif 'legal' in paper_size_lower:
                    devmode.PaperSize = 5  # DMPAPER_LEGAL
                    settings_applied['paper_size'] = 'Legal'
                elif 'a4' in paper_size_lower:
                    devmode.PaperSize = 9  # DMPAPER_A4
                    settings_applied['paper_size'] = 'A4'
                elif 'a3' in paper_size_lower:
                    devmode.PaperSize = 8  # DMPAPER_A3
                    settings_applied['paper_size'] = 'A3'
                logging.info(f"Set paper size to {settings_applied.get('paper_size', paper_size)}")
            
            # Apply orientation setting
            if orientation:
                orientation_lower = str(orientation).lower()
                if 'landscape' in orientation_lower:
                    devmode.Orientation = 2  # DMORIENT_LANDSCAPE
                    settings_applied['orientation'] = 'Landscape'
                    logging.info("Set orientation to Landscape")
                elif 'portrait' in orientation_lower:
                    devmode.Orientation = 1  # DMORIENT_PORTRAIT
                    settings_applied['orientation'] = 'Portrait'
                    logging.info("Set orientation to Portrait")
            
            # Note: Staple and hole punch settings are typically printer-specific
            # and may require printer driver-specific APIs or print processor commands
            if staple and str(staple).lower() not in ['no', 'false', '0', 'off', 'none']:
                settings_applied['staple'] = str(staple)
                logging.info(f"Staple setting requested: {staple} (printer-specific implementation needed)")
            
            if hole_punch and str(hole_punch).lower() not in ['no', 'false', '0', 'off', 'none']:
                settings_applied['hole_punch'] = str(hole_punch)
                logging.info(f"Hole punch setting requested: {hole_punch} (printer-specific implementation needed)")
            
            # Apply the modified settings back to the printer
            printer_info['pDevMode'] = devmode
            win32print.SetPrinter(printer_handle, 2, printer_info, 0)
            
        finally:
            win32print.ClosePrinter(printer_handle)
            
    except Exception as e:
        logging.warning(f"Failed to configure printer settings for {printer_name}: {e}")
        # Continue with printing even if settings configuration fails
    
    return settings_applied

def print_pdf_document(pdf_path, printer_name, adobe_path, job_id=None, add_footer=True, 
                      quantity=None, paper_size=None, duplex=None, staple=None, hole_punch=None, orientation=None):
    """Print a PDF document using Adobe Acrobat or Reader with print options.
    
    Args:
        pdf_path (str): Path to the PDF file
        printer_name (str): Name of the printer
        adobe_path (str): Path to Adobe executable
        job_id (str, optional): Job ID for footer text
        add_footer (bool): Whether to add footer text (default: True)
        quantity (str/int, optional): Number of copies to print
        paper_size (str, optional): Paper size (e.g., "Letter", "Legal", "A4")
        duplex (str, optional): Duplex setting (e.g., "Yes", "No", "True", "False")
        staple (str, optional): Staple setting (e.g., "Yes", "No", "Top Left")
        hole_punch (str, optional): Hole punch setting (e.g., "Yes", "No", "3-hole")
        orientation (str, optional): Page orientation ("portrait" or "landscape")
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if not os.path.exists(adobe_path):
        raise FileNotFoundError(f"Adobe Acrobat/Reader not found: {adobe_path}")

    # Auto-detect orientation if not provided
    if orientation is None:
        try:
            orientation = detect_pdf_orientation(pdf_path)
        except:
            orientation = 'portrait'  # Default fallback
    
    # Adjust quantity by adding 3 if quantity is provided
    if quantity is not None:
        try:
            adjusted_quantity = int(quantity) + 3
            logging.info(f"Original quantity: {quantity}, Adjusted quantity (quantity+3): {adjusted_quantity}")
        except (ValueError, TypeError):
            adjusted_quantity = 1
            logging.warning(f"Invalid quantity '{quantity}', using default of 1")
    else:
        adjusted_quantity = 1

    # Check printer status before attempting to print
    try:
        printer_status = check_printer_status(printer_name)
        if "Error" in str(printer_status) or "Offline" in str(printer_status):
            logging.warning(f"Printer {printer_name} status: {printer_status}")
    except Exception as e:
        logging.warning(f"Could not check printer status for {printer_name}: {e}")

    # Set the printer as default
    previous = win32print.GetDefaultPrinter()
    win32print.SetDefaultPrinter(printer_name)
    
    # Configure printer settings for orientation and copies
    try:
        configure_printer_settings(printer_name, adjusted_quantity, paper_size, duplex, staple, hole_punch, orientation)
    except Exception as e:
        logging.warning(f"Could not configure printer settings: {e}")

    # Determine which PDF file to print
    print_pdf_path = pdf_path
    temp_footer_pdf = None
    
    try:
        # Add footer if requested and job_id is available
        if add_footer and job_id:
            try:
                from pdf_footer_utils import add_footer_to_pdf
                # Try to get configuration from main module
                try:
                    import main
                    font_size = getattr(main, 'FOOTER_FONT_SIZE', 6)
                    font_family = getattr(main, 'FOOTER_FONT_FAMILY', 'Times-Roman')
                except (ImportError, AttributeError):
                    # Fallback to defaults if config not available
                    font_size = 6
                    font_family = 'Times-Roman'
                
                temp_footer_pdf = add_footer_to_pdf(pdf_path, job_id, font_size=font_size, font_family=font_family)
                print_pdf_path = temp_footer_pdf
                logging.info(f"Added footer text to PDF for job {job_id}")
            except Exception as e:
                logging.warning(f"Failed to add footer to PDF, printing without footer: {e}")
                # Continue with original PDF if footer addition fails
        elif add_footer and not job_id:
            logging.info("Footer requested but no job_id provided, printing without footer")
        
        # Configure printer settings based on print options
        settings_applied = {}
        if any([quantity, paper_size, duplex, staple, hole_punch, orientation]):
            logging.info(f"Configuring printer settings for {printer_name}")
            settings_applied = configure_printer_settings(
                printer_name, quantity, paper_size, duplex, staple, hole_punch, orientation
            )
            if settings_applied:
                logging.info(f"Applied printer settings: {settings_applied}")
        
        # Skip ShellExecute and go directly to Adobe for more reliable printing
        logging.info(f"Using Adobe Acrobat for printing to {printer_name}")

        try:
            # Use Adobe's command line printing with enhanced parameters for page size preservation
            # /t = silent print and terminate
            # /h = hide splash screen
            cmd = [adobe_path, '/t', print_pdf_path, printer_name]
            
            # Log the command for debugging
            logging.info(f"Running Adobe command: {' '.join(cmd)}")
            
            # Set environment variables that can influence Adobe printing behavior
            env = os.environ.copy()
            # These registry-like settings help preserve original document formatting
            env['ACROBAT_PRESERVE_PAGE_SIZE'] = '1'
            env['ACROBAT_FIT_PAGE'] = '0'  # Don't fit to page, preserve original size

            # Use fire-and-forget approach to prevent hanging
            # Start the process but don't wait for it to complete
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP  # Detach from parent
            )
            
            logging.info(f"Adobe process started with PID {process.pid}")
            
            # Give Adobe a moment to start processing, then move on
            import time
            time.sleep(3)  # Allow Adobe to start and begin processing
            
            # Schedule cleanup of the Adobe process after a delay
            import threading
            def delayed_cleanup():
                time.sleep(60)  # Wait 60 seconds for print to complete
                try:
                    if process.poll() is None:  # Process still running
                        logging.info("Cleaning up Adobe process after 60 seconds")
                        try:
                            import psutil
                            parent = psutil.Process(process.pid)
                            for child in parent.children(recursive=True):
                                child.terminate()
                            parent.terminate()
                        except:
                            process.terminate()
                except Exception as e:
                    logging.debug(f"Adobe cleanup completed or failed: {e}")
            
            # Start cleanup thread
            cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
            cleanup_thread.start()
            
            logging.info("Adobe printing initiated successfully (non-blocking)")
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"Adobe printing failed with exit code {e.returncode}: {e.stderr}")
            return False
        except Exception as e:
            logging.error(f"Adobe printing failed to start: {e}")
            return False

    finally:
        # Clean up temporary footer file if created
        if temp_footer_pdf and os.path.exists(temp_footer_pdf):
            try:
                os.remove(temp_footer_pdf)
                logging.debug(f"Cleaned up temporary footer PDF: {temp_footer_pdf}")
            except Exception as e:
                logging.warning(f"Failed to clean up temporary footer PDF: {e}")
                
        # Always restore the original default printer
        try:
            win32print.SetDefaultPrinter(previous)
        except Exception as e:
            logging.warning(f"Failed to restore default printer: {e}")

def print_text_document(text_path, printer_name, is_receipt=False):
    """Print a text document with proper encoding and printer-specific handling."""
    if not os.path.exists(text_path):
        raise FileNotFoundError(f"Text file not found: {text_path}")
    
    # Read the text content
    try:
        with open(text_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(text_path, 'r', encoding='cp1252', errors='replace') as f:
            content = f.read()
    
    if is_receipt:
        # For receipt printers, use ThermalPrinter
        from thermal_printer import ThermalPrinter
        printer = ThermalPrinter(printer_name)
        if printer.print_receipt(content):
            return True
    
    # For regular text documents, use Windows print command
    try:
        subprocess.run(
            ["print", f"/D:{printer_name}", text_path],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        raise Exception(f"Print command failed: {error_msg}")

def check_printer_status(printer_name):
    """Check printer status and return any issues."""
    try:
        printer_handle = win32print.OpenPrinter(printer_name)
        try:
            info = win32print.GetPrinter(printer_handle, 2)
            status = []
            
            if info['Status'] == 0:
                return ["Printer OK"]
            
            if info['Status'] & win32print.PRINTER_STATUS_PAPER_OUT:
                status.append("Out of paper")
            if info['Status'] & win32print.PRINTER_STATUS_DOOR_OPEN:
                status.append("Cover is open")
            if info['Status'] & win32print.PRINTER_STATUS_ERROR:
                status.append("Printer error")
            if info['Status'] & win32print.PRINTER_STATUS_OFFLINE:
                status.append("Printer offline")
            
            return status if status else ["Printer OK"]
        finally:
            win32print.ClosePrinter(printer_handle)
    except Exception as e:
        return [f"Error checking printer status: {e}"]