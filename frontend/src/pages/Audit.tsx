import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { History, ArrowRight, Clock } from 'lucide-react'
import { getQueryHistory, getDatasets, getLineage } from '../api/client'
import type { QueryHistoryItem, Dataset, LineageEntry } from '../types'

export default function AuditPage() {
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null)

  const { data: history = [] } = useQuery<QueryHistoryItem[]>({
    queryKey: ['query-history'],
    queryFn: getQueryHistory,
  })

  const { data: datasets = [] } = useQuery<Dataset[]>({
    queryKey: ['datasets'],
    queryFn: getDatasets,
  })

  const { data: lineage = [] } = useQuery<LineageEntry[]>({
    queryKey: ['lineage', selectedDataset],
    queryFn: () => getLineage(selectedDataset!),
    enabled: !!selectedDataset,
  })

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Audit & Lineage</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <History size={20} /> Query History
          </h3>
          <div className="space-y-3">
            {history.length === 0 && (
              <p className="text-sm text-gray-500">No queries yet.</p>
            )}
            {history.map((item) => (
              <div key={item.id} className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="font-medium text-gray-900 text-sm mb-1">{item.natural_language_query}</p>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span className={`px-1.5 py-0.5 rounded ${
                    item.status === 'success' ? 'bg-green-100 text-green-700' :
                    item.status === 'error' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{item.status}</span>
                  {item.execution_time_ms && <span>{item.execution_time_ms}ms</span>}
                  {item.row_count !== null && <span>{item.row_count} rows</span>}
                  <span className="flex items-center gap-1">
                    <Clock size={10} /> {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>
                {item.generated_sql && (
                  <pre className="mt-2 text-xs font-mono text-gray-600 bg-gray-50 p-2 rounded overflow-auto max-h-20">
                    {item.generated_sql}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <ArrowRight size={20} /> Transformation Lineage
          </h3>

          <select
            value={selectedDataset || ''}
            onChange={(e) => setSelectedDataset(e.target.value || null)}
            className="w-full mb-4 px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">Select a dataset...</option>
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id}>{ds.name}</option>
            ))}
          </select>

          {lineage.length > 0 ? (
            <div className="space-y-2 max-h-96 overflow-auto">
              {lineage.map((entry, i) => (
                <div key={i} className="bg-white border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">
                      {entry.anomaly_type}
                    </span>
                    <span className="text-xs text-gray-500">Row {entry.row_index} &middot; {entry.column_name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <code className="text-red-600 bg-red-50 px-1.5 py-0.5 rounded text-xs">
                      {entry.original_value ?? 'NULL'}
                    </code>
                    <ArrowRight size={12} className="text-gray-400" />
                    <code className="text-green-600 bg-green-50 px-1.5 py-0.5 rounded text-xs">
                      {entry.transformed_value ?? 'NULL'}
                    </code>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Strategy: {entry.fix_strategy} ({((entry.confidence ?? 0) * 100).toFixed(0)}%)</p>
                </div>
              ))}
            </div>
          ) : selectedDataset ? (
            <p className="text-sm text-gray-500">No transformations recorded for this dataset.</p>
          ) : null}
        </div>
      </div>
    </div>
  )
}
