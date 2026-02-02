/**
 * MarketTerminal Component
 *
 * Main market detail page with real-time WebSocket updates for:
 * - Order book (via orderbook_snapshot + orderbook_delta)
 * - Price/Volume/OI (via ticker channel)
 */
const MarketTerminal = ({ ticker, onBack }) => {
    const [market, setMarket] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Real-time data from WebSocket
    const { orderbook, connected: wsConnected, liveData } = useMarketFeed(ticker);

    // Fetch initial market data
    useEffect(() => {
        fetch(`/api/markets/${ticker}`)
            .then(async res => {
                if (!res.ok) throw new Error('Market not found');
                return res.json();
            })
            .then(data => {
                setMarket(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setError(err.message);
                setLoading(false);
            });
    }, [ticker]);

    // Use live values if available, otherwise fall back to initial market data
    const displayPrice = liveData.price ?? market?.last_price;
    const displayVolume = liveData.volume ?? market?.volume_24h;
    const displayOI = liveData.openInterest ?? market?.open_interest;
    const displayYesAsk = liveData.yesAsk ?? market?.yes_ask;
    const displayNoBid = liveData.yesBid ? (100 - liveData.yesBid) : market?.no_ask;

    if (loading) return (
        <div className="h-screen bg-[#0e0e10] flex items-center justify-center flex-col">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-kalshi-green mb-4"></div>
            <div className="text-zinc-500 text-sm">Loading Terminal for {ticker}...</div>
        </div>
    );

    if (error) return (
        <div className="h-screen bg-[#0e0e10] flex items-center justify-center flex-col">
            <h2 className="text-red-500 text-xl font-bold mb-2">Error Loading Market</h2>
            <p className="text-zinc-500 mb-4">{error}</p>
            <button onClick={onBack} className="text-white bg-zinc-800 px-4 py-2 rounded">Back to Search</button>
        </div>
    );

    return (
        <div className="flex-1 flex flex-col min-h-screen bg-[#0e0e10]">
            {/* Header */}
            <div className="px-8 py-5 border-b border-zinc-800 bg-[#0e0e10] flex justify-between items-center sticky top-0 z-50">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onBack}
                        className="p-2 rounded-full hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
                        title="Back to Search"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5" /><path d="M12 19l-7-7 7-7" /></svg>
                    </button>
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <h1 className="text-xl md:text-2xl font-bold text-white leading-tight truncate max-w-2xl">{market.title}</h1>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${market.status === 'active' || market.status === 'open'
                                ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                                : 'bg-zinc-800 text-zinc-500 border border-zinc-700'
                                }`}>
                                {market.status}
                            </span>
                            {/* Live indicator */}
                            {wsConnected && (
                                <span className="flex items-center gap-1 text-[10px] text-green-400">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
                                    LIVE
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-zinc-500 font-mono">
                            <span className="bg-zinc-900 border border-zinc-800 px-1.5 rounded">{market.ticker}</span>
                            <span>•</span>
                            <span className="hidden md:inline">{market.subtitle}</span>
                        </div>
                    </div>
                </div>
                <div className="text-right">
                    <div className={`text-3xl font-mono tracking-tight transition-colors ${wsConnected ? 'text-white' : 'text-zinc-400'}`}>
                        {formatPrice(displayPrice)}
                    </div>
                    <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">Last Price</div>
                </div>
            </div>

            <div className="flex-1 flex flex-col lg:flex-row p-6 gap-6">
                {/* Left Column - Stats, Chart, Rules */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Stats Grid */}
                    <div className="grid grid-cols-4 gap-4 mb-6">
                        <div className="bg-[#131316] p-4 rounded-xl border border-zinc-800/60">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Volume (24h)</div>
                            <div className={`text-xl font-mono ${wsConnected ? 'text-white' : 'text-zinc-400'}`}>
                                {formatNumber(displayVolume)}
                            </div>
                        </div>
                        <div className="bg-[#131316] p-4 rounded-xl border border-zinc-800/60">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Open Interest</div>
                            <div className={`text-xl font-mono ${wsConnected ? 'text-white' : 'text-zinc-400'}`}>
                                {formatNumber(displayOI)}
                            </div>
                        </div>
                        <div className="bg-[#131316] p-4 rounded-xl border border-zinc-800/60">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Liquidity</div>
                            <div className="text-xl font-mono text-green-400">{formatDollar(market.liquidity)}</div>
                        </div>
                        <div className="bg-[#131316] p-4 rounded-xl border border-zinc-800/60">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Expiration</div>
                            <div className="text-sm font-mono text-white truncate">
                                {new Date(market.expiration_time).toLocaleDateString()}
                            </div>
                        </div>
                    </div>

                    {/* Price Chart */}
                    <div className="bg-[#111113] rounded-xl border border-zinc-800 flex flex-col mb-6 relative group overflow-hidden shadow-lg h-[500px]">
                        <SimpleChart ticker={market.ticker} />
                    </div>

                    {/* Market Rules */}
                    <div className="bg-[#131316] p-4 rounded-xl border border-zinc-800/60 max-h-40 overflow-y-auto custom-scrollbar">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-2 sticky top-0 bg-[#131316] pb-2">Market Rules</h3>
                        <div className="text-zinc-500 text-xs leading-relaxed font-sans" dangerouslySetInnerHTML={{ __html: market.rules_primary }}></div>
                    </div>
                </div>

                {/* Right Column - Orderbook and Trade Panel */}
                <div className="w-[400px] flex flex-col gap-6">
                    {/* Orderbook - now receives data from WebSocket */}
                    <div className="flex-1">
                        <Orderbook book={orderbook} connected={wsConnected} />
                    </div>

                    {/* Trade Panel */}
                    <div className="bg-[#131316] p-6 rounded-xl border border-zinc-800 shadow-xl">
                        <div className="grid grid-cols-2 gap-4">
                            <button className="flex flex-col items-center justify-center bg-green-900/10 border border-green-500/20 text-green-400 font-bold py-4 rounded-lg hover:bg-green-500 hover:text-black hover:scale-[1.02] transition-all group">
                                <span className="text-[10px] uppercase opacity-60 mb-1 group-hover:text-black/70">Buy Yes</span>
                                <span className="text-2xl tracking-tight">{formatPrice(displayYesAsk)}</span>
                            </button>
                            <button className="flex flex-col items-center justify-center bg-red-900/10 border border-red-500/20 text-red-400 font-bold py-4 rounded-lg hover:bg-red-500 hover:text-black hover:scale-[1.02] transition-all group">
                                <span className="text-[10px] uppercase opacity-60 mb-1 group-hover:text-black/70">Buy No</span>
                                <span className="text-2xl tracking-tight">{formatPrice(displayNoBid)}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
