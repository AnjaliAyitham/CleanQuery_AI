import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Activity, Zap, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { getDatasets, detectAnomalies, healDataset } from '../api/client'
import type { Dataset, AnomalyReport } from '../types'

const COLORS = ['#ef4444', '#f59e0b', '#22c55e', '#6366f1', '#ec4899']

export default function PipelinePage() {
  const queryClient = useQueryClient()
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null)
  const [anomalyReport, setAnomalyReport] = useState<AnomalyReport | null>(null)

  const { data: datasets = [] } = useQuery<Dataset[]>({
    queryKey: ['datasets'],
    queryFn: getDatasets,
  })

  const detectMutation = useMutation({
    mutationFn: (id: string) => detectAnomalies(id),
    onSuccess: (data) => setAnomalyReport(data),
  })

  const healMutation = useMutation({
    mutationFn: (id: string) => healDataset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
      setAnomalyReport(null)
    },
  })

  const ingestedDatasets = datasets.filter(d => d.status === 'ingested' || d.status === 'ready')

  const anomalyByType = anomalyReport?.anomalies.reduce((acc, a) => {
    acc[a.anomaly_type] = (acc[a.anomaly_type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const pieData = anomalyByType
    ? Object.entries(anomalyByType).map(([name, value]) => ({ name, value }))
    : []

  const severityData = anomalyReport?.anomalies.reduce((acc, a) => {
    acc[a.severity] = (acc[a.severity] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const barData = severityData
    ? Object.entries(severityData).map(([name, count]) => ({ name, count }))
    : []

  return (
    <div className="max-w-5xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Pipeline Status</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {ingestedDatasets.map((ds) => (
          <div
            key={ds.id}
            onClick={() => setSelectedDataset(ds.id)}
            className={`bg-white border rounded-lg p-4 cursor-pointer transition-all ${
              selectedDataset === ds.id ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <Activity size={16} className="text-indigo-500" />
              <span className="font-medium text-gray-900">{ds.name}</span>
            </div>
            <p className="text-sm text-gray-500">{ds.row_count} rows</p>
            <span className={`mt-2 inline-block px-2 py-0.5 rounded text-xs font-medium ${
              ds.status === 'ready' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
            }`}>
              {ds.status}
            </span>
          </div>
        ))}
      </div>

      {selectedDataset && (
        <div className="flex gap-3 mb-6">
          <button
            onClick={() => detectMutation.mutate(selectedDataset)}
            disabled={detectMutation.isPending}
            className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 flex items-center gap-2"
          >
            {detectMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <AlertTriangle size={16} />}
            Detect Anomalies
          </button>
          <button
            onClick={() => healMutation.mutate(selectedDataset)}
            disabled={healMutation.isPending}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
          >
            {healMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
            Auto-Heal
          </button>
        </div>
      )}

      {healMutation.isSuccess && (
        <div className="mb-6 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
          <CheckCircle size={16} className="text-green-600" />
          <span className="text-green-700 text-sm">Dataset healed successfully</span>
        </div>
      )}

      {anomalyReport && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            Anomaly Report ({anomalyReport.total_anomalies} found)
          </h3>
          <p className="text-sm text-gray-600 mb-6">{anomalyReport.summary}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {pieData.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">By Type</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                      {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
            {barData.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">By Severity</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={barData}>
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-2">Row</th>
                  <th className="text-left p-2">Column</th>
                  <th className="text-left p-2">Type</th>
                  <th className="text-left p-2">Severity</th>
                  <th className="text-left p-2">Original</th>
                  <th className="text-left p-2">Fix</th>
                  <th className="text-left p-2">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {anomalyReport.anomalies.slice(0, 50).map((a, i) => (
                  <tr key={i} className="border-t border-gray-100">
                    <td className="p-2">{a.row_index}</td>
                    <td className="p-2 font-mono text-xs">{a.column}</td>
                    <td className="p-2">{a.anomaly_type}</td>
                    <td className="p-2">
                      <span className={`px-1.5 py-0.5 rounded text-xs ${
                        a.severity === 'high' ? 'bg-red-100 text-red-700' :
                        a.severity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>{a.severity}</span>
                    </td>
                    <td className="p-2 font-mono text-xs">{a.original_value ?? 'NULL'}</td>
                    <td className="p-2 font-mono text-xs text-green-700">{a.new_value ?? '-'}</td>
                    <td className="p-2">{(a.confidence * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
