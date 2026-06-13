import json

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.client import call_llm_structured
from app.llm.prompts import ANOMALY_DETECTION_SYSTEM, ANOMALY_DETECTION_USER
from app.llm.response_models import AnomalyClassificationResponse, AnomalyItem
from app.models.dataset import Dataset


def detect_duplicates(df: pd.DataFrame) -> list[dict]:
    anomalies = []
    subset_cols = [c for c in df.columns if c not in ("id", "created_at", "updated_at")]
    duplicated_mask = df.duplicated(subset=subset_cols, keep="first")
    for idx in df[duplicated_mask].index.tolist():
        first_match = df[duplicated_mask == False][
            (df.loc[duplicated_mask == False, subset_cols] == df.loc[idx, subset_cols]).all(axis=1)
        ].index
        orig_idx = int(first_match[0]) if len(first_match) > 0 else 0
        anomalies.append({
            "row_index": int(idx),
            "column": "(all)",
            "original_value": f"Duplicate of row {orig_idx}",
            "anomaly_type": "duplicate",
            "severity": "medium",
            "suggested_fix": "Remove duplicate row",
            "confidence": 0.95,
        })
    return anomalies


def detect_statistical_anomalies(df: pd.DataFrame) -> list[dict]:
    anomalies = []

    for col in df.select_dtypes(include=[np.number]).columns:
        series = df[col].dropna()
        if len(series) < 10:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outliers = df[(df[col] < lower) | (df[col] > upper)]
        for idx, row in outliers.iterrows():
            anomalies.append({
                "row_index": int(idx),
                "column": col,
                "original_value": str(row[col]),
                "anomaly_type": "outlier",
                "severity": "medium",
            })

    for col in df.columns:
        null_pct = df[col].isna().sum() / len(df)
        if 0 < null_pct < 0.5:
            null_indices = df[df[col].isna()].index.tolist()[:10]
            for idx in null_indices:
                anomalies.append({
                    "row_index": int(idx),
                    "column": col,
                    "original_value": None,
                    "anomaly_type": "missing",
                    "severity": "low" if null_pct < 0.1 else "medium",
                })

    return anomalies


async def detect_format_anomalies_with_llm(
    df: pd.DataFrame,
    column_types: dict[str, str],
) -> AnomalyClassificationResponse:
    all_anomalies: list[AnomalyItem] = []

    for col, expected_type in column_types.items():
        if col not in df.columns:
            continue

        values = df[col].dropna().astype(str).tolist()
        if not values:
            continue

        sample_values = values[:50]
        prompt = ANOMALY_DETECTION_USER.format(
            column_name=col,
            expected_type=expected_type,
            values=json.dumps(sample_values[:20]),
            total_count=len(values),
            null_count=int(df[col].isna().sum()),
            unique_count=int(df[col].nunique()),
        )

        result = await call_llm_structured(
            prompt=prompt,
            response_model=AnomalyClassificationResponse,
            system=ANOMALY_DETECTION_SYSTEM,
            model=settings.openai_model_fast,
        )
        all_anomalies.extend(result.anomalies)

    return AnomalyClassificationResponse(
        anomalies=all_anomalies,
        summary=f"Found {len(all_anomalies)} format anomalies across {len(column_types)} columns",
    )


async def run_full_detection(
    db: AsyncSession,
    dataset: Dataset,
) -> AnomalyClassificationResponse:
    if not dataset.target_table_name:
        raise ValueError("Dataset not yet ingested")

    result = await db.execute(text(f'SELECT * FROM "{dataset.target_table_name}"'))
    rows = result.fetchall()
    columns = result.keys()
    df = pd.DataFrame(rows, columns=columns)

    duplicate_anomalies = detect_duplicates(df)
    stat_anomalies = detect_statistical_anomalies(df)

    from sqlalchemy import select
    from app.models.dataset import ColumnMapping

    mappings_result = await db.execute(
        select(ColumnMapping).where(ColumnMapping.dataset_id == dataset.id)
    )
    mappings = mappings_result.scalars().all()
    column_types = {m.target_column: m.target_type for m in mappings}

    llm_result = await detect_format_anomalies_with_llm(df, column_types)

    dup_items = [
        AnomalyItem(
            row_index=a["row_index"],
            column=a["column"],
            original_value=a["original_value"],
            anomaly_type=a["anomaly_type"],
            severity=a["severity"],
            suggested_fix=a["suggested_fix"],
            new_value=None,
            confidence=a["confidence"],
        )
        for a in duplicate_anomalies
    ]

    stat_items = [
        AnomalyItem(
            row_index=a["row_index"],
            column=a["column"],
            original_value=a["original_value"],
            anomaly_type=a["anomaly_type"],
            severity=a["severity"],
            suggested_fix=None,
            new_value=None,
            confidence=0.9,
        )
        for a in stat_anomalies
    ]

    all_anomalies = dup_items + stat_items + llm_result.anomalies
    return AnomalyClassificationResponse(
        anomalies=all_anomalies,
        summary=f"Found {len(all_anomalies)} total anomalies ({len(dup_items)} duplicates, {len(stat_items)} statistical, {len(llm_result.anomalies)} format)",
    )
