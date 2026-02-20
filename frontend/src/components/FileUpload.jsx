import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'

export default function FileUpload({ onUploadStart, onProcessing, onResults, onError, status }) {
    const [fileName, setFileName] = useState(null)

    const onDrop = useCallback(
        async (acceptedFiles) => {
            if (acceptedFiles.length === 0) return
            const file = acceptedFiles[0]

            if (!file.name.toLowerCase().endsWith('.csv')) {
                onError('Only CSV files are accepted.')
                return
            }

            setFileName(file.name)
            onUploadStart()

            const formData = new FormData()
            formData.append('file', file)

            try {
                onProcessing()
                const API_URL = import.meta.env.VITE_API_URL || ''
                const response = await axios.post(`${API_URL}/api/upload`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    timeout: 120000,
                })
                onResults(response.data)
            } catch (err) {
                const detail =
                    err.response?.data?.detail || err.message || 'Upload failed.'
                onError(detail)
            }
        },
        [onUploadStart, onProcessing, onResults, onError]
    )

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'text/csv': ['.csv'] },
        maxFiles: 1,
        disabled: status === 'uploading' || status === 'processing',
    })

    const isLoading = status === 'uploading' || status === 'processing'

    return (
        <div
            {...getRootProps()}
            className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition-all duration-300 ${isDragActive
                ? 'border-primary-400 bg-primary-600/10 shadow-xl shadow-primary-600/10'
                : 'border-primary-700/40 hover:border-primary-500/60 hover:bg-primary-900/10'
                } ${isLoading ? 'pointer-events-none opacity-70' : ''}`}
        >
            <input {...getInputProps()} />

            {isLoading ? (
                <div className="space-y-4">
                    <div className="mx-auto w-16 h-16 rounded-full border-4 border-primary-700 border-t-primary-400 animate-spin" />
                    <p className="text-primary-300 font-semibold text-lg">
                        {status === 'uploading' ? 'Uploading...' : 'Analyzing transactions...'}
                    </p>
                    <p className="text-primary-400/50 text-sm">
                        Running graph-based detection algorithms
                    </p>
                    {fileName && (
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-900/30 text-primary-300 text-xs font-mono">
                            📄 {fileName}
                        </div>
                    )}
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-600/20 to-primary-800/20 border border-primary-700/30 flex items-center justify-center">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            className="h-9 w-9 text-primary-400"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                        >
                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                            <polyline points="14,2 14,8 20,8" />
                            <line x1="12" y1="18" x2="12" y2="12" />
                            <polyline points="9,15 12,12 15,15" />
                        </svg>
                    </div>
                    <div>
                        <p className="text-white font-semibold text-lg mb-1">
                            {isDragActive ? 'Drop your CSV here' : 'Drop CSV file or click to browse'}
                        </p>
                        <p className="text-primary-400/50 text-sm">
                            Required columns: transaction_id, sender_id, receiver_id, amount, timestamp
                        </p>
                    </div>
                    <div className="flex items-center justify-center gap-3 text-xs text-primary-500/40">
                        <span className="px-2 py-1 rounded-md bg-primary-900/20 border border-primary-800/20">.csv</span>
                        <span>Max 10,000+ transactions</span>
                    </div>
                </div>
            )}
        </div>
    )
}
