import { useEffect, useRef, useState, useMemo } from 'react'
import cytoscape from 'cytoscape'

// Distinct ring colors
const RING_PALETTE = [
    { fill: '#dc2626', border: '#fca5a5' },
    { fill: '#d97706', border: '#fcd34d' },
    { fill: '#7c3aed', border: '#c4b5fd' },
    { fill: '#0891b2', border: '#67e8f9' },
    { fill: '#db2777', border: '#f9a8d4' },
    { fill: '#059669', border: '#6ee7b7' },
    { fill: '#ea580c', border: '#fdba74' },
    { fill: '#4f46e5', border: '#a5b4fc' },
    { fill: '#0d9488', border: '#5eead4' },
    { fill: '#e11d48', border: '#fda4af' },
]

const PATTERN_LABELS = {
    cycle: '🔄 Cycle',
    smurfing: '📡 Smurfing',
    shell_chain: '🐚 Shell Chain',
    passthrough: '💸 Pass-Through',
    temporal_burst: '⚡ Burst',
}

// Pattern badge colors
function patternColor(p) {
    if (p.includes('cycle')) return { bg: '#991b1b30', fg: '#fca5a5', border: '#991b1b50' }
    if (p.includes('fan_in')) return { bg: '#92400e30', fg: '#fcd34d', border: '#92400e50' }
    if (p.includes('fan_out')) return { bg: '#78350f30', fg: '#fbbf24', border: '#78350f50' }
    if (p.includes('shell')) return { bg: '#581c8730', fg: '#c4b5fd', border: '#581c8750' }
    if (p.includes('passthrough')) return { bg: '#0e749130', fg: '#67e8f9', border: '#0e749150' }
    if (p.includes('burst')) return { bg: '#9a340030', fg: '#fdba74', border: '#9a340050' }
    return { bg: '#33415530', fg: '#94a3b8', border: '#33415550' }
}

