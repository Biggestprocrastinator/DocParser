# AI-Powered Document Analysis & Extraction
**Track 2 Submission | HCL GUVI Intern Hiring Hackathon 2026**

## Architecture: The Augmented Hybrid Pipeline
Unlike standard OCR solutions, this system implements an Augmented Hybrid Pipeline designed to solve the "Handwriting Gap" and "Structural Complexity" in modern documents.

* **Stage 1: Local OCR Grounding** - Uses Tesseract OCR and OpenCV (Otsu Thresholding, 2x Scaling interpolations) to extract raw text and establish a secure, spatial baseline.
* **Stage 2: Multimodal Vision Audit** - Leverages Gemini 3 Flash to visually "see" the original document. It cross-references the raw OCR text with the visual image to accurately capture messy handwriting (e.g., student names and handwritten amounts) and dynamically ignore UI noise like phone status bars or screen artifacts.
* **Stage 3: Asynchronous Orchestration** - Utilizes Redis and Celery to process large multi-page PDFs and complex DOCX files asynchronously without causing API timeouts or blocking the main execution thread.

## Key Features
* **Handwriting Intelligence**: Accurately extracts handwritten ink from gym receipts, university fee slips, and academic sketches where standard OCR fails.
* **Universal File Support**: Seamlessly processes `.png`, `.jpg`, `.pdf`, and `.docx` file formats.
* **Structured Intelligence**: Automatically identifies and categorizes Names, Dates, Organizations, and Amounts into a flat, machine-readable JSON schema.
* **Async Resilience**: Handles long-running tasks via background workers, providing a `task_id` for status polling to ensure a robust user experience.

## Tech Stack
* **Core Logic**: Python 3.10+, FastAPI
* **AI/ML**: Google Gemini 3 Flash (Multimodal)
* **OCR & Computer Vision**: Pytesseract, OpenCV (`cv2`)
* **Task Management**: Celery, Redis (Upstash)
* **Document Handling**: `pdf2image`, `python-docx`, Poppler

## AI Tool Disclosure
* **Google Gemini 3 Flash**: Primary engine for multimodal document reasoning and entity extraction.
* **Gemini AI**: Assisted in system architecture design, debugging local environment conflicts (Tesseract/Poppler), and drafting technical documentation.

## Setup & Installation

### 1. Prerequisites
* Python 3.10+
* Tesseract OCR (Installed and added to System PATH)
* Poppler (For PDF-to-Image conversion)

### 2. Local Setup
```bash
# Clone the repository
git clone https://github.com/Biggestprocrastinator/DocParser.git
cd DocParser

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r src/requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the `src/` directory based on `.env.example`:
```env
GEMINI_API_KEY=your_gemini_key_here
CELERY_BROKER_URL=your_redis_url_here
CELERY_RESULT_BACKEND=your_redis_url_here
API_KEY=your_api_key_here
```

### 4. Run the Application
Open two terminal instances.

**Terminal 1:** Start Redis/Celery Worker
```bash
cd src
celery -A tasks worker --loglevel=info --pool=solo
```

**Terminal 2:** Start FastAPI Server
```bash
cd src
uvicorn main:app --reload
```

## API Documentation

### Analyze Document
`POST /api/document-analyze`

**Request Headers:**
* `x-api-key`: `your_api_key_here`

**Request Body:**
```json
{
  "fileName": "receipt.png",
  "fileType": "image",
  "fileBase64": "iVBORw0KG..."
}
```

**Success Response (200 OK):**
```json
{
  "status": "success",
  "fileName": "receipt.png",
  "summary": "fee receipt for xyx University...",
  "entities": {
    "names": ["x y z"],
    "dates": ["1-Jul-2025"],
    "organizations": ["123 University", "123 Bank"],
    "amounts": ["123"]
  },
  "sentiment": "Neutral"
}
```

## Known Limitations
* **Rate Limits**: Bound by Gemini Free Tier (15 requests per minute).
* **Encrypted Files**: Cannot process password-protected PDFs.

## Author
**Niraj Wadkar**  
Third-year B.Tech Computer Science Student  