"""
/report endpoint.

Generates and streams a downloadable PDF or Excel report for a
previously uploaded dataset.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.models.schemas import ReportRequest
from app.services.ingestion_service import DataIngestionService
from app.services.report_service import ReportGenerationService

router = APIRouter()


@router.post(
    "/",
    summary="Generate a PDF or Excel report",
    description=(
        "Generate a downloadable report for an already-uploaded dataset. "
        "Specify `format: 'pdf'` or `format: 'excel'` in the request body. "
        "The response is a binary file stream."
    ),
    responses={
        200: {
            "description": "Binary PDF or XLSX file.",
            "content": {
                "application/pdf": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            },
        }
    },
)
async def generate_report(request: ReportRequest) -> Response:
    """
    Generate and return a formatted report.

    Request body:
    - **file_id**: Dataset identifier from `POST /upload`.
    - **format**: `pdf` (default) or `excel`.
    - **title**: Optional report title (max 120 chars).
    - **include_charts**: Embed charts in PDF (default: true).
    - **columns**: Optional list of column names to include.

    Returns the report as a binary file download.
    """
    try:
        df, filename = DataIngestionService.get_dataframe(request.file_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with file_id='{request.file_id}' not found. "
                   "Please upload the file first via POST /upload.",
        )

    data, media_type, out_name = ReportGenerationService.generate(
        df=df,
        filename=filename,
        file_id=request.file_id,
        request=request,
    )

    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"',
            "Content-Length": str(len(data)),
        },
    )