export default function GraphVisualization({ results }) {
    const containerRef = useRef(null)
    const cyRef = useRef(null)
    const [hoveredNode, setHoveredNode] = useState(null)
    const [layoutType, setLayoutType] = useState('cose')
    const [selectedRing, setSelectedRing] = useState(null)

    const ringColorMap = useMemo(() => {
        const map = {}
        results.fraud_rings.forEach((ring, i) => {
            map[ring.ring_id] = RING_PALETTE[i % RING_PALETTE.length]
        })
        return map
    }, [results.fraud_rings])

    const nodeRingMap = useMemo(() => {
        const map = {}
        const priority = { cycle: 3, smurfing: 2, shell_chain: 1, passthrough: 2, temporal_burst: 1 }
        results.fraud_rings.forEach((ring) => {
            ring.member_accounts.forEach((acc) => {
                const existing = map[acc]
                if (!existing || (priority[ring.pattern_type] || 0) > (priority[existing.pattern_type] || 0)) {
                    map[acc] = { ring_id: ring.ring_id, pattern_type: ring.pattern_type }
                }
            })
        })
        return map
    }, [results.fraud_rings])

    const suspiciousSet = useMemo(() => {
        const s = new Set()
        results.graph.nodes.forEach((n) => { if (n.is_suspicious) s.add(n.id) })
        return s
    }, [results.graph.nodes])

    useEffect(() => {
        if (!containerRef.current) return
        const elements = []

        results.graph.nodes.forEach((n) => {
            const ringInfo = nodeRingMap[n.id]
            const ringId = ringInfo ? ringInfo.ring_id : ''
            const palette = ringId ? ringColorMap[ringId] : null
            const patternType = ringInfo ? ringInfo.pattern_type : ''
            let size = 22
            if (n.is_suspicious) size = 28 + Math.min(n.suspicion_score, 100) * 0.2

            elements.push({
                data: {
                    id: n.id,
                    label: n.id,
                    fullLabel: n.id,
                    in_degree: n.in_degree,
                    out_degree: n.out_degree,
                    total_degree: n.total_degree,
                    suspicion_score: n.suspicion_score,
                    is_suspicious: n.is_suspicious,
                    ring_id: ringId,
                    pattern_type: patternType,
                    detected_patterns_list: n.detected_patterns || [],
                    nodeColor: palette ? palette.fill : (n.is_suspicious ? '#dc2626' : '#334155'),
                    borderColor: palette ? palette.border : (n.is_suspicious ? '#fca5a5' : '#64748b'),
                    nodeSize: size,
                },
            })
        })

        results.graph.edges.forEach((e, i) => {
            elements.push({
                data: {
                    id: `e${i}`,
                    source: e.source,
                    target: e.target,
                    isSuspiciousEdge: suspiciousSet.has(e.source) && suspiciousSet.has(e.target),
                },
            })
        })

        const cy = cytoscape({
            container: containerRef.current,
            elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        label: 'data(label)',
                        'font-size': '8px',
                        'font-family': '"JetBrains Mono", monospace',
                        color: '#94a3b8',
                        'text-valign': 'bottom',
                        'text-margin-y': 5,
                        'text-outline-width': 2,
                        'text-outline-color': '#0f172a',
                        'background-color': 'data(nodeColor)',
                        'border-width': 2,
                        'border-color': 'data(borderColor)',
                        width: 'data(nodeSize)',
                        height: 'data(nodeSize)',
                        'overlay-opacity': 0,
                        'transition-property': 'width, height, border-width, opacity, background-color',
                        'transition-duration': '0.25s',
                    },
                },
                {
                    selector: 'node[?is_suspicious]',
                    style: {
                        'border-width': 3,
                        color: '#f1f5f9',
                        'font-weight': 600,
                        'font-size': '9px',
                    },
                },
                {
                    selector: 'edge',
                    style: {
                        width: 1.2,
                        'line-color': '#1e293b',
                        'target-arrow-color': '#475569',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 0.7,
                        'curve-style': 'bezier',
                        opacity: 0.4,
                    },
                },
                {
                    selector: 'edge[?isSuspiciousEdge]',
                    style: {
                        width: 2,
                        'line-color': '#991b1b',
                        'target-arrow-color': '#ef4444',
                        opacity: 0.7,
                    },
                },
                {
                    selector: '.hover-focus',
                    style: {
                        'border-width': 4,
                        'border-color': '#fbbf24',
                        width: 'mapData(nodeSize, 22, 48, 34, 56)',
                        height: 'mapData(nodeSize, 22, 48, 34, 56)',
                        color: '#ffffff',
                        'font-size': '10px',
                    },
                },
                {
                    selector: '.hover-neighbor',
                    style: { 'border-width': 3, 'border-color': '#fde68a', opacity: 1 },
                },
                {
                    selector: 'edge.hover-edge',
                    style: { width: 2.5, 'line-color': '#fbbf24', 'target-arrow-color': '#fbbf24', opacity: 0.9 },
                },
                {
                    selector: '.dimmed',
                    style: { opacity: 0.12 },
                },
                {
                    selector: '.ring-highlight',
                    style: { 'border-width': 4, opacity: 1 },
                },
                {
                    selector: 'node:active',
                    style: { 'overlay-opacity': 0 },
                },
            ],
            layout: {
                name: layoutType,
                animate: false,
                padding: 50,
                nodeRepulsion: () => 12000,
                idealEdgeLength: () => 120,
                nodeOverlap: 40,
                gravity: 0.25,
            },
            minZoom: 0.1,
            maxZoom: 5,
            wheelSensitivity: 0.25,
        })

        cy.on('mouseover', 'node', (evt) => {
            const node = evt.target
            setHoveredNode(node.data())
            cy.elements().addClass('dimmed')
            node.removeClass('dimmed').addClass('hover-focus')
            node.connectedEdges().removeClass('dimmed').addClass('hover-edge')
            node.neighborhood('node').removeClass('dimmed').addClass('hover-neighbor')
        })

        cy.on('mouseout', 'node', () => {
            setHoveredNode(null)
            cy.elements().removeClass('dimmed hover-focus hover-edge hover-neighbor')
        })

        cyRef.current = cy
        return () => cy.destroy()
    }, [results, ringColorMap, nodeRingMap, suspiciousSet, layoutType])

    const handleLayout = (name) => {
        setLayoutType(name)
        if (cyRef.current) {
            cyRef.current.layout({
                name, animate: true, animationDuration: 600, padding: 50,
                nodeRepulsion: () => 12000, idealEdgeLength: () => 120, gravity: 0.25,
            }).run()
        }
    }

    const handleFitView = () => {
        cyRef.current?.animate({ fit: { padding: 50 }, duration: 400, easing: 'ease-out' })
    }

    const handleHighlightRing = (ringId) => {
        if (!cyRef.current) return
        const cy = cyRef.current
        if (selectedRing === ringId) {
            setSelectedRing(null)
            cy.elements().removeClass('dimmed ring-highlight hover-edge')
            return
        }
        setSelectedRing(ringId)
        const ring = results.fraud_rings.find((r) => r.ring_id === ringId)
        if (!ring) return
        cy.elements().addClass('dimmed')
        ring.member_accounts.forEach((acc) => {
            const node = cy.getElementById(acc)
            if (node.length) {
                node.removeClass('dimmed').addClass('ring-highlight')
                node.connectedEdges().forEach((edge) => {
                    const other = edge.connectedNodes().filter((n) => n.id() !== acc)
                    if (other.length && ring.member_accounts.includes(other[0].id())) {
                        edge.removeClass('dimmed').addClass('hover-edge')
                    }
                })
            }
        })
    }

    const ringsByPattern = useMemo(() => {
        const groups = {}
        results.fraud_rings.forEach((ring) => {
            if (!groups[ring.pattern_type]) groups[ring.pattern_type] = []
            groups[ring.pattern_type].push(ring)
        })
        return groups
    }, [results.fraud_rings])

    // Score color helper
    const scoreColor = (s) => s >= 80 ? 'text-red-400' : s >= 50 ? 'text-amber-400' : s > 0 ? 'text-yellow-300' : 'text-green-400'
    const scoreGradient = (s) =>
        s >= 80 ? 'linear-gradient(90deg, #dc2626, #ef4444)'
            : s >= 50 ? 'linear-gradient(90deg, #d97706, #f59e0b)'
                : s > 0 ? 'linear-gradient(90deg, #ca8a04, #eab308)'
                    : 'linear-gradient(90deg, #16a34a, #22c55e)'

    return (
        <div className="space-y-4">
            {/* Controls Bar */}
            <div className="glass rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500 font-medium uppercase tracking-wider mr-1">Layout:</span>
                        {[
                            { id: 'cose', label: 'Force' },
                            { id: 'circle', label: 'Circle' },
                            { id: 'breadthfirst', label: 'Tree' },
                            { id: 'grid', label: 'Grid' },
                        ].map((l) => (
                            <button
                                key={l.id}
                                onClick={() => handleLayout(l.id)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${layoutType === l.id
                                        ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                                        : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 border border-slate-700/50'
                                    }`}
                            >
                                {l.label}
                            </button>
                        ))}
                        <button
                            onClick={handleFitView}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 border border-slate-700/50 transition-all duration-200 ml-1"
                        >
                            ⟲ Fit
                        </button>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded-full bg-slate-700 border-2 border-slate-500" />
                            <span className="text-slate-500">Clean</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <div className="w-4 h-4 rounded-full bg-red-700 border-2 border-red-400" />
                            <span className="text-slate-500">Suspicious</span>
                        </div>
                    </div>
                </div>

                {/* Ring filter chips */}
                {results.fraud_rings.length > 0 && (
                    <div className="flex flex-wrap gap-2 items-center">
                        <span className="text-xs text-slate-500 font-medium uppercase tracking-wider mr-1">Rings:</span>
                        {Object.entries(ringsByPattern).map(([pattern, rings]) => (
                            <div key={pattern} className="flex items-center gap-1">
                                <span className="text-[10px] text-slate-600 mr-0.5">{PATTERN_LABELS[pattern] || pattern}:</span>
                                {rings.slice(0, 6).map((ring) => {
                                    const palette = ringColorMap[ring.ring_id]
                                    const isActive = selectedRing === ring.ring_id
                                    return (
                                        <button
                                            key={ring.ring_id}
                                            onClick={() => handleHighlightRing(ring.ring_id)}
                                            className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold transition-all duration-200 border ${isActive ? 'scale-110 shadow-lg' : 'opacity-80 hover:opacity-100'
                                                }`}
                                            style={{
                                                backgroundColor: isActive ? palette?.fill : 'transparent',
                                                borderColor: palette?.border || '#64748b',
                                                color: isActive ? '#fff' : palette?.border || '#94a3b8',
                                            }}
                                        >
                                            {ring.ring_id}
                                        </button>
                                    )
                                })}
                                {rings.length > 6 && <span className="text-[10px] text-slate-600">+{rings.length - 6}</span>}
                            </div>
                        ))}
                        {selectedRing && (
                            <button
                                onClick={() => {
                                    setSelectedRing(null)
                                    cyRef.current?.elements().removeClass('dimmed ring-highlight hover-edge')
                                }}
                                className="px-2 py-0.5 rounded-full text-[10px] font-semibold text-slate-400 border border-slate-600 hover:text-white hover:border-slate-400 transition-all"
                            >
                                ✕ Clear
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Graph */}
            <div
                className="relative rounded-xl overflow-hidden border border-slate-800/80"
                style={{ height: '650px', background: 'linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #0a0f1a 100%)' }}
            >
                <div ref={containerRef} className="w-full h-full" />

                {/* ───── HOVER TOOLTIP ───── */}
                {hoveredNode && (
                    <div
                        className="absolute top-4 right-4 rounded-xl p-4 min-w-[260px] max-w-[320px] shadow-2xl border border-slate-700/50 z-50"
                        style={{ background: 'rgba(15, 23, 42, 0.95)', backdropFilter: 'blur(16px)' }}
                    >
                        {/* Header */}
                        <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-700/40">
                            <div
                                className="w-3.5 h-3.5 rounded-full flex-shrink-0"
                                style={{
                                    backgroundColor: hoveredNode.nodeColor,
                                    boxShadow: hoveredNode.is_suspicious ? `0 0 10px ${hoveredNode.nodeColor}` : 'none',
                                }}
                            />
                            <div>
                                <p className="font-mono font-bold text-white text-sm leading-tight">{hoveredNode.fullLabel}</p>
                                <p className="text-[10px] text-slate-500">
                                    {hoveredNode.is_suspicious ? '⚠ Suspicious Account' : '✓ Clean Account'}
                                </p>
                            </div>
                        </div>

                        {/* Degree metrics */}
                        <div className="grid grid-cols-3 gap-2 mb-3">
                            <div className="text-center p-1.5 rounded-lg bg-slate-800/50">
                                <p className="text-white font-bold font-mono">{hoveredNode.in_degree}</p>
                                <p className="text-[9px] text-slate-500">In</p>
                            </div>
                            <div className="text-center p-1.5 rounded-lg bg-slate-800/50">
                                <p className="text-white font-bold font-mono">{hoveredNode.out_degree}</p>
                                <p className="text-[9px] text-slate-500">Out</p>
                            </div>
                            <div className="text-center p-1.5 rounded-lg bg-slate-800/50">
                                <p className="text-white font-bold font-mono">{hoveredNode.total_degree}</p>
                                <p className="text-[9px] text-slate-500">Total</p>
                            </div>
                        </div>

                        {/* Suspicion Score */}
                        <div className="mb-3">
                            <div className="flex justify-between items-center mb-1">
                                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Suspicion Score</span>
                                <span className={`text-sm font-bold font-mono ${scoreColor(hoveredNode.suspicion_score)}`}>
                                    {hoveredNode.suspicion_score}/100
                                </span>
                            </div>
                            <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                                <div
                                    className="h-full rounded-full transition-all duration-300"
                                    style={{ width: `${hoveredNode.suspicion_score}%`, background: scoreGradient(hoveredNode.suspicion_score) }}
                                />
                            </div>
                        </div>

                        {/* Detected Patterns */}
                        {hoveredNode.detected_patterns_list && hoveredNode.detected_patterns_list.length > 0 && (
                            <div className="mb-3">
                                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-1.5">Detected Patterns</p>
                                <div className="flex flex-wrap gap-1">
                                    {hoveredNode.detected_patterns_list.map((p, i) => {
                                        const c = patternColor(p)
                                        return (
                                            <span
                                                key={i}
                                                className="px-1.5 py-0.5 rounded text-[9px] font-semibold"
                                                style={{ backgroundColor: c.bg, color: c.fg, border: `1px solid ${c.border}` }}
                                            >
                                                {p}
                                            </span>
                                        )
                                    })}
                                </div>
                            </div>
                        )}

                        {/* Ring & Pattern */}
                        {(hoveredNode.ring_id || hoveredNode.pattern_type) && (
                            <div className="flex items-center gap-2 pt-2 border-t border-slate-700/40">
                                {hoveredNode.ring_id && (
                                    <span
                                        className="font-mono font-semibold text-[10px] px-1.5 py-0.5 rounded"
                                        style={{
                                            color: ringColorMap[hoveredNode.ring_id]?.border || '#94a3b8',
                                            backgroundColor: (ringColorMap[hoveredNode.ring_id]?.fill || '#334155') + '25',
                                            border: `1px solid ${(ringColorMap[hoveredNode.ring_id]?.fill || '#334155')}40`,
                                        }}
                                    >
                                        {hoveredNode.ring_id}
                                    </span>
                                )}
                                {hoveredNode.pattern_type && (
                                    <span className="text-slate-400 text-[10px] font-medium">
                                        {PATTERN_LABELS[hoveredNode.pattern_type] || hoveredNode.pattern_type}
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Stats */}
                <div className="absolute bottom-3 left-3 text-[10px] text-slate-600 font-mono">
                    {results.graph.nodes.length} nodes · {results.graph.edges.length} edges
                </div>
            </div>
        </div>
    )
}
