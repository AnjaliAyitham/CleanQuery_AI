import uuid

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.response_models import SchemaMappingResponse
from app.models.dataset import ColumnMapping, Dataset

TYPE_MAP = {
    "text": "TEXT",
    "integer": "BIGINT",
    "float": "DOUBLE PRECISION",
    "date": "DATE",
    "timestamp": "TIMESTAMPTZ",
    "boolean": "BOOLEAN",
    "json": "JSONB",
}


async def create_dataset(
    db: AsyncSession,
    name: str,
    source_type: str,
    filename: str | None,
    df: pd.DataFrame,
) -> Dataset:
    dataset = Dataset(
        name=name,
        source_type=source_type,
        original_filename=filename,
        row_count=len(df),
        column_count=len(df.columns),
        status="pending",
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


async def save_mapping(
    db: AsyncSession,
    dataset: Dataset,
    mapping: SchemaMappingResponse,
) -> None:
    dataset.target_table_name = f"data_{mapping.suggested_table_name}"
    dataset.status = "mapped"

    for col_map in mapping.mappings:
        cm = ColumnMapping(
            dataset_id=dataset.id,
            source_column=col_map.source_column,
            target_column=col_map.target_column,
            source_type="inferred",
            target_type=col_map.target_type,
            transformation=col_map.transformation,
            confidence=col_map.confidence,
        )
        db.add(cm)

    await db.commit()


async def materialize_table(
    db: AsyncSession,
    dataset: Dataset,
    mapping: SchemaMappingResponse,
    df: pd.DataFrame,
) -> int:
    table_name = dataset.target_table_name
    columns_sql = []
    for col_map in mapping.mappings:
        pg_type = TYPE_MAP.get(col_map.target_type, "TEXT")
        columns_sql.append(f'"{col_map.target_column}" {pg_type}')

    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (id SERIAL PRIMARY KEY, {", ".join(columns_sql)})'
    await db.execute(text(create_sql))

    rename_map = {m.source_column: m.target_column for m in mapping.mappings}
    target_cols = [m.target_column for m in mapping.mappings]
    df_renamed = df.rename(columns=rename_map)[target_cols]

    rows = df_renamed.where(df_renamed.notna(), None).to_dict(orient="records")
    if not rows:
        return 0

    cols = ", ".join(f'"{c}"' for c in target_cols)
    placeholders = ", ".join(f":{c}" for c in target_cols)
    insert_sql = text(f'INSERT INTO "{table_name}" ({cols}) VALUES ({placeholders})')

    await db.execute(insert_sql, rows)
    dataset.status = "ingested"
    dataset.row_count = len(rows)
    await db.commit()
    return len(rows)
