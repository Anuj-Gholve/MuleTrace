export default function ResultsDashboard({ results }) {
    const { suspicious_accounts, fraud_rings, summary } = results

    const patternColors = {
        cycle: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
        smurfing: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
        shell_chain: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30' },
    }

    const getScoreColor = (score) => {
        if (score >= 80) return 'text-red-400'
        if (score >= 50) return 'text-amber-400'
        if (score >= 25) return 'text-yellow-300'
        return 'text-green-400'
    }

    const getScoreBarColor = (score) => {
        if (score >= 80) return 'from-red-600 to-red-400'
        if (score >= 50) return 'from-amber-600 to-amber-400'
        if (score >= 25) return 'from-yellow-600 to-yellow-400'
        return 'from-green-600 to-green-400'
    }

    return (
        <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                    {
                        label: 'Accounts Analyzed',
                        value: summary.total_accounts_analyzed,
                        icon: '👥',
                        color: 'from-primary-600/20 to-primary-800/20',
                        border: 'border-primary-700/30',
                    },
                    {
                        label: 'Suspicious Flagged',
                        value: summary.suspicious_accounts_flagged,
                        icon: '🚨',
                        color: 'from-red-600/20 to-red-800/20',
                        border: 'border-red-700/30',
                    },
                    {
                        label: 'Fraud Rings',
                        value: summary.fraud_rings_detected,
                        icon: '🔗',
                        color: 'from-amber-600/20 to-amber-800/20',
                        border: 'border-amber-700/30',
                    },
                    {
                        label: 'Processing Time',
                        value: `${summary.processing_time_seconds}s`,
                        icon: '⚡',
                        color: 'from-green-600/20 to-green-800/20',
                        border: 'border-green-700/30',
                    },
                ].map((card) => (
                    <div
                        key={card.label}
                        className={`rounded-xl bg-gradient-to-br ${card.color} border ${card.border} p-5 transition-all duration-300 hover:scale-[1.02]`}
                    >
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-2xl">{card.icon}</span>
                        </div>
                        <p className="text-2xl font-bold text-white mb-1">{card.value}</p>
                        <p className="text-xs text-primary-300/50 font-medium uppercase tracking-wider">
                            {card.label}
                        </p>
                    </div>
                ))}
            </div>

            {/* Fraud Rings Table */}
            <div className="glass rounded-xl overflow-hidden">
                <div className="px-6 py-4 border-b border-primary-800/30">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        🔗 Fraud Ring Summary
                    </h3>
                    <p className="text-xs text-primary-400/50 mt-1">
                        Detected fraud rings with member details and risk assessment
                    </p>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-primary-900/20 text-primary-300/70">
                                <th className="px-6 py-3 text-left font-semibold text-xs uppercase tracking-wider">Ring ID</th>
                                <th className="px-6 py-3 text-left font-semibold text-xs uppercase tracking-wider">Pattern Type</th>
                                <th className="px-6 py-3 text-center font-semibold text-xs uppercase tracking-wider">Members</th>
                                <th className="px-6 py-3 text-center font-semibold text-xs uppercase tracking-wider">Risk Score</th>
                                <th className="px-6 py-3 text-left font-semibold text-xs uppercase tracking-wider">Member Accounts</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-primary-800/20">
                            {fraud_rings.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-8 text-center text-primary-400/40">
                                        No fraud rings detected
                                    </td>
                                </tr>
                            ) : (
                                fraud_rings.map((ring) => {
                                    const colors = patternColors[ring.pattern_type] || patternColors.cycle
                                    return (
                                        <tr
                                            key={ring.ring_id}
                                            className="hover:bg-primary-900/10 transition-colors duration-150"
                                        >
                                            <td className="px-6 py-3">
                                                <span className="font-mono font-semibold text-primary-300">
                                                    {ring.ring_id}
                                                </span>
                                            </td>
                                            <td className="px-6 py-3">
                                                <span
                                                    className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold ${colors.bg} ${colors.text} border ${colors.border}`}
                                                >
                                                    {ring.pattern_type}
                                                </span>
                                            </td>
                                            <td className="px-6 py-3 text-center">
                                                <span className="text-white font-bold">
                                                    {ring.member_accounts.length}
                                                </span>
                                            </td>
                                            <td className="px-6 py-3 text-center">
                                                <span className={`font-bold ${getScoreColor(ring.risk_score)}`}>
                                                    {ring.risk_score}
                                                </span>
                                            </td>
                                            <td className="px-6 py-3">
                                                <div className="flex flex-wrap gap-1 max-w-md">
                                                    {ring.member_accounts.slice(0, 8).map((acc) => (
                                                        <span
                                                            key={acc}
                                                            className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-primary-900/40 text-primary-300/80 border border-primary-800/30"
                                                        >
                                                            {acc}
                                                        </span>
                                                    ))}
                                                    {ring.member_accounts.length > 8 && (
                                                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-primary-400/50">
                                                            +{ring.member_accounts.length - 8} more
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Suspicious Accounts */}
            <div className="glass rounded-xl overflow-hidden">
                <div className="px-6 py-4 border-b border-primary-800/30">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        🚨 Suspicious Accounts
                    </h3>
                    <p className="text-xs text-primary-400/50 mt-1">
                        Accounts flagged by the detection engine, sorted by suspicion score
                    </p>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-primary-900/20 text-primary-300/70">
                                <th className="px-6 py-3 text-left font-semibold text-xs uppercase tracking-wider">Account ID</th>
                                <th className="px-6 py-3 text-left font-semibold text-xs uppercase tracking-wider">Suspicion Score</th>
                                <th className="px-6 py-3 text-left font-semibold text-xs uppercase tracking-wider">Patterns</th>
                                <th className="px-6 py-3 text-left font-semibold text-xs uppercase tracking-wider">Ring ID</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-primary-800/20">
                            {suspicious_accounts.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-8 text-center text-primary-400/40">
                                        No suspicious accounts found
                                    </td>
                                </tr>
                            ) : (
                                suspicious_accounts.slice(0, 50).map((acc, idx) => (
                                    <tr
                                        key={`${acc.account_id}-${acc.ring_id}-${idx}`}
                                        className="hover:bg-primary-900/10 transition-colors duration-150"
                                    >
                                        <td className="px-6 py-3">
                                            <span className="font-mono font-semibold text-white">
                                                {acc.account_id}
                                            </span>
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center gap-3 min-w-[140px]">
                                                <div className="w-20 h-2 rounded-full bg-primary-900/40 overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full bg-gradient-to-r ${getScoreBarColor(acc.suspicion_score)}`}
                                                        style={{ width: `${acc.suspicion_score}%` }}
                                                    />
                                                </div>
                                                <span className={`font-bold text-sm ${getScoreColor(acc.suspicion_score)}`}>
                                                    {acc.suspicion_score}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="flex flex-wrap gap-1">
                                                {acc.detected_patterns.map((p) => (
                                                    <span
                                                        key={p}
                                                        className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary-900/30 text-primary-300/80 border border-primary-800/20"
                                                    >
                                                        {p}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                        <td className="px-6 py-3">
                                            <span className="font-mono text-primary-300/70 text-xs">
                                                {acc.ring_id}
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                    {suspicious_accounts.length > 50 && (
                        <div className="px-6 py-3 text-center text-xs text-primary-400/40 border-t border-primary-800/20">
                            Showing 50 of {suspicious_accounts.length} suspicious accounts
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
