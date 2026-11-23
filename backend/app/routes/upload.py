# backend/app/routes/upload.py
# Upload endpoint accepting multi-file uploads with size, extension validation, and immediate parsing (FR-1 to FR-5).

from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.app.config import settings
from backend.app.storage.sqlite_store import store
from backend.app.models.dataset import DatasetModel
from backend.app.ingestion.validator import validate_file_metadata, sanitize_filename
from backend.app.ingestion import parse_uploaded_file

router = APIRouter(tags=["Upload"])


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """
    Receives multi-file uploads, validates format/size, isolates saved file,
    runs safe parsing (no macro execution), and creates populated dataset profiles.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were provided in the upload request.",
        )

    uploaded_datasets: List[DatasetModel] = []
    overall_warnings: List[str] = []

    for file in files:
        raw_filename = file.filename or "unknown_file"
        clean_filename = sanitize_filename(raw_filename)

        content = await file.read()
        size_bytes = len(content)

        # Validate metadata, extension, and file size limits (FR-1, FR-3)
        is_valid, error_msg, ext = validate_file_metadata(
            filename=clean_filename,
            size_bytes=size_bytes,
            content_type=file.content_type,
        )

        if not is_valid:
            overall_warnings.append(f"Skipped '{raw_filename}': {error_msg}")
            continue

        dataset_id = str(uuid.uuid4())
        saved_file_name = f"{dataset_id}_{clean_filename}"
        file_path = settings.uploads_dir / saved_file_name

        try:
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            overall_warnings.append(f"Failed to save '{raw_filename}' to storage: {str(e)}")
            continue

        # Safely parse file (CSV, TSV, XLSX, JSON) without macro/formula execution (FR-2, FR-3)
        file_warnings: List[str] = []
        try:
            tables, parse_warns = parse_uploaded_file(
                file_path=file_path,
                original_filename=clean_filename,
                dataset_id=dataset_id,
            )
            file_warnings.extend(parse_warns)
            status_code = "profiled" if tables else "uploaded"
        except Exception as e:
            # Corrupted or unsupported file handled gracefully as a message, not crash (FR-3)
            tables = []
            status_code = "error"
            file_warnings.append(f"Parsing error: {str(e)}")

        dataset = DatasetModel(
            id=dataset_id,
            filename=clean_filename,
            file_type=ext.replace(".", ""),
            size_bytes=size_bytes,
            status=status_code,
            tables=tables,
            warnings=file_warnings,
        )

        store.save_dataset(dataset)
        uploaded_datasets.append(dataset)
        overall_warnings.extend(file_warnings)

    return {
        "datasets": uploaded_datasets,
        "warnings": overall_warnings,
        "count": len(uploaded_datasets),
    }
