import pytest
from unittest.mock import AsyncMock, patch

from app.llm.response_models import (
    AnomalyClassificationResponse,
    ColumnMappingItem,
    GeneratedQuery,
    QueryExplanation,
    SchemaMappingResponse,
)


@pytest.fixture
def mock_schema_mapping():
    return SchemaMappingResponse(
        mappings=[
            ColumnMappingItem(
                source_column="Order ID",
                target_column="order_id",
                target_type="integer",
                transformation=None,
                confidence=0.95,
            ),
            ColumnMappingItem(
                source_column="Product Name",
                target_column="product_name",
                target_type="text",
                transformation=None,
                confidence=0.98,
            ),
            ColumnMappingItem(
                source_column="Sale Date",
                target_column="sale_date",
                target_type="date",
                transformation="parse_date(%Y-%m-%d)",
                confidence=0.85,
            ),
            ColumnMappingItem(
                source_column="Amount",
                target_column="amount",
                target_type="float",
                transformation="strip_currency($)",
                confidence=0.90,
            ),
        ],
        suggested_table_name="sales",
        notes=["Mixed date formats detected in Sale Date column"],
    )


@pytest.fixture
def mock_generated_query():
    return GeneratedQuery(
        sql="SELECT region, SUM(amount) as total_sales FROM data_sales GROUP BY region",
        explanation="This query calculates total sales grouped by region.",
        tables_used=["data_sales"],
        assumptions=["'amount' represents sales value in USD"],
    )


@pytest.fixture
def mock_openai_client():
    with patch("app.llm.client.get_openai_client") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client
