/**
 * Balance/P&L Chart Component
 * Shows portfolio performance over time using pure SVG.
 */
const BalanceChart = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [timeframe, setTimeframe] = useState('1M');
    const [hoverIndex, setHoverIndex] = useState(null);

    useEffect(() => {
        setLoading(true);
        const config = {
            '1D': { days: 1, resolution: 'minute' },
            '1W': { days: 7, resolution: 'hour' },
            '1M': { days: 30, resolution: 'hour' },
            '3M': { days: 90, resolution: 'day' },
            'ALL': { days: 1825, resolution: 'day' },
        }[timeframe] || { days: 30, resolution: 'hour' };

        fetch(`/api/portfolio/history?days=${config.days}&resolution=${config.resolution}`)
            .then(res => res.json())
            .then(raw => {
                const sorted = Array.isArray(raw) ? raw.sort((a, b) => a.ts - b.ts) : [];
                setData(sorted);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [timeframe]);

    const formatDate = (ts) => {
        const d = new Date(ts * 1000);
        if (timeframe === '1W') return d.toLocaleDateString([], { weekday: 'short', month: 'numeric', day: 'numeric' });
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    };

    if (loading) {
        return (
            <div className="h-64 flex items-center justify-center text-zinc-600 text-xs uppercase animate-pulse">
                Loading History...
            </div>
        );
    }

    if (!data.length) {
        return (
            <div className="h-64 flex flex-col items-center justify-center text-zinc-600 text-xs uppercase relative">
                <div className="absolute top-2 right-4 flex gap-2">
                    {['1D', '1W', '1M', '3M', 'ALL'].map(tf => (
                        <button
                            key={tf}
                            onClick={() => setTimeframe(tf)}
                            className={`text-[10px] font-bold px-2 py-1 rounded transition-colors ${
                                timeframe === tf ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
                            }`}
                        >
                            {tf}
                        </button>
                    ))}
                </div>
                No trading history
            </div>
        );
    }

    const width = 800;
    const height = 200;
    const padding = { top: 20, right: 60, bottom: 20, left: 10 };

    const values = data.map(d => d.pnl);
    const minVal = Math.min(0, ...values);
    const maxVal = Math.max(0, ...values);
    const range = maxVal - minVal || 1;
    const buffer = range * 0.1;

    const getX = (i) => padding.left + (i / (data.length - 1)) * (width - padding.left - padding.right);
    const getY = (v) => padding.top + ((maxVal + buffer - v) / (range + buffer * 2)) * (height - padding.top - padding.bottom);

    const points = data.map((d, i) => `${getX(i)},${getY(d.pnl)}`).join(' ');
    const zeroY = getY(0);

    const endPnl = data[data.length - 1].pnl;
    const isPositive = endPnl >= 0;
    const strokeColor = isPositive ? '#4ade80' : '#f87171';

    const areaPath = `
        M ${padding.left},${zeroY}
        L ${padding.left},${getY(data[0].pnl)}
        ${points.replace(/,/g, ' ')}
        L ${width - padding.right},${zeroY}
        Z
    `;

    const currentData = hoverIndex !== null ? data[hoverIndex] : data[data.length - 1];
    const currentPnl = currentData.pnl;
    const currentDate = new Date(currentData.ts * 1000);

    return (
        <div className="w-full relative pt-4 pb-2 px-4 flex flex-col">
            <div className="flex justify-between items-start mb-2 z-10 relative">
                <div className="flex flex-col">
                    <span className="text-xs text-zinc-500 uppercase tracking-wider font-bold mb-1">
                        Cumulative P&L
                    </span>
                    <span className={`text-xl font-mono tracking-tight font-bold ${currentPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {currentPnl >= 0 ? '+' : ''}{formatDollar(currentPnl)}
                    </span>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider">
                        {hoverIndex !== null
                            ? currentDate.toLocaleDateString() + ' ' + currentDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                            : `${formatDate(data[0].ts)} - ${formatDate(data[data.length - 1].ts)}`
                        }
                    </span>
                </div>
                <div className="flex gap-1 bg-[#18181b] p-1 rounded-lg border border-zinc-800">
                    {['1D', '1W', '1M', '3M', 'ALL'].map(tf => (
                        <button
                            key={tf}
                            onClick={() => setTimeframe(tf)}
                            className={`text-[10px] font-bold px-2 py-1 rounded transition-colors ${
                                timeframe === tf ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
                            }`}
                        >
                            {tf}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 relative cursor-crosshair overflow-visible" style={{ height: height }}>
                <svg
                    viewBox={`0 0 ${width} ${height}`}
                    className="w-full h-full overflow-visible"
                    preserveAspectRatio="none"
                    onMouseLeave={() => setHoverIndex(null)}
                    onMouseMove={(e) => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const ratio = Math.max(0, Math.min(1, (x - padding.left) / (rect.width - padding.left - padding.right)));
                        const idx = Math.round(ratio * (data.length - 1));
                        setHoverIndex(Math.max(0, Math.min(data.length - 1, idx)));
                    }}
                >
                    <defs>
                        <linearGradient id="pnlGradGreen" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stopColor="#4ade80" stopOpacity="0.3" />
                            <stop offset="100%" stopColor="#4ade80" stopOpacity="0" />
                        </linearGradient>
                        <linearGradient id="pnlGradRed" x1="0%" y1="100%" x2="0%" y2="0%">
                            <stop offset="0%" stopColor="#f87171" stopOpacity="0.3" />
                            <stop offset="100%" stopColor="#f87171" stopOpacity="0" />
                        </linearGradient>
                    </defs>

                    {/* Zero line */}
                    <line
                        x1={padding.left}
                        y1={zeroY}
                        x2={width - padding.right}
                        y2={zeroY}
                        stroke="#3f3f46"
                        strokeWidth="1"
                        strokeDasharray="4 4"
                        vectorEffect="non-scaling-stroke"
                    />
                    <text
                        x={width - padding.right + 8}
                        y={zeroY + 4}
                        fill="#71717a"
                        fontSize="11"
                        fontFamily="monospace"
                    >
                        $0
                    </text>

                    {/* Area fill */}
                    <path
                        d={areaPath}
                        fill={isPositive ? 'url(#pnlGradGreen)' : 'url(#pnlGradRed)'}
                        stroke="none"
                    />

                    {/* Line */}
                    <polyline
                        fill="none"
                        stroke={strokeColor}
                        strokeWidth="2"
                        points={points}
                        vectorEffect="non-scaling-stroke"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    />

                    {/* Hover line */}
                    {hoverIndex !== null && (
                        <>
                            <line
                                x1={getX(hoverIndex)}
                                y1={padding.top}
                                x2={getX(hoverIndex)}
                                y2={height - padding.bottom}
                                stroke="#71717a"
                                strokeWidth="1"
                                strokeDasharray="4 4"
                                vectorEffect="non-scaling-stroke"
                            />
                            <circle
                                cx={getX(hoverIndex)}
                                cy={getY(data[hoverIndex].pnl)}
                                r="4"
                                fill={strokeColor}
                                stroke="#18181b"
                                strokeWidth="2"
                                vectorEffect="non-scaling-stroke"
                            />
                        </>
                    )}
                </svg>
            </div>

            <div className="flex justify-between text-[10px] text-zinc-500 font-mono mt-1 uppercase">
                <span>{formatDate(data[0].ts)}</span>
                <span>{formatDate(data[data.length - 1].ts)}</span>
            </div>
        </div>
    );
};
