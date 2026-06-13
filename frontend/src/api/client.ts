import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

export async function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/ingestion/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getDatasets() {
  const { data } = await api.get('/ingestion/datasets')
  return data
}

export async function getDataset(id: string) {
  const { data } = await api.get(`/ingestion/datasets/${id}`)
  return data
}

export async function triggerMapping(id: string) {
  const { data } = await api.post(`/ingestion/datasets/${id}/map`)
  return data
}

export async function approveMapping(id: string, mappings: unknown[], tableName: string) {
  const { data } = await api.put(`/ingestion/datasets/${id}/map`, {
    mappings,
    table_name: tableName,
  })
  return data
}

export async function previewDataset(id: string) {
  const { data } = await api.get(`/ingestion/datasets/${id}/preview`)
  return data
}

export async function detectAnomalies(datasetId: string) {
  const { data } = await api.post(`/anomaly/datasets/${datasetId}/detect`)
  return data
}

export async function healDataset(datasetId: string) {
  const { data } = await api.post(`/anomaly/datasets/${datasetId}/heal`)
  return data
}

export async function getLineage(datasetId: string) {
  const { data } = await api.get(`/anomaly/datasets/${datasetId}/lineage`)
  return data
}

export async function exportCleanedCsv(datasetId: string) {
  const response = await api.get(`/anomaly/datasets/${datasetId}/export`, {
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  const disposition = response.headers['content-disposition']
  const filename = disposition?.match(/filename="(.+)"/)?.[1] || 'cleaned_data.csv'
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function processFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/cleanse/process', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function analyzeFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/cleanse/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function downloadReport(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/cleanse/report', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  const name = file.name.replace(/\.[^.]+$/, '') + '_report.pdf'
  link.setAttribute('download', name)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function downloadCleanedCsv(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/cleanse/clean-export', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  const name = file.name.replace(/\.[^.]+$/, '') + '_cleaned.csv'
  link.setAttribute('download', name)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function askQuestion(question: string) {
  const { data } = await api.post('/query/ask', { question })
  return data
}

export async function getQueryHistory() {
  const { data } = await api.get('/query/history')
  return data
}

export async function getSchemaContext() {
  const { data } = await api.get('/query/schema-context')
  return data
}

export default api
