"""
/summary endpoint.

Returns descriptive statistics for a previously uploaded dataset.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import SummaryResponse
from app.services.analytics_service import AnalyticsService
from app.services.ingestion_service import DataIngestionService

router = APIRouter()


@router.get(
    "/{file_id}",
    response_model=SummaryResponse,
    summary="Get summary statistics for an uploaded dataset",
    description=(
        "Returns per-column descriptive statistics (mean, median, std, missing %, "
        "top category, etc.) for the dataset identified by `file_id`."
    ),
)
async def get_summary(file_id: str) -> SummaryResponse:
    """
    Compute and return descriptive statistics for the given dataset.

    Path parameter:
    - **file_id**: The identifier returned by `POST /upload`.

    Returns a `SummaryResponse` containing per-column statistics.
    """
    try:
        df, filename = DataIngestionService.get_dataframe(file_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with file_id='{file_id}' not found. "
                   "Please upload the file first via POST /upload.",
        )

    return AnalyticsService.summarise(file_id, filename, df)
