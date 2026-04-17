import os
import json
from celery import Celery
import pytesseract
from pdf2image import convert_from_path
import google.generativeai as genai
from dotenv import load_dotenv
import cv2
import numpy as np
import re
import PIL.Image

from utils import clean_text, preprocess_image, extract_text_from_docx

load_dotenv()

# Initialize Celery connected to Redis
app = Celery(
    'document_tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Initialize Gemini Client
genai.configure(api_key=os.getenv('GEMINI_API_KEY', 'default_key'))

def extract_text_with_ocr(file_path: str, file_type: str) -> str:
    """
    Extracts text from a given image or PDF file using Tesseract OCR,
    passing each page/image through an OpenCV pre-processing pipeline first.
    """
    text = ""
    try:
        if file_type.lower() == 'pdf':
            # Convert PDF pages to images then OCR them
            images = convert_from_path(file_path)
            for img in images:
               
                cv_img = np.array(img)
                cv_img = cv_img[:, :, ::-1].copy() 
                
                
                processed = preprocess_image(cv_img)
                text += pytesseract.image_to_string(processed) + "\n"
        else: 
            
            cv_img = cv2.imread(file_path)
            if cv_img is not None:
                processed = preprocess_image(cv_img)
                text += pytesseract.image_to_string(processed)
    except Exception as e:
        print(f"OCR Error: {e}")
        text = ""
        
    return text

@app.task
def analyze_document_task(file_path: str, file_type: str, file_name: str) -> dict:

    #Celery task to handle OCR and AI analysis via Gemini API.

    try:
        #  Pure Text Extraction for DOCX
        if file_type.lower() == 'docx':
            extracted_text = extract_text_from_docx(file_path)
            
            if not extracted_text.strip():
                return {
                    "fileName": file_name,
                    "summary": "No text detected",
                    "entities": {"names": [], "dates": [], "organizations": [], "amounts": []},
                    "sentiment": "Neutral"
                }
                
            
            prompt = (
                "You are a research analyst. Summarize this Word document and extract the entities (names, dates, organizations, amounts) and sentiment.\n"
                "Output ONLY valid JSON. The JSON must have exact top-level keys: 'summary', 'entities', and 'sentiment'.\n"
                "- 'summary': A concise brief of the text.\n"
                "- 'entities': An object containing exactly these arrays: 'names', 'dates', 'organizations', 'amounts'. "
                "Map found data into these specific categories. If none are found, use an empty list [].\n"
                "- 'sentiment': Must be exactly one of the words: 'Positive', 'Neutral', or 'Negative'.\n\n"
                f"Document Text:\n{extracted_text[:6000]}"
            )
            content_payload = [prompt]

        #Multimodal Vision for Images & PDFs
        else:
            #1: Extract Text via PyTesseract
            extracted_text = extract_text_with_ocr(file_path, file_type)
            
            if not extracted_text.strip():
                return {
                    "fileName": file_name,
                    "summary": "No text detected",
                    "entities": {
                        "names": [],
                        "dates": [],
                        "organizations": [],
                        "amounts": []
                    },
                    "sentiment": "Neutral"
                }
                
            # Clean the OCR text
            cleaned_text = clean_text(extracted_text)

            
            hints = []
            
            # 1. Names
            name_matches = re.finditer(r'(?:Name|To|Customer)[\s:]+([A-Za-z\s]{3,30})', cleaned_text, re.IGNORECASE)
            for m in name_matches:
                match = m.group(1).strip()
                if match: hints.append(f"Potential Name: {match}")
                    
            # 2. Amounts
            amount_matches = re.finditer(r'(?:[\$€£]?\s*\b\d{3,6}\b|\$\s*\d+\.\d{2}\b)', cleaned_text)
            for m in amount_matches:
                hints.append(f"Potential Amount: {m.group(0).strip()}")
                
            # 3. Dates
            date_matches = re.finditer(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b', cleaned_text, re.IGNORECASE)
            for m in date_matches:
                hints.append(f"Potential Date: {m.group(0).strip()}")
                
            hints_text = "\n".join(hints) if hints else "No direct regex hints found."

            #2: Extract data using Gemini API with Multimodal Vision prompt
            prompt = f"""Act as a Senior Document Intelligence Specialist. You are analyzing a document using an Augmented Hybrid Pipeline (Vision + OCR).

### 🔎 MISSION
Your goal is to extract structured data with high recall for the HCL GUVI rubric. If the OCR text is messy or empty, perform a "Vision Audit" by looking at the provided image/PDF directly to find the information.

### 📂 INPUT DATA:
--- OCR Data & Regex Hints ---
[HINTS]
{hints_text}
[/HINTS]
Document Text:
{cleaned_text[:5000]}
------------------------------

### 📋 EXTRACTION DIRECTIVES
1. **Summary**: Write a 3-5 sentence professional summary. If the document contains technical diagrams (e.g., algorithms or sketches), describe the functional flow and key concepts depicted.
2. **Sentiment**: [Positive, Negative, or Neutral].
3. **Entities - Names**: Extract all human names. 
   - *Logic*: Automatically normalize common OCR artifacts (e.g., resolve '1' as 'I', or '0' as 'o' in surnames) based on high-probability linguistic structures.
4. **Entities - Organizations**: Extract all formal institutions, including companies, gyms, government agencies, and educational universities.
5. **Entities - Dates**: Extract specific calendar dates, month/year pairings, and time durations (e.g., "6 months", "1-year").
6. **Entities - Amounts**: 
   - **INCLUDE**: All financial values (e.g., "7000"), academic metrics (e.g., "SGPA", "CGPA", "Grades"), and percentages.
   - **EXCLUDE**: Strictly filter out metadata noise such as phone numbers, postal codes, and internal database UUIDs.

### 🧩 HANDLING FAILURES
- Never return "No text detected" if there is any visual content.
- If a field is truly missing, return an empty list [].
- Treat handwritten text with the same priority as printed text.

### 📦 OUTPUT (Strict JSON)
{{
  "status": "success",
  "summary": "...",
  "entities": {{
    "names": [],
    "dates": [],
    "organizations": [],
    "amounts": []
  }},
  "sentiment": "..."
}}"""
            
            # Load the PIL Image for Gemini Multimodal API
            try:
                if file_type.lower() == 'pdf':
                    pil_pages = convert_from_path(file_path)
                    gemini_image = pil_pages[0] if pil_pages else None
                else:
                    with PIL.Image.open(file_path) as img:
                        img.load() #load into memory
                        gemini_image = img 
            except Exception as e:
                print(f"PIL Load Error: {e}")
                gemini_image = None
                
            content_payload = [prompt, gemini_image] if gemini_image else [prompt]

        
        
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        response = model.generate_content(content_payload, generation_config={"response_mime_type": "application/json"})
        
        # 3: Parse and Structure Gemini Response
        try:
            raw_response = response.text.strip()
            
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:-3].strip()
            elif raw_response.startswith("```"):
                raw_response = raw_response[3:-3].strip()
                
            ai_data = json.loads(raw_response)
            
            return {
                "fileName": file_name,
                "summary": ai_data.get("summary", "Summary missing"),
                "entities": ai_data.get("entities", {
                    "names": [],
                    "dates": [],
                    "organizations": [],
                    "amounts": []
                }),
                "sentiment": ai_data.get("sentiment", "Neutral")
            }
        except Exception:
            
            return {
                "fileName": file_name,
                "summary": "Data extraction failed due to parsing error.",
                "entities": {
                    "names": [],
                    "dates": [],
                    "organizations": [],
                    "amounts": []
                },
                "sentiment": "Neutral"
            }

    except Exception as e:
         return {"error": f"Analysis failed: {str(e)}"}
    finally:
        # 4: Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
