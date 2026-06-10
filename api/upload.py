import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["Uploads"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

class UploadResponse(BaseModel):
    file_id: str
    file_type: str
    original_filename: str
    saved_filepath: str
    size_bytes: int

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(..., regex="^(cmdb|actual)$")
):
    """
    Uploads a file representing either expected CMDB inventory (CSV) or actual server scan (JSON).
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Check file extensions
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if file_type == "cmdb" and ext != ".csv":
        raise HTTPException(status_code=400, detail="CMDB file must be a CSV file (.csv)")
    if file_type == "actual" and ext != ".json":
        raise HTTPException(status_code=400, detail="Actual inventory file must be a JSON file (.json)")
        
    # Generate unique filename to avoid collision
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_type}_{file_id}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)
    
    try:
        # Write file chunk by chunk
        size = 0
        with open(saved_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                buffer.write(chunk)
                size += len(chunk)
    except Exception as e:
        # Clean up in case of failure
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
        
    return UploadResponse(
        file_id=file_id,
        file_type=file_type,
        original_filename=filename,
        saved_filepath=saved_path,
        size_bytes=size
    )
