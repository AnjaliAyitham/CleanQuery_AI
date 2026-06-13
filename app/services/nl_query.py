import re
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.client import call_llm_structured
from app.llm.prompts import (
    EXPLAIN_RESULTS_SYSTEM,
    EXPLAIN_RESULTS_USER,
    NL_TO_SQL_SYSTEM,
    NL_TO_SQL_USER,
)
from app.llm.response_models import GeneratedQuery, QueryExplanation
from app.models.query_log import QueryAuditLog


async def build_schema_context(db: AsyncSession) -> str:
    result = await db.execute(text("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name LIKE 'data_%'
        ORDER BY table_name, ordinal_position
    """))
    rows = result.fetchall()

    tables: dict[str, list[str]] = {}
    for row in rows:
        table = row[0]
        col_info = f"  - {row[1]} ({row[2]})"
        tables.setdefault(table, []).append(col_info)

    context_parts = []
    for table, columns in tables.items():
        context_parts.append(f"Table: {table}\nColumns:\n" + "\n".join(columns))

    return "\n\n".join(context_parts) if context_parts else "No data tables available."


def validate_sql(sql: str) -> bool:
    normalized = sql.strip().upper()
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
    first_keyword = re.split(r"\s+", normalized)[0] if normalized else ""
    if first_keyword not in ("SELECT", "WITH"):
        return False
    for keyword in dangerous:
        if re.search(rf"\b{keyword}\b", normalized):
            return False
    return True


async def generate_and_execute(
    db: AsyncSession,
    question: str,
) -> dict:
    schema_context = await build_schema_context(db)

    prompt = NL_TO_SQL_USER.format(
        schema_context=schema_context,
        question=question,
    )

    generated = await call_llm_structured(
        prompt=prompt,
        response_model=GeneratedQuery,
        system=NL_TO_SQL_SYSTEM,
    )

    if not validate_sql(generated.sql):
        audit = QueryAuditLog(
            natural_language_query=question,
            generated_sql=generated.sql,
            status="rejected",
            error_message="Generated SQL contains unsafe operations",
            model_used=settings.openai_model,
        )
        db.add(audit)
        await db.commit()
        raise ValueError("Generated SQL contains unsafe operations and was rejected")

    start = time.time()
    try:
        await db.execute(text(f"SET LOCAL statement_timeout = '{settings.query_timeout_seconds}s'"))
        result = await db.execute(text(generated.sql))
        rows = [dict(row._mapping) for row in result.fetchmany(settings.query_max_rows)]
        elapsed_ms = int((time.time() - start) * 1000)

        results_preview = str(rows[:10]) if rows else "No results"
        explain_prompt = EXPLAIN_RESULTS_USER.format(
            question=question,
            row_count=len(rows),
            results_preview=results_preview,
        )
        explanation = await call_llm_structured(
            prompt=explain_prompt,
            response_model=QueryExplanation,
            system=EXPLAIN_RESULTS_SYSTEM,
            model=settings.openai_model_fast,
        )

        audit = QueryAuditLog(
            natural_language_query=question,
            generated_sql=generated.sql,
            execution_time_ms=elapsed_ms,
            row_count=len(rows),
            status="success",
            explanation=explanation.summary,
            model_used=settings.openai_model,
        )
        db.add(audit)
        await db.commit()
        await db.refresh(audit)

        return {
            "id": str(audit.id),
            "question": question,
            "generated_sql": generated.sql,
            "explanation": explanation.summary,
            "key_findings": explanation.key_findings,
            "tables_used": generated.tables_used,
            "assumptions": generated.assumptions,
            "results": rows,
            "row_count": len(rows),
            "execution_time_ms": elapsed_ms,
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        audit = QueryAuditLog(
            natural_language_query=question,
            generated_sql=generated.sql,
            execution_time_ms=elapsed_ms,
            status="error",
            error_message=str(e),
            model_used=settings.openai_model,
        )
        db.add(audit)
        await db.commit()
        raise
