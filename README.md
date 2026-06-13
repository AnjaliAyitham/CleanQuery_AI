# CleanQuery AI

End-to-end automated data engineering & analytics pipeline powered by LLMs.

## Architecture

Three-phase intelligent pipeline:

1. **Schema Mapping & Ingestion** — Upload CSVs/JSON, GPT auto-maps columns to a standardized schema
2. **Anomaly Detection & Self-Healing** — Statistical + LLM-based anomaly detection with auto-fix
3. **Natural Language Query** — Ask questions in plain English, get SQL + results + explanations

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (async)
- **Database:** PostgreSQL 16
- **LLM:** OpenAI GPT-4o / GPT-4o-mini
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, TanStack Query, Recharts

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- OpenAI API key

### 1. Start PostgreSQL

```bash
docker-compose up -d
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App

Navigate to http://localhost:5173

## API Endpoints

| Phase | Endpoint | Description |
|-------|----------|-------------|
| Ingestion | `POST /api/v1/ingestion/upload` | Upload CSV/JSON file |
| Ingestion | `POST /api/v1/ingestion/datasets/{id}/map` | Trigger schema mapping |
| Anomaly | `POST /api/v1/anomaly/datasets/{id}/detect` | Detect anomalies |
| Anomaly | `POST /api/v1/anomaly/datasets/{id}/heal` | Auto-heal data |
| Query | `POST /api/v1/query/ask` | Ask a natural language question |
| Query | `GET /api/v1/query/history` | Query audit trail |

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
cleanquery-ai/
├── app/                    # FastAPI backend
│   ├── llm/               # OpenAI client, prompts, response models
│   ├── models/            # SQLAlchemy ORM models
│   ├── routers/           # API endpoint handlers
│   ├── schemas/           # Pydantic request/response schemas
│   ├── services/          # Business logic (schema_mapper, anomaly_detector, nl_query)
│   └── utils/             # File parser, type detector
├── frontend/              # React + Vite + TypeScript
│   └── src/
│       ├── api/           # Axios API client
│       ├── pages/         # Upload, Pipeline, Query, Audit
│       └── types/         # TypeScript interfaces
├── tests/                 # Unit + integration tests
├── alembic/               # Database migrations
└── docker-compose.yml     # PostgreSQL
```
