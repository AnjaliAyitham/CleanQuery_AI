import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import {
  Upload,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Download,
  FileDown,
  X,
  Zap,
  ArrowRight,
  BarChart3,
  TrendingUp,
  Link2,
  Lightbulb,
  Wrench,
  Table,
  History,
  Gauge,
  Clock,
  AlertCircle,
} from 'lucide-react'
import { analyzeFile, downloadReport, downloadCleanedCsv } from '../api/client'

interface ColumnStat {
  name: string
  dtype: string
  null_count: number
  null_pct: number
  unique_count: number
  mean?: number
  median?: number
  std?: number
  min?: number
  max?: number
  outlier_count?: number
  top_values?: Record<string, number>
}

interface Correlation {
  column_1: string
  column_2: string
  correlation?: number
  cramers_v?: number
  strength: string
  direction?: string
}

interface AnalysisResult {
  filename: string
  raw_kpis: Record<string, number>
  clean_kpis: Record<string, number>
  cleaning_log: { action: string; detail: string }[]
  column_stats: ColumnStat[]
  relationships: {
    strong_correlations: Correlation[]
    categorical_associations: Correlation[]
    numeric_categorical: { categorical: string; numeric: string; eta_squared: number; effect: string }[]
  }
  insights: string[]
}

interface HistoryEntry {
  filename: string
  timestamp: string
  qualityScore: number
  rows: number
  columns: number
}

function computeQualityScore(result: AnalysisResult): number {
  const { raw_kpis, clean_kpis, column_stats, cleaning_log } = result
  let score = 100

  const nullPenalty = column_stats.reduce((sum, c) => sum + c.null_pct, 0) / column_stats.length
  score -= nullPenalty * 0.5

  const issueRatio = cleaning_log.length / Math.max(raw_kpis.row_count, 1)
  score -= Math.min(issueRatio * 100, 20)

  const rowLoss = ((raw_kpis.row_count - clean_kpis.row_count) / Math.max(raw_kpis.row_count, 1)) * 100
  score -= rowLoss * 0.3

  const outlierCols = column_stats.filter(c => (c.outlier_count || 0) > 0).length
  score -= outlierCols * 2

  return Math.max(0, Math.min(100, Math.round(score)))
}

function getColumnRecommendations(stats: ColumnStat[]): { column: string; type: 'warning' | 'suggestion' | 'fix'; message: string }[] {
  const recs: { column: string; type: 'warning' | 'suggestion' | 'fix'; message: string }[] = []

  for (const col of stats) {
    if (col.null_pct > 30) {
      recs.push({ column: col.name, type: 'warning', message: `${col.null_pct.toFixed(1)}% null values — consider dropping or imputing` })
    } else if (col.null_pct > 5) {
      recs.push({ column: col.name, type: 'suggestion', message: `${col.null_pct.toFixed(1)}% nulls — fill with median/mode or flag as missing` })
    }

    if (col.unique_count === 1) {
      recs.push({ column: col.name, type: 'fix', message: 'Only 1 unique value — column adds no information, consider removing' })
    }

    if ((col.outlier_count || 0) > 0) {
      recs.push({ column: col.name, type: 'warning', message: `${col.outlier_count} outliers detected — review for data entry errors` })
    }

    if (col.dtype === 'object' && col.unique_count > 100) {
      recs.push({ column: col.name, type: 'suggestion', message: 'High cardinality text column — consider encoding or grouping rare values' })
    }

    const nameIssues = /^(unnamed|column|col)\s*\d*$/i.test(col.name) || /^\s|\s$/.test(col.name)
    if (nameIssues) {
      recs.push({ column: col.name, type: 'fix', message: 'Non-descriptive or malformed column name — rename for clarity' })
    }
  }

  return recs
}

