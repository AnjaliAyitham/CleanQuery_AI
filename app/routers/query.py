from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.query_log import QueryAuditLog
from app.schemas.query import QueryHistoryItem, QueryRequest, SchemaContextResponse
from app.services.nl_query import build_schema_context, generate_and_execute

router = APIRouter()


@router.post("/ask")
async def ask_question(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await generate_and_execute(db, request.question)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {e}")


@router.get("/history", response_model=list[QueryHistoryItem])
async def get_query_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QueryAuditLog).order_by(QueryAuditLog.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/history/{query_id}")
async def get_query_detail(
    query_id: str,
    db: AsyncSession = Depends(get_db),
):
    import uuid

    result = await db.get(QueryAuditLog, uuid.UUID(query_id))
    if not result:
        raise HTTPException(status_code=404, detail="Query not found")
    return result


@router.get("/schema-context", response_model=SchemaContextResponse)
async def get_schema_context(db: AsyncSession = Depends(get_db)):
    context = await build_schema_context(db)
    tables = []
    if context != "No data tables available.":
        for block in context.split("\n\n"):
            lines = block.strip().split("\n")
            if lines:
                table_name = lines[0].replace("Table: ", "")
                columns = [l.strip("- ").strip() for l in lines[2:] if l.strip().startswith("-")]
                tables.append({"name": table_name, "columns": columns})
    return {"tables": tables}
