import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.llm.response_models import ColumnMappingItem, SchemaMappingResponse
from app.models.dataset import Dataset
from app.schemas.ingestion import (
    DatasetDetailResponse,
    DatasetResponse,
    MappingApproval,
)
from app.services.ingestion import create_dataset, materialize_table, save_mapping
from app.services.schema_mapper import map_schema
from app.utils.file_parser import get_sample_rows, parse_file

router = APIRouter()


@router.post("/upload", response_model=DatasetResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    filename = file.filename or "unknown"

    try:
        df = parse_file(filename, content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    dataset = await create_dataset(
        db=db,
        name=filename.rsplit(".", 1)[0],
        source_type=filename.rsplit(".", 1)[-1] if "." in filename else "unknown",
        filename=filename,
        df=df,
    )
    return dataset


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return result.scalars().all()


@router.get("/datasets/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset(dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Dataset)
        .options(selectinload(Dataset.column_mappings))
        .where(Dataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/datasets/{dataset_id}/map")
async def trigger_mapping(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    content = None
    if dataset.original_filename:
        import os

        upload_path = os.path.join("uploads", str(dataset.id), dataset.original_filename)
        if os.path.exists(upload_path):
            with open(upload_path, "rb") as f:
                content = f.read()

    if content is None:
        raise HTTPException(status_code=400, detail="Original file not available for re-mapping")

    df = parse_file(dataset.original_filename, content)
    mapping = await map_schema(df)

    await save_mapping(db, dataset, mapping)
    return {
        "dataset_id": str(dataset_id),
        "mapping": mapping.model_dump(),
        "preview": get_sample_rows(df),
    }


@router.put("/datasets/{dataset_id}/map")
async def approve_mapping(
    dataset_id: uuid.UUID,
    approval: MappingApproval,
    db: AsyncSession = Depends(get_db),
):
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    mapping = SchemaMappingResponse(
        mappings=[
            ColumnMappingItem(
                source_column=m.source_column,
                target_column=m.target_column,
                target_type=m.target_type,
                transformation=m.transformation,
                confidence=m.confidence or 1.0,
            )
            for m in approval.mappings
        ],
        suggested_table_name=approval.table_name,
        notes=[],
    )

    import os

    upload_path = os.path.join("uploads", str(dataset.id), dataset.original_filename or "")
    if not os.path.exists(upload_path):
        raise HTTPException(status_code=400, detail="Original file not available")

    with open(upload_path, "rb") as f:
        content = f.read()

    df = parse_file(dataset.original_filename or "", content)
    row_count = await materialize_table(db, dataset, mapping, df)

    return {"dataset_id": str(dataset_id), "status": "ingested", "row_count": row_count}


@router.get("/datasets/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.target_table_name:
        raise HTTPException(status_code=400, detail="Dataset not yet ingested")

    from sqlalchemy import text

    result = await db.execute(
        text(f'SELECT * FROM "{dataset.target_table_name}" LIMIT :limit'),
        {"limit": limit},
    )
    columns = list(result.keys())
    rows = [dict(row._mapping) for row in result]
    return {"dataset_id": str(dataset_id), "columns": columns, "rows": rows, "count": len(rows)}
