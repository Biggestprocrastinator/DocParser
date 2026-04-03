from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import tempfile
import os
from dotenv import load_dotenv
from celery.exceptions import TimeoutError as CeleryTimeoutError
from celery.result import AsyncResult

from utils import save_base64_to_tempfile
from tasks import analyze_document_task, app as celery_app

load_dotenv()

app = FastAPI(title="AI-Powered Document Analysis API")

# Setup Authentication
API_KEY_NAME = "x-api-key"
EXPECTED_API_KEY = os.getenv("API_KEY", "YOUR_SECRET_API_KEY")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != EXPECTED_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
    return api_key

# Request Schema
class DocumentRequest(BaseModel):
    fileName: str
    fileType: str
    fileBase64: str

@app.post("/api/document-analyze")
async def document_analyze(
    request: DocumentRequest, 
    api_key: str = Security(verify_api_key)
):
    try:
        # Step 1: Decode Base64 to a temporary file
        temp_dir = tempfile.gettempdir()
        temp_file_path = save_base64_to_tempfile(
            base64_string=request.fileBase64,
            temp_dir=temp_dir,
            file_name=request.fileName
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 payload: {str(e)}")

    try:
        
        task = analyze_document_task.delay(
            file_path=temp_file_path,
            file_type=request.fileType,
            file_name=request.fileName
        )
        
        
        result = task.get(timeout=25)
        
        
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
             
        
        return {
            "status": "success",
            "fileName": request.fileName,
            "summary": result.get("summary", ""),
            "entities": result.get("entities", {"names": [], "dates": [], "organizations": [], "amounts": []}),
            "sentiment": result.get("sentiment", "Neutral")
        }

    except CeleryTimeoutError:
        
        # Return a 202 Accepted status and tell the client the Task ID
        return {
            "status": "processing",
            "message": "Document is very large and still processing in the background.",
            "task_id": task.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.get("/api/document-status/{task_id}")
async def get_document_status(task_id: str, api_key: str = Security(verify_api_key)):
    """
    Client can poll this endpoint if the initial request times out.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == 'PENDING' or task_result.state == 'STARTED':
        return {"status": "processing"}
    elif task_result.state == 'SUCCESS':
        res = task_result.result
        if "error" in res:
             raise HTTPException(status_code=500, detail=res["error"])
             
        return {
            "status": "success",
            "fileName": res.get("fileName", "unknown_file"),
            "summary": res.get("summary", ""),
            "entities": res.get("entities", {"names": [], "dates": [], "organizations": [], "amounts": []}),
            "sentiment": res.get("sentiment", "Neutral")
        }
    elif task_result.state == 'FAILURE':
        raise HTTPException(status_code=500, detail="Background task failed.")
    else:
        return {"status": task_result.state}

