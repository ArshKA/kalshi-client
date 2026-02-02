/**
 * Portfolio Page Component
 *
 * Displays portfolio summary, positions, settlement history, and subaccounts.
 */
const PortfolioPage = ({ onBack, onSelectMarket }) => {
    const [summary, setSummary] = useState(null);
    const [positions, setPositions] = useState([]);
    const [settlements, setSettlements] = useState([]);
    const [subaccounts, setSubaccounts] = useState([]);
    const [transfers, setTransfers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('positions');

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch core portfolio data
                const [summaryRes, positionsRes, settlementsRes] = await Promise.all([
                    fetch('/api/portfolio/summary'),
                    fetch('/api/portfolio/positions'),
                    fetch('/api/portfolio/settlements?limit=50'),
                ]);

                if (!summaryRes.ok) throw new Error('Failed to fetch portfolio');

                const [summaryData, positionsData, settlementsData] = await Promise.all([
                    summaryRes.json(),
                    positionsRes.json(),
                    settlementsRes.json(),
                ]);

                setSummary(summaryData);
                setPositions(Array.isArray(positionsData) ? positionsData : []);
                setSettlements(Array.isArray(settlementsData) ? settlementsData : []);

                // Fetch subaccount data separately (optional, may not exist)
                try {
                    const [subaccountsRes, transfersRes] = await Promise.all([
                        fetch('/api/portfolio/subaccounts/balances'),
                        fetch('/api/portfolio/subaccounts/transfers?limit=20'),
                    ]);
                    if (subaccountsRes.ok && transfersRes.ok) {
                        const [subaccountsData, transfersData] = await Promise.all([
                            subaccountsRes.json(),
                            transfersRes.json(),
                        ]);
                        setSubaccounts(Array.isArray(subaccountsData) ? subaccountsData : []);
                        setTransfers(Array.isArray(transfersData) ? transfersData : []);
                    }
                } catch {
                    // Subaccounts not available, that's fine
                    setSubaccounts([]);
                    setTransfers([]);
                }

                setError(null);
            } catch (e) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
        const interval = setInterval(fetchData, 15000);
        return () => clearInterval(interval);
    }, []);

    const totalRealizedPnl = settlements.reduce((sum, s) => {
        const feeCents = Math.round(parseFloat(s.fee_cost || 0) * 100);
        const pnl = (s.revenue || 0) - (s.yes_total_cost || 0) - (s.no_total_cost || 0) - feeCents;
        return sum + pnl;
    }, 0);

    const totalSubaccountBalance = subaccounts.reduce((sum, s) => sum + (s.balance || 0), 0);

    return (
        <div className="min-h-screen bg-[#0e0e10] p-6">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <h1 className="text-2xl font-bold text-white">Portfolio</h1>
                    <button onClick={onBack} className="text-zinc-500 hover:text-white text-sm">
                        ← Back
                    </button>
                </div>

                {loading && (
                    <div className="text-zinc-500 text-center py-12">Loading portfolio...</div>
                )}

                {error && (
                    <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
                        {error}
                    </div>
                )}

                {summary && (
                    <div className="space-y-6">
                        {/* Summary Cards */}
                        <div className="grid grid-cols-3 gap-4">
                            <div className="bg-[#18181b] border border-zinc-800 rounded-xl p-4">
                                <div className="text-xs text-zinc-500 uppercase mb-1">Available Balance</div>
                                <div className="text-2xl font-mono text-white">{formatDollar(summary.balance)}</div>
                            </div>
                            <div className="bg-[#18181b] border border-zinc-800 rounded-xl p-4">
                                <div className="text-xs text-zinc-500 uppercase mb-1">Portfolio Value</div>
                                <div className="text-2xl font-mono text-kalshi-green">{formatDollar(summary.portfolio_value)}</div>
                            </div>
                            <div className="bg-[#18181b] border border-zinc-800 rounded-xl p-4">
                                <div className="text-xs text-zinc-500 uppercase mb-1">Realized P&L</div>
                                <div className={`text-2xl font-mono ${totalRealizedPnl >= 0 ? 'text-kalshi-green' : 'text-kalshi-red'}`}>
                                    {totalRealizedPnl >= 0 ? '+' : ''}{formatDollar(totalRealizedPnl)}
                                </div>
                            </div>
                        </div>

                        {/* Tabs */}
                        <div className="flex gap-2 border-b border-zinc-800">
                            <button
                                onClick={() => setActiveTab('positions')}
                                className={`px-4 py-2 text-sm font-medium transition-colors ${
                                    activeTab === 'positions'
                                        ? 'text-white border-b-2 border-kalshi-green'
                                        : 'text-zinc-500 hover:text-white'
                                }`}
                            >
                                Positions ({positions.length})
                            </button>
                            <button
                                onClick={() => setActiveTab('settlements')}
                                className={`px-4 py-2 text-sm font-medium transition-colors ${
                                    activeTab === 'settlements'
                                        ? 'text-white border-b-2 border-kalshi-green'
                                        : 'text-zinc-500 hover:text-white'
                                }`}
                            >
                                Settlements ({settlements.length})
                            </button>
                            {subaccounts.length > 0 && (
                                <button
                                    onClick={() => setActiveTab('subaccounts')}
                                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                                        activeTab === 'subaccounts'
                                            ? 'text-white border-b-2 border-kalshi-green'
                                            : 'text-zinc-500 hover:text-white'
                                    }`}
                                >
                                    Subaccounts ({subaccounts.length})
                                </button>
                            )}
                        </div>

                        {/* Positions Tab */}
                        {activeTab === 'positions' && (
                            <div className="bg-[#18181b] border border-zinc-800 rounded-xl overflow-hidden">
                                {positions.length === 0 ? (
                                    <div className="text-zinc-500 text-center py-12">No open positions</div>
                                ) : (
                                    <table className="w-full">
                                        <thead>
                                            <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase">
                                                <th className="text-left p-4">Market</th>
                                                <th className="text-right p-4">Position</th>
                                                <th className="text-right p-4">Exposure</th>
                                                <th className="text-right p-4">P&L</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {positions.map((p) => (
                                                <tr
                                                    key={p.ticker}
                                                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30 cursor-pointer transition-colors"
                                                    onClick={() => onSelectMarket && onSelectMarket(p.ticker)}
                                                >
                                                    <td className="p-4">
                                                        <div className="font-mono text-white text-sm">{p.ticker}</div>
                                                    </td>
                                                    <td className="p-4 text-right">
                                                        <span className={`font-mono ${p.position > 0 ? 'text-kalshi-green' : 'text-kalshi-red'}`}>
                                                            {p.position > 0 ? '+' : ''}{p.position} {p.position > 0 ? 'YES' : 'NO'}
                                                        </span>
                                                    </td>
                                                    <td className="p-4 text-right font-mono text-zinc-400">
                                                        {formatDollar(Math.abs(p.market_exposure || 0))}
                                                    </td>
                                                    <td className="p-4 text-right">
                                                        <span className={`font-mono ${(p.realized_pnl || 0) >= 0 ? 'text-kalshi-green' : 'text-kalshi-red'}`}>
                                                            {(p.realized_pnl || 0) >= 0 ? '+' : ''}{formatDollar(p.realized_pnl || 0)}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        )}

                        {/* Settlements Tab */}
                        {activeTab === 'settlements' && (
                            <div className="bg-[#18181b] border border-zinc-800 rounded-xl overflow-hidden">
                                {settlements.length === 0 ? (
                                    <div className="text-zinc-500 text-center py-12">No settlements yet</div>
                                ) : (
                                    <table className="w-full">
                                        <thead>
                                            <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase">
                                                <th className="text-left p-4">Market</th>
                                                <th className="text-right p-4">Result</th>
                                                <th className="text-right p-4">Position</th>
                                                <th className="text-right p-4">P&L</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {settlements.map((s, i) => {
                                                const feeCents = Math.round(parseFloat(s.fee_cost || 0) * 100);
                                                const pnl = (s.revenue || 0) - (s.yes_total_cost || 0) - (s.no_total_cost || 0) - feeCents;
                                                const netPos = (s.yes_count || 0) - (s.no_count || 0);
                                                const isYes = s.market_result === 'yes';
                                                return (
                                                    <tr key={`${s.ticker}-${i}`} className="border-b border-zinc-800/50">
                                                        <td className="p-4">
                                                            <div className="font-mono text-white text-sm">{s.ticker}</div>
                                                            {s.settled_time && (
                                                                <div className="text-xs text-zinc-600">
                                                                    {new Date(s.settled_time).toLocaleDateString()}
                                                                </div>
                                                            )}
                                                        </td>
                                                        <td className="p-4 text-right">
                                                            <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                                                                isYes
                                                                    ? 'bg-kalshi-green/20 text-kalshi-green'
                                                                    : 'bg-kalshi-red/20 text-kalshi-red'
                                                            }`}>
                                                                {isYes ? 'YES' : 'NO'}
                                                            </span>
                                                        </td>
                                                        <td className="p-4 text-right font-mono text-zinc-400">
                                                            {netPos !== 0 && (netPos > 0 ? `+${netPos} YES` : `${Math.abs(netPos)} NO`)}
                                                            {netPos === 0 && '—'}
                                                        </td>
                                                        <td className="p-4 text-right">
                                                            <span className={`font-mono ${pnl >= 0 ? 'text-kalshi-green' : 'text-kalshi-red'}`}>
                                                                {pnl >= 0 ? '+' : ''}{formatDollar(pnl)}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        )}

                        {/* Subaccounts Tab */}
                        {activeTab === 'subaccounts' && (
                            <div className="space-y-4">
                                {/* Subaccount Summary */}
                                <div className="bg-[#18181b] border border-zinc-800 rounded-xl p-4">
                                    <div className="flex justify-between items-center">
                                        <div>
                                            <div className="text-xs text-zinc-500 uppercase mb-1">Total Across Subaccounts</div>
                                            <div className="text-xl font-mono text-white">{formatDollar(totalSubaccountBalance)}</div>
                                        </div>
                                        <div className="text-xs text-zinc-600">
                                            {subaccounts.length} subaccount{subaccounts.length !== 1 ? 's' : ''}
                                        </div>
                                    </div>
                                </div>

                                {/* Subaccount Balances */}
                                <div className="bg-[#18181b] border border-zinc-800 rounded-xl overflow-hidden">
                                    <div className="px-4 py-3 border-b border-zinc-800">
                                        <h3 className="text-sm font-medium text-white">Balances</h3>
                                    </div>
                                    <table className="w-full">
                                        <thead>
                                            <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase">
                                                <th className="text-left p-4">Subaccount</th>
                                                <th className="text-right p-4">Balance</th>
                                                <th className="text-right p-4">Portfolio Value</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {subaccounts.map((sub) => (
                                                <tr key={sub.subaccount_id} className="border-b border-zinc-800/50">
                                                    <td className="p-4">
                                                        <div className="font-mono text-white text-sm">
                                                            {sub.subaccount_id.slice(0, 8)}...
                                                        </div>
                                                    </td>
                                                    <td className="p-4 text-right font-mono text-white">
                                                        {formatDollar(sub.balance || 0)}
                                                    </td>
                                                    <td className="p-4 text-right font-mono text-zinc-400">
                                                        {sub.portfolio_value != null ? formatDollar(sub.portfolio_value) : '—'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Recent Transfers */}
                                {transfers.length > 0 && (
                                    <div className="bg-[#18181b] border border-zinc-800 rounded-xl overflow-hidden">
                                        <div className="px-4 py-3 border-b border-zinc-800">
                                            <h3 className="text-sm font-medium text-white">Recent Transfers</h3>
                                        </div>
                                        <table className="w-full">
                                            <thead>
                                                <tr className="border-b border-zinc-800 text-xs text-zinc-500 uppercase">
                                                    <th className="text-left p-4">From → To</th>
                                                    <th className="text-right p-4">Amount</th>
                                                    <th className="text-right p-4">Date</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {transfers.map((t) => (
                                                    <tr key={t.transfer_id} className="border-b border-zinc-800/50">
                                                        <td className="p-4">
                                                            <div className="font-mono text-xs text-zinc-400">
                                                                {t.from_subaccount_id.slice(0, 6)}... → {t.to_subaccount_id.slice(0, 6)}...
                                                            </div>
                                                        </td>
                                                        <td className="p-4 text-right font-mono text-white">
                                                            {formatDollar(t.amount)}
                                                        </td>
                                                        <td className="p-4 text-right text-xs text-zinc-500">
                                                            {t.created_time ? new Date(t.created_time).toLocaleDateString() : '—'}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        )}

                        <p className="text-xs text-zinc-600 text-center">
                            Auto-refreshes every 15 seconds
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};
