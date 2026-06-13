import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Upload as UploadIcon, FileUp, Check, Loader2 } from 'lucide-react'
import { uploadFile, getDatasets, triggerMapping } from '../api/client'
import type { Dataset } from '../types'

export default function UploadPage() {
  const queryClient = useQueryClient()
  const [mappingResult, setMappingResult] = useState<unknown>(null)

  const { data: datasets = [] } = useQuery<Dataset[]>({
    queryKey: ['datasets'],
    queryFn: getDatasets,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadFile(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['datasets'] }),
  })

  const mapMutation = useMutation({
    mutationFn: (id: string) => triggerMapping(id),
    onSuccess: (data) => {
      setMappingResult(data)
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
    },
  })

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => {
      if (files[0]) uploadMutation.mutate(files[0])
    },
    accept: { 'text/csv': ['.csv'], 'application/json': ['.json'] },
    maxFiles: 1,
  })

  return (
    <div className="max-w-4xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Upload Data</h2>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-indigo-400'
        }`}
      >
        <input {...getInputProps()} />
        <FileUp className="mx-auto mb-4 text-gray-400" size={48} />
        {uploadMutation.isPending ? (
          <p className="text-gray-600">Uploading...</p>
        ) : isDragActive ? (
          <p className="text-indigo-600 font-medium">Drop the file here</p>
        ) : (
          <div>
            <p className="text-gray-600 mb-1">Drag & drop a CSV or JSON file here</p>
            <p className="text-sm text-gray-400">or click to browse</p>
          </div>
        )}
      </div>

      {uploadMutation.isSuccess && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
          <Check size={16} className="text-green-600" />
          <span className="text-green-700 text-sm">File uploaded successfully</span>
        </div>
      )}

      {datasets.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Datasets</h3>
          <div className="space-y-3">
            {datasets.map((ds) => (
              <div key={ds.id} className="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{ds.name}</p>
                  <p className="text-sm text-gray-500">
                    {ds.source_type} &middot; {ds.row_count ?? '?'} rows &middot; {ds.column_count ?? '?'} cols
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    ds.status === 'ready' ? 'bg-green-100 text-green-700' :
                    ds.status === 'ingested' ? 'bg-blue-100 text-blue-700' :
                    ds.status === 'mapped' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {ds.status}
                  </span>
                  {ds.status === 'pending' && (
                    <button
                      onClick={() => mapMutation.mutate(ds.id)}
                      disabled={mapMutation.isPending}
                      className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1"
                    >
                      {mapMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <UploadIcon size={14} />}
                      Map Schema
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {mappingResult && (
        <div className="mt-8 bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Schema Mapping Result</h3>
          <pre className="bg-gray-50 p-4 rounded text-sm overflow-auto max-h-96">
            {JSON.stringify(mappingResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
