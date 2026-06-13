export interface Dataset {
  id: string
  name: string
  source_type: string
  original_filename: string | null
  row_count: number | null
  column_count: number | null
  target_table_name: string | null
  status: string
}

export interface ColumnMapping {
  source_column: string
  target_column: string
  target_type: string
  transformation: string | null
  confidence: number | null
}

export interface DatasetDetail extends Dataset {
  column_mappings: ColumnMapping[]
}

export interface AnomalyItem {
  row_index: number
  column: string
  original_value: string | null
  anomaly_type: string
  severity: string
  suggested_fix: string | null
  new_value: string | null
  confidence: number
}

export interface AnomalyReport {
  dataset_id: string
  total_anomalies: number
  summary: string
  anomalies: AnomalyItem[]
}

export interface HealingResult {
  dataset_id: string
  total_healed: number
  skipped: number
  details: Record<string, unknown>[]
}

export interface QueryResult {
  id: string
  question: string
  generated_sql: string
  explanation: string
  key_findings: string[]
  tables_used: string[]
  assumptions: string[]
  results: Record<string, unknown>[]
  row_count: number
  execution_time_ms: number
}

export interface QueryHistoryItem {
  id: string
  natural_language_query: string
  generated_sql: string | null
  status: string
  row_count: number | null
  execution_time_ms: number | null
  explanation: string | null
  created_at: string
}

export interface LineageEntry {
  row_index: number | null
  column_name: string
  original_value: string | null
  transformed_value: string | null
  anomaly_type: string
  fix_strategy: string
  confidence: number | null
}
