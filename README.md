# 📊 Automated Data Reporting Generator

A production-ready **FastAPI** REST service that ingests raw CSV or JSON data, computes descriptive statistics, and generates downloadable **PDF** or **Excel** reports — automatically.

---

## 🧩 Problem → Solution

| Problem | Solution |
|---|---|
| Business users receive raw CSV/JSON exports and must manually build reports in Excel | Single API call produces a formatted, ready-to-share report |
| Ad-hoc data analysis is slow and inconsistent | Standardised statistics endpoint ensures every dataset is analysed the same way |
| Report creation is not version-controlled or reproducible | API-driven pipeline integrates naturally with CI/CD and automation scripts |

---

## ✨ Features

- **`POST /upload`** — Upload a CSV or JSON file; get back a `file_id` and column metadata
- **`GET /summary/{file_id}`** — Descriptive statistics per column (mean, median, std, missing %, top category)
- **`POST /report`** — Generate a formatted **PDF** or **Excel** report with overview, stats table, and data preview
- **Input validation** with Pydantic v2 — clear error messages for invalid payloads
- **OOP service layer** — `DataIngestionService`, `AnalyticsService`, `ReportGenerationService`
- **Swagger UI** auto-generated at `/docs`; ReDoc at `/redoc`
- **Unit + integration tests** with pytest
- **Docker** ready — single command to run

---

## 🗂️ Project Structure

```
automated-data-reporting-api /
├── app/
│   ├── main.py                  # FastAPI app, middleware, router registration
│   ├── core/
│   │   ├── config.py            # Pydantic-Settings configuration
│   │   ├── exceptions.py        # Custom exception hierarchy + handlers
│   │   └── logger.py            # Centralised logger factory
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── services/
│   │   ├── ingestion_service.py # File parsing (CSV, JSON) + in-memory registry
│   │   ├── analytics_service.py # Descriptive statistics computation
│   │   └── report_service.py    # PDF (ReportLab) + Excel (openpyxl) generation
│   └── api/
│       └── endpoints/
│           ├── upload.py
│           ├── summary.py
│           └── report.py
├── tests/
│   ├── unit/
│   │   ├── test_analytics_service.py
│   │   └── test_ingestion_service.py
│   └── integration/
│       └── test_api.py
├── data/samples/                # Example CSV and JSON files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

---

## 🚀 Quick Start

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/sanket-thethunder/automated-data-reporting-api.git
cd automated-data-reporting-api
docker compose up --build
```

API available at **http://localhost:8000**  
Swagger UI at **http://localhost:8000/docs**

---

### Option 2 — Local (Python 3.12+)

```bash
# 1. Clone
git clone https://github.com/sanket-thethunder/automated-data-reporting-apir.git
cd automated-data-reporting-api

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn app.main:app --reload
```

---

## 📡 API Usage

### 1. Upload a file

```bash
curl -X POST http://localhost:8000/upload/ \
  -F "file=@data/samples/sales.csv"
```

**Response:**
```json
{
  "file_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "sales.csv",
  "rows": 10,
  "columns": ["product", "revenue", "units_sold", "region", "quarter", "in_stock"],
  "message": "File uploaded and parsed successfully."
}
```

---

### 2. Get summary statistics

```bash
curl http://localhost:8000/summary/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

---

### 3. Generate a PDF report

```bash
curl -X POST http://localhost:8000/report/ \
  -H "Content-Type: application/json" \
  -d '{"file_id": "3fa85f64-...", "format": "pdf", "title": "Q4 Sales Report"}' \
  --output report.pdf
```

### 4. Generate an Excel report

```bash
curl -X POST http://localhost:8000/report/ \
  -H "Content-Type: application/json" \
  -d '{"file_id": "3fa85f64-...", "format": "excel"}' \
  --output report.xlsx
```

---

## 🧪 Running Tests

```bash
pytest -v
```

Run with coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

---

## ⚙️ Configuration

Set via environment variables or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Automated Report Generator` | Display name |
| `DEBUG` | `false` | Enable debug logging |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum upload file size |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.115 |
| Data processing | pandas 2.2, NumPy 2.1 |
| PDF generation | ReportLab 4.2 |
| Excel generation | openpyxl 3.1 |
| Validation | Pydantic v2 |
| Testing | pytest, httpx |
| Containerisation | Docker, Docker Compose |

---

## 📄 License

MIT
