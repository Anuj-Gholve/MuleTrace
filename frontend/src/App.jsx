import { useState } from 'react'
import FileUpload from './components/FileUpload'
import ResultsDashboard from './components/ResultsDashboard'
import GraphVisualization from './components/GraphVisualization'

function App() {
    const [results, setResults] = useState(null)
    const [status, setStatus] = useState('idle') // idle | uploading | processing | done | error
    const [error, setError] = useState(null)
    const [activeTab, setActiveTab] = useState('dashboard')

    const handleUploadStart = () => {
        setStatus('uploading')
        setError(null)
    }

    const handleProcessing = () => {
        setStatus('processing')
    }

    const handleResults = (data) => {
        setResults(data)
        setStatus('done')
        setActiveTab('dashboard')
    }

    const handleError = (err) => {
        setError(err)
        setStatus('error')
    }

    const handleReset = () => {
        setResults(null)
        setStatus('idle')
        setError(null)
    }

    const handleDownloadJSON = () => {
        if (!results) return
        const { graph, ...outputData } = results
        const blob = new Blob([JSON.stringify(outputData, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'detection_results.json'
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <div className="min-h-screen bg-surface-950">
            {/* Header */}
            <header className="glass sticky top-0 z-50 border-b border-primary-900/30">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg shadow-primary-500/20">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <circle cx="12" cy="12" r="3" />
                                    <circle cx="4" cy="6" r="2" />
                                    <circle cx="20" cy="6" r="2" />
                                    <circle cx="4" cy="18" r="2" />
                                    <circle cx="20" cy="18" r="2" />
                                    <line x1="6" y1="6" x2="9" y2="10" />
                                    <line x1="18" y1="6" x2="15" y2="10" />
                                    <line x1="6" y1="18" x2="9" y2="14" />
                                    <line x1="18" y1="18" x2="15" y2="14" />
                                </svg>
                            </div>
                            <div>
                                <h1 className="text-lg font-bold text-white tracking-tight">
                                    MuleTrace
                                </h1>
                                <p className="text-xs text-primary-300/60 font-medium -mt-0.5">
                                    Graph-Based Money Muling Analysis
                                </p>
                            </div>
                        </div>

                        {results && (
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={handleDownloadJSON}
                                    className="px-4 py-2 text-sm font-medium rounded-lg bg-primary-600 hover:bg-primary-500 text-white transition-all duration-200 flex items-center gap-2 shadow-lg shadow-primary-600/20"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                                        <polyline points="7,10 12,15 17,10" />
                                        <line x1="12" y1="15" x2="12" y2="3" />
                                    </svg>
                                    Export JSON
                                </button>
                                <button
                                    onClick={handleReset}
                                    className="px-4 py-2 text-sm font-medium rounded-lg border border-primary-700/50 text-primary-300 hover:bg-primary-900/30 transition-all duration-200"
                                >
                                    New Analysis
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Upload Area — shown when no results */}
                {!results && (
                    <div className="flex items-center justify-center min-h-[70vh]">
                        <div className="w-full max-w-2xl animate-fade-in-up">
                            <div className="text-center mb-8">
                                <h2 className="text-3xl font-extrabold text-white mb-3">
                                    Detect Financial Crime
                                </h2>
                                <p className="text-primary-300/70 text-lg max-w-lg mx-auto">
                                    Upload transaction data to discover money muling patterns using
                                    advanced graph algorithms.
                                </p>
                            </div>
                            <FileUpload
                                onUploadStart={handleUploadStart}
                                onProcessing={handleProcessing}
                                onResults={handleResults}
                                onError={handleError}
                                status={status}
                            />
                            {error && (
                                <div className="mt-4 p-4 rounded-xl bg-danger-600/10 border border-danger-500/30 text-danger-400 text-sm">
                                    <strong>Error:</strong> {error}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Results — shown when analysis is complete */}
                {results && (
                    <div className="space-y-6 animate-fade-in-up">
                        {/* Tabs */}
                        <div className="flex gap-1 p-1 glass rounded-xl w-fit">
                            {[
                                { key: 'dashboard', label: 'Dashboard', icon: '📊' },
                                { key: 'graph', label: 'Graph Visualization', icon: '🔗' },
                            ].map((tab) => (
                                <button
                                    key={tab.key}
                                    onClick={() => setActiveTab(tab.key)}
                                    className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 flex items-center gap-2 ${activeTab === tab.key
                                            ? 'bg-primary-600 text-white shadow-lg shadow-primary-600/30'
                                            : 'text-primary-300/60 hover:text-primary-200 hover:bg-primary-900/20'
                                        }`}
                                >
                                    <span>{tab.icon}</span>
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        {activeTab === 'dashboard' && (
                            <ResultsDashboard results={results} />
                        )}
                        {activeTab === 'graph' && (
                            <GraphVisualization results={results} />
                        )}
                    </div>
                )}
            </main>

            {/* Footer */}
            <footer className="border-t border-primary-900/20 py-6 mt-12">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <p className="text-xs text-primary-300/30">
                        MuleTrace · Hackathon Project · Money Muling Detection via Graph Theory
                    </p>
                </div>
            </footer>
        </div>
    )
}

export default App
