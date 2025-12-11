import os
import sys
import logging
import pdfplumber
from PIL import Image
import pytesseract
import whisper

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
whisper_model = whisper.load_model("base")

async def read_file(upload_file):
    """Save and extract text from uploaded file."""
    logger.info(f"Saving uploaded file: {upload_file.filename}")
    os.makedirs("uploads", exist_ok=True)
    file_bytes=await upload_file.read()
    file_name=upload_file.filename
    file_path=os.path.join("uploads", file_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    extracted_text=""

    try:
        extension=os.path.splitext(file_name)[1].lower()

        if extension==".pdf":
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted_text += page.extract_text() + "\n"
                logger.info(f"Extracted text from {file_name}: {extracted_text[:100]}..")
                extracted_text="PDF Text: " + extracted_text
        elif extension in [".jpg", ".jpeg", ".png"]:
            img=Image.open(file_path)
            extracted_text=pytesseract.image_to_string(img)
            extracted_text="Photo Text: " + extracted_text
            logger.info(f"Extracted text from {file_name}: {extracted_text[:100]}..")
            
        elif extension in [".mp3", ".wav", ".m4a", ".aac", ".ogg"]:
            logger.info(f"Processing audio file: {file_name}")
            result = whisper_model.transcribe(file_path)
            extracted_text = result["text"]
            logger.info(f"Audio transcription: {extracted_text[:100]}...")
            extracted_text="Audio Text: " + extracted_text
        else:
            logger.warning(f"File for text extraction.")
        
    except Exception as e:
        logger.error(f"Error reading file: {e}")

    return extracted_text