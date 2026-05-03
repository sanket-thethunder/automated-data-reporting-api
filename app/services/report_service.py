"""
Report Generation Service.

Produces downloadable PDF or Excel reports from a pandas DataFrame.

PDF generation uses ReportLab (pure-Python, no external binary needed).
Excel generation uses openpyxl with rich formatting.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.core.exceptions import ReportGenerationError
from app.core.logger import get_logger
from app.models.schemas import ReportFormat, ReportRequest
from app.services.analytics_service import AnalyticsService

logger = get_logger(__name__)

# Brand colours
BRAND_BLUE = colors.HexColor("#2563EB")
BRAND_DARK = colors.HexColor("#1E293B")
LIGHT_GREY = colors.HexColor("#F1F5F9")


class ReportGenerationService:
    """
    Orchestrates report creation.

    Dispatches to the appropriate private method based on the requested format.
    """

    @classmethod
    def generate(
        cls,
        df: pd.DataFrame,
        filename: str,
        file_id: str,
        request: ReportRequest,
    ) -> tuple[bytes, str, str]:
        """
        Generate a report and return its raw bytes plus metadata.

        Args:
            df: Source DataFrame.
            filename: Original uploaded filename.
            file_id: Dataset identifier.
            request: Validated :class:`~app.models.schemas.ReportRequest`.

        Returns:
            ``(bytes, media_type, suggested_filename)``

        Raises:
            ReportGenerationError: If rendering fails.
        """
        # Optionally filter columns
        if request.columns:
            missing = [c for c in request.columns if c not in df.columns]
            if missing:
                raise ReportGenerationError(
                    f"Requested columns not found in dataset: {missing}"
                )
            df = df[request.columns]

        try:
            if request.format == ReportFormat.PDF:
                data = cls._generate_pdf(df, filename, request)
                media_type = "application/pdf"
                out_name = f"report_{file_id[:8]}.pdf"
            else:
                data = cls._generate_excel(df, filename, request)
                media_type = (
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet"
                )
                out_name = f"report_{file_id[:8]}.xlsx"
        except ReportGenerationError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error during report generation")
            raise ReportGenerationError(str(exc)) from exc

        logger.info(
            "Generated %s report for file_id=%s  (%d bytes)",
            request.format.value,
            file_id,
            len(data),
        )
        return data, media_type, out_name

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    @classmethod
    def _generate_pdf(
        cls, df: pd.DataFrame, filename: str, request: ReportRequest
    ) -> bytes:
        """Render a multi-section PDF report using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            textColor=BRAND_DARK,
            fontSize=22,
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            textColor=BRAND_BLUE,
            spaceBefore=14,
            spaceAfter=4,
        )
        body_style = styles["BodyText"]

        story = []

        # ── Title & metadata ────────────────────────────────────────────
        story.append(Paragraph(request.title, title_style))
        story.append(
            Paragraph(
                f"<font color='grey' size='9'>Source: {filename} &nbsp;|&nbsp; "
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC</font>",
                body_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE))
        story.append(Spacer(1, 0.4 * cm))

        # ── Dataset overview ────────────────────────────────────────────
        story.append(Paragraph("Dataset Overview", heading_style))
        overview_data = [
            ["Metric", "Value"],
            ["Total Rows", f"{len(df):,}"],
            ["Total Columns", str(len(df.columns))],
            ["Numeric Columns", str(len(df.select_dtypes(include="number").columns))],
            [
                "Categorical Columns",
                str(len(df.select_dtypes(exclude="number").columns)),
            ],
            [
                "Missing Values",
                f"{df.isna().sum().sum():,} "
                f"({df.isna().mean().mean() * 100:.1f}%)",
            ],
        ]
        story.append(cls._make_table(overview_data))
        story.append(Spacer(1, 0.4 * cm))

        # ── Summary statistics ──────────────────────────────────────────
        numeric_df = df.select_dtypes(include="number")
        if not numeric_df.empty:
            story.append(Paragraph("Descriptive Statistics (Numeric)", heading_style))
            desc = numeric_df.describe().round(4).reset_index()
            stat_rows = [desc.columns.tolist()] + desc.values.tolist()
            stat_rows = [[str(v) for v in row] for row in stat_rows]
            story.append(cls._make_table(stat_rows, header_colour=BRAND_BLUE))
            story.append(Spacer(1, 0.4 * cm))

        # ── Data preview ────────────────────────────────────────────────
        story.append(Paragraph("Data Preview (first 20 rows)", heading_style))
        preview = df.head(20).fillna("").astype(str)
        preview_rows = [preview.columns.tolist()] + preview.values.tolist()
        story.append(cls._make_table(preview_rows, header_colour=BRAND_DARK))

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def _make_table(data: list[list], header_colour=None) -> Table:
        """Create a styled ReportLab Table from a list-of-lists."""
        header_colour = header_colour or BRAND_BLUE
        col_count = len(data[0]) if data else 1
        available = A4[0] - 4 * cm  # page width minus margins
        col_width = available / col_count

        tbl = Table(data, colWidths=[col_width] * col_count, repeatRows=1)
        style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_colour),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
        tbl.setStyle(style)
        return tbl

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------

    @classmethod
    def _generate_excel(
        cls, df: pd.DataFrame, filename: str, request: ReportRequest
    ) -> bytes:
        """Build a multi-sheet Excel workbook using openpyxl."""
        wb = openpyxl.Workbook()

        # ── Sheet 1: Raw Data ───────────────────────────────────────────
        ws_data = wb.active
        ws_data.title = "Raw Data"
        cls._write_dataframe(ws_data, df, title=f"{request.title} — Raw Data")

        # ── Sheet 2: Summary Stats ──────────────────────────────────────
        ws_stats = wb.create_sheet("Summary Statistics")
        numeric_df = df.select_dtypes(include="number")
        if not numeric_df.empty:
            desc = numeric_df.describe().round(4).reset_index()
            desc.rename(columns={"index": "Statistic"}, inplace=True)
            cls._write_dataframe(
                ws_stats, desc, title="Descriptive Statistics (Numeric Columns)"
            )
        else:
            ws_stats["A1"] = "No numeric columns found in the dataset."

        # ── Sheet 3: Missing Values ─────────────────────────────────────
        ws_missing = wb.create_sheet("Missing Values")
        missing_df = pd.DataFrame(
            {
                "Column": df.columns,
                "Missing Count": df.isna().sum().values,
                "Missing %": (df.isna().mean() * 100).round(2).values,
            }
        )
        cls._write_dataframe(ws_missing, missing_df, title="Missing Value Analysis")

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def _write_dataframe(
        ws, df: pd.DataFrame, title: str = ""
    ) -> None:
        """Write a DataFrame to a worksheet with header styling."""
        header_fill = PatternFill("solid", fgColor="2563EB")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        alt_fill = PatternFill("solid", fgColor="F1F5F9")
        thin = Side(style="thin", color="CBD5E1")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        start_row = 1
        if title:
            ws["A1"] = title
            ws["A1"].font = Font(bold=True, size=13, color="1E293B")
            start_row = 3

        # Headers
        for col_idx, col_name in enumerate(df.columns, start=1):
            cell = ws.cell(row=start_row, column=col_idx, value=str(col_name))
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="left", vertical="center")
            cell.border = border

        # Rows
        for row_idx, row in enumerate(df.itertuples(index=False), start=start_row + 1):
            fill = alt_fill if row_idx % 2 == 0 else PatternFill()
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.fill = fill
                cell.alignment = Alignment(vertical="center")
                cell.border = border

        # Auto-fit column widths
        for col_idx in range(1, len(df.columns) + 1):
            col_letter = get_column_letter(col_idx)
            max_width = max(
                len(str(ws.cell(row=r, column=col_idx).value or ""))
                for r in range(start_row, ws.max_row + 1)
            )
            ws.column_dimensions[col_letter].width = min(max_width + 4, 40)

        ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
