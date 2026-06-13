import io
import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.dataset import Dataset
from app.models.lineage import AnomalyReport, TransformationLog
from app.schemas.anomaly import AnomalyReportResponse, HealingResultResponse, LineageEntry
from app.services.anomaly_detector import run_full_detection
from app.services.self_healer import heal_dataset

router = APIRouter()


@router.post("/datasets/{dataset_id}/detect")
async def detect_anomalies(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.target_table_name:
        raise HTTPException(status_code=400, detail="Dataset not yet ingested")

    result = await run_full_detection(db, dataset)
    return {
        "dataset_id": str(dataset_id),
        "total_anomalies": len(result.anomalies),
        "summary": result.summary,
        "anomalies": [a.model_dump() for a in result.anomalies],
    }


@router.post("/datasets/{dataset_id}/heal", response_model=HealingResultResponse)
async def heal_anomalies(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    anomalies = await run_full_detection(db, dataset)
    result = await heal_dataset(db, dataset, anomalies)
    return result


@router.get("/datasets/{dataset_id}/anomalies")
async def get_anomaly_report(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnomalyReport)
        .where(AnomalyReport.dataset_id == dataset_id)
        .order_by(AnomalyReport.created_at.desc())
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="No anomaly report found")
    return report


@router.get("/datasets/{dataset_id}/lineage", response_model=list[LineageEntry])
async def get_lineage(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TransformationLog)
        .where(TransformationLog.dataset_id == dataset_id)
        .order_by(TransformationLog.created_at.desc())
    )
    return result.scalars().all()


@router.get("/datasets/{dataset_id}/export")
async def export_cleaned_csv(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.target_table_name:
        raise HTTPException(status_code=400, detail="Dataset not yet ingested")

    result = await db.execute(text(f'SELECT * FROM "{dataset.target_table_name}"'))
    rows = result.fetchall()
    columns = list(result.keys())
    df = pd.DataFrame(rows, columns=columns)

    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    filename = f"{dataset.filename.rsplit('.', 1)[0]}_cleaned.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
