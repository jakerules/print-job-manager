"""
PDF Footer Utilities for Adobe Printing
Adds footer text to PDF documents before printing with Adobe Acrobat/Reader.
"""

import os
import logging
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from PyPDF2 import PdfReader, PdfWriter
import io


def add_footer_to_pdf(pdf_path, job_id, output_path=None, font_size=6, font_family="Times-Roman"):
    """
    Add footer text to a PDF document before printing.
    
    Args:
        pdf_path (str): Path to the original PDF file
        job_id (str): Job ID to include in footer text
        output_path (str, optional): Path for output file. If None, creates temp file.
        font_size (int): Font size for footer text (default: 6)
        font_family (str): Font family for footer text (default: "Times-Roman")
        
    Returns:
        str: Path to the modified PDF file with footer
        
    Raises:
        Exception: If PDF processing fails
    """
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        if not job_id:
            logging.warning("No job_id provided for footer text, using 'UNKNOWN'")
            job_id = "UNKNOWN"
            
        # Read the original PDF
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        total_pages = len(reader.pages)
        logging.info(f"Adding footer to {total_pages} pages for job {job_id}")
        
        # Process each page
        for page_num, page in enumerate(reader.pages, 1):
            # Create footer overlay - convert Decimal to float for arithmetic operations
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            footer_pdf = create_footer_overlay(job_id, page_num, total_pages, page_width, page_height, font_size, font_family)
            
            # Merge footer with original page
            page.merge_page(footer_pdf.pages[0])
            writer.add_page(page)
        
        # Determine output path
        if output_path is None:
            # Create downloads directory if it doesn't exist
            downloads_dir = "downloads"
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
            
            # Create temporary file in downloads directory
            temp_fd, output_path = tempfile.mkstemp(suffix='.pdf', prefix=f'{job_id}_footer_', dir=downloads_dir)
            os.close(temp_fd)  # Close the file descriptor, we'll write to the path
        
        # Write the modified PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
            
        logging.info(f"Footer added successfully to PDF: {output_path}")
        return output_path
        
    except Exception as e:
        logging.error(f"Failed to add footer to PDF {pdf_path}: {e}")
        raise


def create_footer_overlay(job_id, page_num, total_pages, page_width, page_height, font_size=6, font_family="Times-Roman"):
    """
    Create a PDF overlay with footer text.
    
    Args:
        job_id (str): Job ID for footer text
        page_num (int): Current page number
        total_pages (int): Total number of pages
        page_width (float): Width of the page in points
        page_height (float): Height of the page in points
        font_size (int): Font size for footer text (default: 6)
        font_family (str): Font family for footer text (default: "Times-Roman")
        
    Returns:
        PdfReader: PDF reader object with footer overlay
    """
    # Create footer text
    footer_text = f"Job: {job_id} - Page {page_num} of {total_pages}"
    
    # Create a BytesIO buffer for the overlay PDF
    buffer = io.BytesIO()
    
    # Create the overlay PDF
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # Set font: configurable family and size
    c.setFont(font_family, font_size)
    
    # Position footer at bottom center of page
    # Leave 0.5 inch margin from bottom
    footer_x = page_width / 2
    footer_y = 0.5 * inch
    
    # Calculate text width for centering
    text_width = c.stringWidth(footer_text, font_family, font_size)
    footer_x = (page_width - text_width) / 2
    
    # Draw the footer text
    c.drawString(footer_x, footer_y, footer_text)
    c.save()
    
    # Create PdfReader from the buffer
    buffer.seek(0)
    return PdfReader(buffer)


def add_footer_and_print(pdf_path, printer_name, adobe_path, job_id):
    """
    Add footer to PDF and print it using Adobe Acrobat/Reader.
    
    Args:
        pdf_path (str): Path to the original PDF file
        printer_name (str): Name of the printer
        adobe_path (str): Path to Adobe executable
        job_id (str): Job ID for footer text
        
    Returns:
        bool: True if successful, False otherwise
    """
    temp_pdf_path = None
    try:
        # Add footer to PDF
        temp_pdf_path = add_footer_to_pdf(pdf_path, job_id)
        
        # Import the existing print function
        from printer_utils import print_pdf_document
        
        # Print the modified PDF
        result = print_pdf_document(temp_pdf_path, printer_name, adobe_path)
        
        if result:
            logging.info(f"Successfully printed PDF with footer for job {job_id}")
        else:
            logging.error(f"Failed to print PDF with footer for job {job_id}")
            
        return result
        
    except Exception as e:
        logging.error(f"Failed to add footer and print PDF: {e}")
        return False
        
    finally:
        # Clean up temporary file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                logging.debug(f"Cleaned up temporary footer PDF: {temp_pdf_path}")
            except Exception as e:
                logging.warning(f"Failed to clean up temporary footer PDF: {e}")