"""
Module for converting PDFs to markdown using Mistral OCR.
"""
import os
import base64
import uuid
import logging
from mistralai import Mistral

# Local imports
from ydrpolicy.data_collection import config  # Changed to absolute import

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def pdf_to_markdown(pdf_url, output_folder):
    """
    Convert a PDF to markdown with extracted images.
    
    Args:
        pdf_url (str): URL to the PDF file
        output_folder (str): Folder to save markdown and images
        
    Returns:
        str: Path to the created markdown file, or empty string if failed
    """
    try:
        # Set up Mistral client
        api_key = config.MISTRAL_API_KEY
        if not api_key:
            logger.error("No Mistral API key found in environment variables")
            return ""
        
        client = Mistral(api_key=api_key)
        
        # Create the folder structure
        images_dir = os.path.join(output_folder, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Process the PDF with OCR
        logger.info(f"Processing PDF with OCR: {pdf_url}")
        ocr_response = client.ocr.process(
            model=config.OCR_MODEL,
            document={
                "type": "document_url",
                "document_url": pdf_url
            },
            include_image_base64=True,
        )
        
        # Process OCR response and save images
        markdown_content = get_combined_markdown(ocr_response, images_dir)
        
        # Generate a filename based on the URL
        filename = os.path.basename(pdf_url)
        if not filename or '.' not in filename:
            filename = f"pdf_{uuid.uuid4().hex[:8]}.md"
        else:
            filename = os.path.splitext(filename)[0] + ".md"
        
        # Save markdown to file
        markdown_path = os.path.join(output_folder, filename)
        with open(markdown_path, 'w', encoding='utf-8') as file:
            file.write(markdown_content)
        
        logger.info(f"PDF successfully converted to markdown: {markdown_path}")
        return markdown_path
        
    except Exception as e:
        logger.error(f"Error converting PDF to markdown: {str(e)}")
        return ""

def save_base64_image(base64_str, output_dir, img_name=None):
    """Save a base64 encoded image to a file and return the path"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate a unique filename if none provided
    if img_name is None:
        img_name = f"image_{uuid.uuid4().hex[:8]}.png"
    elif not any(img_name.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
        img_name += '.png'  # Default to PNG if no extension
    
    # Remove data URL prefix if present (e.g., "data:image/png;base64,")
    if ',' in base64_str:
        base64_str = base64_str.split(',', 1)[1]
    
    # Decode and save the image
    img_path = os.path.join(output_dir, img_name)
    with open(img_path, "wb") as img_file:
        img_file.write(base64.b64decode(base64_str))
    
    return img_path

def replace_images_in_markdown(markdown_str, images_dict, output_dir):
    """Replace image references with links to saved files"""
    # Create image directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Map to store original ID to new filename
    id_to_path = {}
    
    # First save all images
    for img_id, base64_str in images_dict.items():
        filename = f"{img_id}.png"  # Use the original ID as filename
        file_path = save_base64_image(base64_str, output_dir, filename)
        # Store relative path for markdown linking
        id_to_path[img_id] = os.path.join("images", filename)
    
    # Then update markdown to reference the files
    for img_id, rel_path in id_to_path.items():
        markdown_str = markdown_str.replace(f"![{img_id}]({img_id})", f"![{img_id}]({rel_path})")
    
    return markdown_str

def get_combined_markdown(ocr_response, images_dir):
    """Process OCR response, save images, and return updated markdown"""
    markdowns = []
    
    for page in ocr_response.pages:
        image_data = {}
        for img in page.images:
            image_data[img.id] = img.image_base64
        
        updated_markdown = replace_images_in_markdown(page.markdown, image_data, images_dir)
        markdowns.append(updated_markdown)
    
    return "\n\n".join(markdowns)