import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Send, Loader2, Code, ChevronDown, ChevronUp, Download } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { askQuestion, getSchemaContext } from '../api/client'
import type { QueryResult } from '../types'

export default function QueryPage() {
  const [question, setQuestion] = useState('')
  const [showSql, setShowSql] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)

  const { data: schemaCtx } = useQuery({
    queryKey: ['schema-context'],
    queryFn: getSchemaContext,
  })

  const queryMutation = useMutation({
    mutationFn: (q: string) => askQuestion(q),
    onSuccess: (data) => setResult(data),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (question.trim()) queryMutation.mutate(question.trim())
  }

  const handleDownload = () => {
    if (!result?.results.length) return
    const headers = Object.keys(result.results[0])
    const csv = [
      headers.join(','),
      ...result.results.map(row => headers.map(h => JSON.stringify(row[h] ?? '')).join(','))
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'query_results.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const numericColumns = result?.results.length
    ? Object.keys(result.results[0]).filter(k => typeof result.results[0][k] === 'number')
    : []

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Ask Your Data</h2>

      {schemaCtx?.tables?.length > 0 && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-700">
            Available tables: {schemaCtx.tables.map((t: { name: string }) => t.name).join(', ')}
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mb-8">
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your data... (e.g., 'What are total sales by region?')"
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
          />
          <button
            type="submit"
            disabled={queryMutation.isPending || !question.trim()}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
          >
            {queryMutation.isPending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            Ask
          </button>
        </div>
      </form>

      {queryMutation.isError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm">{(queryMutation.error as Error).message}</p>
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-800">Explanation</h3>
              <span className="text-xs text-gray-400">{result.execution_time_ms}ms &middot; {result.row_count} rows</span>
            </div>
            <p className="text-gray-700">{result.explanation}</p>
            {result.key_findings?.length > 0 && (
              <ul className="mt-3 space-y-1">
                {result.key_findings.map((f, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className="text-indigo-500 mt-0.5">&#8226;</span> {f}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="bg-white border border-gray-200 rounded-lg">
            <button
              onClick={() => setShowSql(!showSql)}
              className="w-full px-6 py-3 flex items-center justify-between text-left hover:bg-gray-50"
            >
              <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <Code size={16} /> Generated SQL
              </span>
              {showSql ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {showSql && (
              <pre className="px-6 pb-4 text-sm font-mono text-gray-800 overflow-auto bg-gray-50 mx-4 mb-4 p-4 rounded">
                {result.generated_sql}
              </pre>
            )}
          </div>

          {result.results.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-800">Results</h3>
                <button onClick={handleDownload} className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                  <Download size={14} /> CSV
                </button>
              </div>

              {numericColumns.length > 0 && result.results.length <= 20 && (
                <div className="mb-6">
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={result.results.slice(0, 20)}>
                      <XAxis dataKey={Object.keys(result.results[0]).find(k => typeof result.results[0][k] === 'string') || ''} />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey={numericColumns[0]} fill="#6366f1" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div className="overflow-auto max-h-96">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      {Object.keys(result.results[0]).map((key) => (
                        <th key={key} className="text-left p-2 font-medium text-gray-700">{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.results.slice(0, 100).map((row, i) => (
                      <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="p-2">{String(val ?? 'NULL')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {result.row_count > 100 && (
                <p className="mt-3 text-sm text-gray-500 text-center">Showing 100 of {result.row_count} rows</p>
              )}
            </div>
          )}

          {result.assumptions.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-yellow-800 mb-2">Assumptions Made</h4>
              <ul className="space-y-1">
                {result.assumptions.map((a, i) => (
                  <li key={i} className="text-sm text-yellow-700">&middot; {a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
