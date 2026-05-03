"""
/upload endpoint.

Accepts a single CSV or JSON file, parses it, and returns metadata
including the ``file_id`` required by downstream endpoints.
"""

from fastapi import APIRouter, File, UploadFile, status

from app.models.schemas import UploadResponse
from app.services.ingestion_service import DataIngestionService

router = APIRouter()


@router.post(
    "/",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV or JSON dataset",
    description=(
        "Upload a raw CSV or JSON file. The API parses it, stores it in memory, "
        "and returns a `file_id` that identifies the dataset for subsequent calls "
        "to `/summary` and `/report`."
    ),
)
async def upload_file(
    file: UploadFile = File(..., description="CSV or JSON file to upload."),
) -> UploadResponse:
    """
    Parse and register an uploaded dataset.

    - Accepts **CSV** (`.csv`, `.txt`) and **JSON** (`.json`) files.
    - Maximum file size is configurable via `MAX_UPLOAD_SIZE_MB` (default 50 MB).
    - Returns a `file_id` used to reference this dataset in other endpoints.
    """
    file_id, df = await DataIngestionService.ingest(file)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or "upload",
        rows=len(df),
        columns=df.columns.tolist(),
    )
