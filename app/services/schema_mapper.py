import json

from app.config import settings
from app.llm.client import call_llm_structured
from app.llm.prompts import SCHEMA_MAPPING_SYSTEM, SCHEMA_MAPPING_USER
from app.llm.response_models import SchemaMappingResponse
from app.utils.file_parser import get_sample_rows

import pandas as pd


async def map_schema(df: pd.DataFrame) -> SchemaMappingResponse:
    columns = list(df.columns)
    sample_rows = get_sample_rows(df, n=settings.sample_rows_for_mapping)

    prompt = SCHEMA_MAPPING_USER.format(
        columns=json.dumps(columns),
        sample_count=len(sample_rows),
        sample_rows=json.dumps(sample_rows, indent=2, default=str),
    )

    return await call_llm_structured(
        prompt=prompt,
        response_model=SchemaMappingResponse,
        system=SCHEMA_MAPPING_SYSTEM,
    )
