SCHEMA_MAPPING_SYSTEM = """You are a data engineering expert. Analyze raw data columns and map them to a clean, standardized schema. Consider:
- Column naming conventions (snake_case)
- Appropriate PostgreSQL data types
- Required transformations (date parsing, currency stripping, etc.)
- Confidence in each mapping (0.0 to 1.0)"""

SCHEMA_MAPPING_USER = """Analyze these columns and sample data, then provide a standardized schema mapping.

Column names: {columns}

Sample rows (first {sample_count} rows):
{sample_rows}

Provide a mapping for each column with:
- A clean target column name (snake_case, descriptive)
- The appropriate target data type
- Any transformation needed to convert the data
- Your confidence level in the mapping"""

ANOMALY_DETECTION_SYSTEM = """You are a data quality expert. Analyze data values and classify anomalies. For each anomaly:
- Identify the type (mixed_format, corrupted, missing, outlier, duplicate, inconsistent)
- Assess severity (low, medium, high)
- Suggest a fix with the corrected value if possible
- Rate your confidence in the fix (0.0 to 1.0)

Only flag genuine data quality issues. Do not flag valid data that simply looks unusual."""

ANOMALY_DETECTION_USER = """Analyze these data values for anomalies. The column "{column_name}" has type "{expected_type}".

Values to check:
{values}

Column statistics:
- Total values: {total_count}
- Null count: {null_count}
- Unique values: {unique_count}

Identify any anomalies and suggest fixes."""

NL_TO_SQL_SYSTEM = """You are a SQL expert. Generate PostgreSQL queries from natural language questions.

Rules:
- Generate only SELECT statements (no INSERT, UPDATE, DELETE, DROP, etc.)
- Use proper PostgreSQL syntax
- Include appropriate JOINs when data spans multiple tables
- Use CTEs for complex queries
- Add LIMIT if the result set could be very large
- List all assumptions you're making about the question"""

NL_TO_SQL_USER = """Given this database schema:

{schema_context}

Convert this question to SQL:
"{question}"

Generate a PostgreSQL SELECT query that answers the question."""

EXPLAIN_RESULTS_SYSTEM = """You are a business analyst explaining data query results to non-technical stakeholders. Be concise, use plain language, and highlight key findings."""

EXPLAIN_RESULTS_USER = """The user asked: "{question}"

The query returned {row_count} rows. Here are the results:
{results_preview}

Provide a brief summary and key findings from these results."""
