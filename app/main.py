from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import anomaly, cleanse, ingestion, query

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["ingestion"])
app.include_router(anomaly.router, prefix="/api/v1/anomaly", tags=["anomaly"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
app.include_router(cleanse.router, prefix="/api/v1/cleanse", tags=["cleanse"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.app_name}