export default function DataCleansingPage() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<'idle' | 'processing' | 'done' | 'error'>('idle')
  const [progress, setProgress] = useState(0)
  const [progressLabel, setProgressLabel] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState<'pdf' | 'csv' | null>(null)
  const [activeSection, setActiveSection] = useState<string>('insights')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem('datadlc_history')
    if (stored) setHistory(JSON.parse(stored))
  }, [])

  const addToHistory = (res: AnalysisResult) => {
    const entry: HistoryEntry = {
      filename: res.filename,
      timestamp: new Date().toISOString(),
      qualityScore: computeQualityScore(res),
      rows: res.raw_kpis.row_count,
      columns: res.raw_kpis.column_count,
    }
    const updated = [entry, ...history].slice(0, 20)
    setHistory(updated)
    localStorage.setItem('datadlc_history', JSON.stringify(updated))
  }

  const reset = () => {
    setFile(null)
    setStatus('idle')
    setProgress(0)
    setResult(null)
    setError('')
    setActiveSection('insights')
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const f = acceptedFiles[0]
    if (!f) return

    setFile(f)
    setStatus('processing')
    setError('')
    setResult(null)

    // Animated progress steps
    const steps = [
      { pct: 15, label: 'Parsing file...' },
      { pct: 35, label: 'Cleaning data...' },
      { pct: 55, label: 'Analyzing columns...' },
      { pct: 75, label: 'Finding relationships...' },
      { pct: 90, label: 'Generating insights...' },
    ]

    let stepIdx = 0
    const interval = setInterval(() => {
      if (stepIdx < steps.length) {
        setProgress(steps[stepIdx].pct)
        setProgressLabel(steps[stepIdx].label)
        stepIdx++
      }
    }, 800)

    try {
      const data = await analyzeFile(f)
      clearInterval(interval)
      setProgress(100)
      setProgressLabel('Complete!')
      await pause(500)
      setResult(data)
      addToHistory(data)
      setStatus('done')
    } catch (err: unknown) {
      clearInterval(interval)
      setStatus('error')
      setError(err instanceof Error ? err.message : 'Analysis failed')
    }
  }, [])

  const handleDownloadPdf = async () => {
    if (!file) return
    setDownloading('pdf')
    try { await downloadReport(file) } catch (e) { console.error(e) }
    setDownloading(null)
  }

  const handleDownloadCsv = async () => {
    if (!file) return
    setDownloading('csv')
    try { await downloadCleanedCsv(file) } catch (e) { console.error(e) }
    setDownloading(null)
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/json': ['.json'],
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    disabled: status === 'processing',
  })

  return (
    <div className="min-h-screen -m-8 bg-[#E8F4FD]">
      <div className="max-w-4xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="text-center mb-10">
          <motion.img
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
            src="https://edge.sitecorecloud.io/perficienti28ad-prft2d8b-prod513c-63c8/media/project/perficient-public/prft-public-site/logos/perficient/logo_perficient_full-color_registered-300.svg?iar=0"
            alt="Perficient"
            className="h-9 w-auto mx-auto mb-5"
          />
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#1B365D]/5 border border-[#1B365D]/10 mb-4"
          >
            <Sparkles size={13} className="text-[#E87722]" />
            <span className="text-xs text-[#1B365D] font-medium">AI-Powered Data Analysis</span>
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="text-3xl font-bold text-[#1B365D] mb-2"
          >
            Upload. Analyze. Download.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="text-[#1B365D]/60 text-base max-w-lg mx-auto"
          >
            Drop your CSV or Excel file — our AI agents clean it, find relationships, and generate a complete KPI report as PDF.
          </motion.p>
        </div>

        {/* History Toggle */}
        {history.length > 0 && (
          <div className="mb-6">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-[#1B365D]/10 text-[#1B365D]/70 hover:text-[#1B365D] text-sm transition-colors shadow-sm"
            >
              <History size={14} />
              Recent Analyses ({history.length})
            </button>

            <AnimatePresence>
              {showHistory && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-3 rounded-xl bg-white border border-[#1B365D]/10 shadow-sm overflow-hidden"
                >
                  <div className="p-4 space-y-2 max-h-60 overflow-y-auto">
                    {history.map((entry, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-[#E8F4FD]/50 hover:bg-[#E8F4FD]">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                            entry.qualityScore >= 80 ? 'bg-green-500' : entry.qualityScore >= 60 ? 'bg-amber-500' : 'bg-red-500'
                          }`}>
                            {entry.qualityScore}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-[#1B365D]">{entry.filename}</p>
                            <p className="text-xs text-[#1B365D]/50">{entry.rows} rows · {entry.columns} cols</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-[#1B365D]/40">
                          <Clock size={11} />
                          {new Date(entry.timestamp).toLocaleDateString()}
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Upload / Processing / Results */}
        <AnimatePresence mode="wait">
          {status === 'idle' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20, transition: { duration: 0.2 } }}
              transition={{ duration: 0.6, delay: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <div
                {...getRootProps()}
                className={`relative rounded-2xl border-2 border-dashed p-14 text-center cursor-pointer transition-all duration-300 ${
                  isDragActive
                    ? 'border-[#1B365D] bg-white scale-[1.01] shadow-lg'
                    : 'border-[#1B365D]/20 bg-white hover:border-[#1B365D]/40 hover:shadow-md'
                }`}
              >
                <input {...getInputProps()} />
                <motion.div
                  className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-[#E8F4FD] border border-[#1B365D]/10 flex items-center justify-center"
                  animate={{ y: [0, -8, 0] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                >
                  <Upload size={28} className="text-[#1B365D]" />
                </motion.div>
                <h2 className="text-xl font-semibold text-[#1B365D] mb-2">
                  {isDragActive ? 'Drop it here!' : 'Drop your file here'}
                </h2>
                <p className="text-[#1B365D]/50 mb-5 text-sm">or click to browse</p>
                <div className="flex items-center justify-center gap-2">
                  {['.csv', '.xlsx', '.json', '.pdf'].map((ext, i) => (
                    <motion.span
                      key={ext}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: 0.7 + i * 0.1 }}
                      className="px-2.5 py-1 rounded-md bg-[#E8F4FD] border border-[#1B365D]/15 text-xs text-[#1B365D]/70 font-mono"
                    >
                      {ext}
                    </motion.span>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {status === 'processing' && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="rounded-2xl border border-[#1B365D]/10 bg-white p-10 text-center shadow-sm"
            >
              <motion.div
                className="w-16 h-16 mx-auto mb-5 rounded-full bg-[#E8F4FD] border border-[#1B365D]/10 flex items-center justify-center"
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
              >
                <Zap size={28} className="text-[#1B365D]" />
              </motion.div>
              <h2 className="text-lg font-semibold text-[#1B365D] mb-1">{progressLabel}</h2>
              <p className="text-[#1B365D]/50 text-sm mb-5">{file?.name}</p>

              {/* Progress bar */}
              <div className="max-w-sm mx-auto h-2 bg-[#1B365D]/10 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-[#E87722] rounded-full"
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
              </div>
              <p className="text-[#E87722] text-xs mt-2 font-mono font-medium">{progress}%</p>

              {/* Animated steps */}
              <div className="flex items-center justify-center gap-2 mt-6">
                {['Parse', 'Clean', 'Analyze', 'Relate', 'Insight'].map((step, i) => (
                  <motion.div
                    key={step}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium ${
                      progress > (i + 1) * 18
                        ? 'bg-green-500/10 text-green-600 border border-green-500/20'
                        : progress > i * 18
                        ? 'bg-[#E87722]/10 text-[#E87722] border border-[#E87722]/20'
                        : 'bg-[#1B365D]/5 text-[#1B365D]/40 border border-[#1B365D]/10'
                    }`}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                  >
                    {progress > (i + 1) * 18 ? <CheckCircle2 size={10} /> : null}
                    {step}
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {status === 'error' && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-2xl border border-red-500/20 bg-red-500/5 p-10 text-center"
            >
              <AlertTriangle size={36} className="text-red-500 mx-auto mb-3" />
              <h2 className="text-lg font-semibold text-[#1B365D] mb-2">Analysis Failed</h2>
              <p className="text-red-600 text-sm mb-5">{error}</p>
              <button onClick={reset} className="px-5 py-2 bg-[#E87722] hover:bg-[#E87722]/90 text-white rounded-lg text-sm transition-colors">
                Try Again
              </button>
            </motion.div>
          )}

          {status === 'done' && result && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="space-y-6"
            >
              {/* File info + Download buttons */}
              <div className="rounded-2xl border border-[#1B365D]/10 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center">
                      <CheckCircle2 size={20} className="text-green-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-[#1B365D] text-sm">{result.filename}</p>
                      <p className="text-xs text-[#1B365D]/50">
                        {result.raw_kpis.row_count} rows &middot; {result.raw_kpis.column_count} columns &middot; Analysis complete
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleDownloadPdf}
                      disabled={downloading === 'pdf'}
                      className="flex items-center gap-2 px-4 py-2 bg-[#1B365D] hover:bg-[#152a4a] text-white rounded-lg font-medium text-sm disabled:opacity-50 transition-colors"
                    >
                      {downloading === 'pdf' ? <Loader2 size={15} className="animate-spin" /> : <FileDown size={15} />}
                      Download PDF Report
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleDownloadCsv}
                      disabled={downloading === 'csv'}
                      className="flex items-center gap-2 px-4 py-2 bg-[#1B365D]/5 hover:bg-[#1B365D]/10 border border-[#1B365D]/15 text-[#1B365D] rounded-lg text-sm transition-colors disabled:opacity-50"
                    >
                      {downloading === 'csv' ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
                      Cleaned CSV
                    </motion.button>
                    <button onClick={reset} className="p-2 text-[#1B365D]/40 hover:text-[#1B365D] rounded-lg hover:bg-[#1B365D]/10 transition-colors">
                      <X size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Data Quality Score */}
              <QualityScoreCard score={computeQualityScore(result)} />

              {/* KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <KpiCard label="Rows Cleaned" before={result.raw_kpis.row_count} after={result.clean_kpis.row_count} icon={Table} delay={0} />
                <KpiCard label="Issues Fixed" value={result.cleaning_log.length} icon={Wrench} color="amber" delay={0.1} />
                <KpiCard label="Relationships Found" value={
                  result.relationships.strong_correlations.length +
                  result.relationships.categorical_associations.length +
                  result.relationships.numeric_categorical.length
                } icon={Link2} color="purple" delay={0.2} />
                <KpiCard label="Insights" value={result.insights.length} icon={Lightbulb} color="green" delay={0.3} />
              </div>

              {/* Tab Navigation */}
              <div className="flex items-center gap-1 p-1 rounded-lg bg-white border border-[#1B365D]/10 shadow-sm">
                {[
                  { id: 'insights', label: 'Insights', icon: Lightbulb },
                  { id: 'recommendations', label: 'Recommendations', icon: AlertCircle },
                  { id: 'cleaning', label: 'Cleaning Log', icon: Wrench },
                  { id: 'columns', label: 'Columns', icon: BarChart3 },
                  { id: 'relationships', label: 'Relationships', icon: Link2 },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveSection(tab.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                      activeSection === tab.id
                        ? 'bg-[#1B365D] text-white'
                        : 'text-[#1B365D]/60 hover:text-[#1B365D] hover:bg-[#E8F4FD]'
                    }`}
                  >
                    <tab.icon size={14} />
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeSection}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="rounded-2xl border border-[#1B365D]/10 bg-white p-6 shadow-sm"
                >
                  {activeSection === 'insights' && (
                    <div className="space-y-3">
                      {result.insights.map((insight, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className="flex items-start gap-3 p-3 rounded-lg bg-[#E8F4FD]/50 border border-[#1B365D]/5"
                        >
                          <span className="text-base leading-none mt-0.5">{insight.charAt(0)}</span>
                          <p className="text-sm text-[#1B365D]/80">{insight.substring(2)}</p>
                        </motion.div>
                      ))}
                    </div>
                  )}

                  {activeSection === 'recommendations' && (
                    <div className="space-y-3">
                      {(() => {
                        const recs = getColumnRecommendations(result.column_stats)
                        if (recs.length === 0) return <p className="text-[#1B365D]/50 text-sm">All columns look good — no recommendations at this time.</p>
                        return recs.map((rec, i) => (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.04 }}
                            className="flex items-start gap-3 p-3 rounded-lg bg-[#E8F4FD]/50 border border-[#1B365D]/5"
                          >
                            <span className={`shrink-0 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              rec.type === 'fix' ? 'bg-red-500/15 text-red-600'
                              : rec.type === 'warning' ? 'bg-amber-500/15 text-amber-600'
                              : 'bg-blue-500/15 text-blue-600'
                            }`}>
                              {rec.type}
                            </span>
                            <div>
                              <p className="text-sm font-medium text-[#1B365D] font-mono">{rec.column}</p>
                              <p className="text-xs text-[#1B365D]/60 mt-0.5">{rec.message}</p>
                            </div>
                          </motion.div>
                        ))
                      })()}
                    </div>
                  )}

                  {activeSection === 'cleaning' && (
                    <div className="space-y-2">
                      {result.cleaning_log.length === 0 ? (
                        <p className="text-gray-500 text-sm">No cleaning was needed — data was already clean.</p>
                      ) : (
                        result.cleaning_log.map((entry, i) => (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.04 }}
                            className="flex items-center gap-3 p-3 rounded-lg bg-[#E8F4FD]/50"
                          >
                            <span className="px-2 py-0.5 bg-[#E87722]/15 text-[#E87722] rounded text-[10px] font-mono shrink-0">
                              {entry.action}
                            </span>
                            <span className="text-sm text-[#1B365D]/70">{entry.detail}</span>
                          </motion.div>
                        ))
                      )}
                    </div>
                  )}

                  {activeSection === 'columns' && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead className="text-[#1B365D]/60 border-b border-[#1B365D]/10">
                          <tr>
                            <th className="px-3 py-2 text-left">Column</th>
                            <th className="px-3 py-2 text-left">Type</th>
                            <th className="px-3 py-2 text-left">Unique</th>
                            <th className="px-3 py-2 text-left">Nulls</th>
                            <th className="px-3 py-2 text-left">Mean / Top Value</th>
                            <th className="px-3 py-2 text-left">Outliers</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1B365D]/5">
                          {result.column_stats.map((col, i) => (
                            <motion.tr
                              key={col.name}
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              transition={{ delay: i * 0.02 }}
                              className="hover:bg-[#E8F4FD]/50"
                            >
                              <td className="px-3 py-2 text-[#1B365D] font-medium font-mono">{col.name}</td>
                              <td className="px-3 py-2">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                                  col.dtype.includes('float') || col.dtype.includes('int')
                                    ? 'bg-blue-500/15 text-blue-600'
                                    : 'bg-purple-500/15 text-purple-600'
                                }`}>
                                  {col.dtype}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-[#1B365D]/60">{col.unique_count}</td>
                              <td className="px-3 py-2 text-[#1B365D]/60">{col.null_count > 0 ? <span className="text-amber-600">{col.null_count}</span> : '0'}</td>
                              <td className="px-3 py-2 text-[#1B365D]/60 font-mono">
                                {col.mean != null ? col.mean.toFixed(1) : col.top_values ? Object.keys(col.top_values)[0] : '—'}
                              </td>
                              <td className="px-3 py-2">
                                {col.outlier_count != null ? (
                                  col.outlier_count > 0 ? (
                                    <span className="text-red-600">{col.outlier_count}</span>
                                  ) : (
                                    <span className="text-green-600">0</span>
                                  )
                                ) : '—'}
                              </td>
                            </motion.tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {activeSection === 'relationships' && (
                    <div className="space-y-4">
                      {result.relationships.strong_correlations.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-[#1B365D] mb-2 uppercase tracking-wide">Numeric Correlations</h4>
                          <div className="space-y-2">
                            {result.relationships.strong_correlations.map((r, i) => (
                              <motion.div
                                key={i}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.05 }}
                                className="flex items-center gap-3 p-3 rounded-lg bg-[#E8F4FD]/50"
                              >
                                <span className="text-sm text-[#1B365D] font-mono">{r.column_1}</span>
                                <ArrowRight size={12} className="text-[#1B365D]/50" />
                                <span className="text-sm text-[#1B365D] font-mono">{r.column_2}</span>
                                <span className={`ml-auto px-2 py-0.5 rounded text-xs font-medium ${
                                  r.strength === 'strong' ? 'bg-red-500/15 text-red-600' : 'bg-amber-500/15 text-amber-600'
                                }`}>
                                  r = {r.correlation}
                                </span>
                              </motion.div>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.relationships.categorical_associations.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-[#1B365D] mb-2 uppercase tracking-wide">Categorical Associations</h4>
                          <div className="space-y-2">
                            {result.relationships.categorical_associations.map((r, i) => (
                              <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-[#E8F4FD]/50">
                                <span className="text-sm text-[#1B365D] font-mono">{r.column_1}</span>
                                <Link2 size={12} className="text-purple-600" />
                                <span className="text-sm text-[#1B365D] font-mono">{r.column_2}</span>
                                <span className="ml-auto px-2 py-0.5 rounded text-xs bg-purple-500/15 text-purple-600">
                                  V = {r.cramers_v}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.relationships.numeric_categorical.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-[#1B365D] mb-2 uppercase tracking-wide">Category → Numeric Impact</h4>
                          <div className="space-y-2">
                            {result.relationships.numeric_categorical.map((r, i) => (
                              <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-[#E8F4FD]/50">
                                <span className="text-sm text-[#1B365D] font-mono">{r.categorical}</span>
                                <TrendingUp size={12} className="text-green-600" />
                                <span className="text-sm text-[#1B365D] font-mono">{r.numeric}</span>
                                <span className="ml-auto px-2 py-0.5 rounded text-xs bg-green-500/15 text-green-600">
                                  η² = {r.eta_squared} ({r.effect})
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {result.relationships.strong_correlations.length === 0 &&
                       result.relationships.categorical_associations.length === 0 &&
                       result.relationships.numeric_categorical.length === 0 && (
                        <p className="text-gray-500 text-sm">No significant relationships detected between columns.</p>
                      )}
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function KpiCard({
  label,
  value,
  before,
  after,
  icon: Icon,
  color = 'indigo',
  delay = 0,
}: {
  label: string
  value?: number
  before?: number
  after?: number
  icon: React.ComponentType<{ size?: number | string; className?: string }>
  color?: string
  delay?: number
}) {
  const colorMap: Record<string, string> = {
    indigo: 'bg-white border-[#1B365D]/10 text-[#1B365D]',
    amber: 'bg-white border-[#E87722]/20 text-[#E87722]',
    purple: 'bg-white border-purple-500/20 text-purple-600',
    green: 'bg-white border-green-500/20 text-green-600',
  }
  const colors = colorMap[color] || colorMap.indigo

  const parts = colors.split(' ')
  const bgClass = parts[0]
  const borderClass = parts[1]
  const iconClass = parts[2]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={{ y: -3, transition: { duration: 0.2 } }}
      className={`rounded-xl p-4 ${bgClass} border ${borderClass} shadow-sm hover:shadow-md transition-shadow`}
    >
      <Icon size={16} className={iconClass} />
      <p className="text-2xl font-bold text-[#1B365D] mt-2">
        {value != null ? value : before != null && after != null ? `${before} → ${after}` : '—'}
      </p>
      <p className="text-[11px] text-[#1B365D]/50 mt-0.5">{label}</p>
    </motion.div>
  )
}

function QualityScoreCard({ score }: { score: number }) {
  const color = score >= 80 ? '#16a34a' : score >= 60 ? '#d97706' : '#dc2626'
  const label = score >= 80 ? 'Excellent' : score >= 60 ? 'Needs Improvement' : 'Poor Quality'
  const circumference = 2 * Math.PI * 40

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-[#1B365D]/10 bg-white p-6 shadow-sm"
    >
      <div className="flex items-center gap-6">
        <div className="relative w-24 h-24 shrink-0">
          <svg className="w-24 h-24 -rotate-90" viewBox="0 0 96 96">
            <circle cx="48" cy="48" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
            <motion.circle
              cx="48" cy="48" r="40" fill="none" stroke={color} strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: circumference - (score / 100) * circumference }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl font-bold text-[#1B365D]">{score}</span>
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Gauge size={16} className="text-[#1B365D]" />
            <h3 className="font-semibold text-[#1B365D]">Data Quality Score</h3>
          </div>
          <p className="text-sm font-medium" style={{ color }}>{label}</p>
          <p className="text-xs text-[#1B365D]/50 mt-1">
            Based on null values, outliers, cleaning operations, and data loss
          </p>
        </div>
      </div>
    </motion.div>
  )
}

function pause(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
