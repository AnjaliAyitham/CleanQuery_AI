import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.response_models import AnomalyClassificationResponse
from app.models.dataset import Dataset
from app.models.lineage import AnomalyReport, TransformationLog

CONFIDENCE_THRESHOLD = 0.8


async def heal_dataset(
    db: AsyncSession,
    dataset: Dataset,
    anomalies: AnomalyClassificationResponse,
) -> dict:
    if not dataset.target_table_name:
        raise ValueError("Dataset not yet ingested")

    healed = 0
    skipped = 0
    details = []

    for anomaly in anomalies.anomalies:
        if anomaly.confidence < CONFIDENCE_THRESHOLD or not anomaly.new_value:
            skipped += 1
            details.append({
                "row_index": anomaly.row_index,
                "column": anomaly.column,
                "action": "skipped",
                "reason": "low confidence" if anomaly.confidence < CONFIDENCE_THRESHOLD else "no fix available",
            })
            continue

        update_sql = text(
            f'UPDATE "{dataset.target_table_name}" '
            f'SET "{anomaly.column}" = :new_value '
            f"WHERE ctid = (SELECT ctid FROM \"{dataset.target_table_name}\" OFFSET :row_idx LIMIT 1)"
        )
        await db.execute(update_sql, {"new_value": anomaly.new_value, "row_idx": anomaly.row_index})

        log_entry = TransformationLog(
            dataset_id=dataset.id,
            row_index=anomaly.row_index,
            column_name=anomaly.column,
            original_value=anomaly.original_value,
            transformed_value=anomaly.new_value,
            anomaly_type=anomaly.anomaly_type,
            fix_strategy=anomaly.suggested_fix or "auto",
            confidence=anomaly.confidence,
        )
        db.add(log_entry)
        healed += 1
        details.append({
            "row_index": anomaly.row_index,
            "column": anomaly.column,
            "action": "healed",
            "original": anomaly.original_value,
            "new_value": anomaly.new_value,
        })

    report = AnomalyReport(
        dataset_id=dataset.id,
        total_anomalies=len(anomalies.anomalies),
        auto_fixed=healed,
        requires_review=skipped,
        report_json={"details": details, "summary": anomalies.summary},
    )
    db.add(report)

    dataset.status = "ready"
    await db.commit()

    return {
        "dataset_id": str(dataset.id),
        "total_healed": healed,
        "skipped": skipped,
        "details": details,
    }
