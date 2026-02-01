const { useState, useEffect } = React;

// --- Utils ---
const formatPrice = (cents) => {
    if (cents === null || cents === undefined) return '-';
    // Kalshi prices are 1-99 cents.
    return `${cents}¢`;
};

const formatDollar = (cents) => {
    if (!cents) return '$0.00';
    return `$${(cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const formatNumber = (num) => {
    if (!num) return '0';
    return num.toLocaleString();
};

const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
        case 'active':
        case 'open':
            return 'border-kalshi-green/50 text-kalshi-green bg-green-900/10';
        case 'closed':
        case 'settled':
        case 'finalized':
            return 'border-zinc-700 text-zinc-500 bg-zinc-800/50';
        default:
            return 'border-zinc-700 text-zinc-500';
    }
};

// --- Components ---

const LandingPage = ({ onSearch }) => {
    const [ticker, setTicker] = useState('');
    const [suggestions, setSuggestions] = useState([]);

    useEffect(() => {
        if (!ticker || ticker.length < 2) {
            setSuggestions([]);
            return;
        }

        const fetchSuggestions = async () => {
            try {
                const res = await fetch(`/api/markets?ticker=${ticker}&limit=5`);
                const data = await res.json();
                setSuggestions(data);
            } catch (e) {
                console.error(e);
            }
        };

        const timer = setTimeout(fetchSuggestions, 300);
        return () => clearTimeout(timer);
    }, [ticker]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (ticker.trim()) onSearch(ticker.trim());
    };

    return (
        <div className="min-h-screen bg-[#0e0e10] flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-md text-center">
                <h1 className="text-4xl font-bold text-white mb-2 tracking-tight">Kalshi Terminal</h1>
                <p className="text-zinc-500 mb-8">Direct Market Access & Analytics</p>

                <div className="relative">
                    <form onSubmit={handleSubmit} className="relative">
                        <input
                            type="text"
                            className="w-full bg-[#18181b] border border-zinc-700 text-white px-6 py-4 rounded-xl shadow-2xl focus:outline-none focus:border-kalshi-green text-lg placeholder-zinc-600 transition-all"
                            placeholder="Enter Ticker (e.g. KXMV...)"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value)}
                            autoFocus
                        />
                        <button
                            type="submit"
                            className="absolute right-3 top-3 bg-kalshi-green text-black font-bold p-2 px-4 rounded-lg hover:bg-emerald-400 transition-colors"
                        >
                            GO
                        </button>
                    </form>

                    {suggestions.length > 0 && (
                        <div className="absolute top-full left-0 right-0 mt-2 bg-[#18181b] border border-zinc-800 rounded-xl shadow-2xl overflow-hidden z-50 text-left">
                            {suggestions.map((m) => (
                                <div
                                    key={m.ticker}
                                    onClick={() => onSearch(m.ticker)}
                                    className="p-4 hover:bg-zinc-800 cursor-pointer border-b border-zinc-800/50 last:border-0"
                                >
                                    <div className="flex justify-between items-center mb-1">
                                        <span className="font-mono text-xs text-zinc-500 bg-zinc-900 px-2 py-0.5 rounded">{m.ticker}</span>
                                        <span className="text-kalshi-green font-mono text-sm">{formatPrice(m.last_price)}</span>
                                    </div>
                                    <div className="text-sm text-zinc-300 truncate">{m.title}</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="mt-8 text-xs text-zinc-600">
                    <p>Try searching for: <span className="text-zinc-500">Fed</span>, <span className="text-zinc-500">S&P</span>, <span className="text-zinc-500">Precipitation</span></p>
                </div>

                <div className="mt-12">
                    <button onClick={() => onSearch(null, 'KXSB')} className="text-zinc-500 hover:text-white underline text-sm">
                        Browse Series Directory
                    </button>
                </div>
            </div>
        </div>
    );
};

const EventList = ({ seriesTicker, onBack, onSelectMarket }) => {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedEvent, setExpandedEvent] = useState(null);
    const [markets, setMarkets] = useState({}); // eventTicker -> markets[]

    useEffect(() => {
        setLoading(true);
        fetch(`/api/series/${seriesTicker}/events`)
            .then(res => res.json())
            .then(data => {
                setEvents(data);
                setLoading(false);
            })
            .catch(e => setLoading(false));
    }, [seriesTicker]);

    const handleExpand = async (event) => {
        if (expandedEvent === event.event_ticker) {
            setExpandedEvent(null);
            return;
        }

        setExpandedEvent(event.event_ticker);
        if (!markets[event.event_ticker]) {
            try {
                const res = await fetch(`/api/events/${event.event_ticker}/markets`);
                const data = await res.json();

                // Sort by volume descending
                data.sort((a, b) => (b.volume_24h || 0) - (a.volume_24h || 0));

                setMarkets(prev => ({ ...prev, [event.event_ticker]: data }));
            } catch (e) {
                console.error(e);
            }
        }
    };

    if (loading) return <div className="p-8 text-zinc-500">Loading Events...</div>;

    return (
        <div className="p-8 max-w-4xl mx-auto">
            <button onClick={onBack} className="mb-6 text-zinc-500 hover:text-white flex items-center gap-2">
                &larr; Back to Search
            </button>
            <h1 className="text-3xl font-bold text-white mb-2">{seriesTicker} Events</h1>
            <p className="text-zinc-500 mb-8">Select an event to view markets</p>

            <div className="flex flex-col gap-3">
                {events.map(e => (
                    <div key={e.event_ticker} className="bg-[#18181b] border border-zinc-800 rounded-xl overflow-hidden">
                        <button
                            onClick={() => handleExpand(e)}
                            className="w-full text-left p-4 hover:bg-[#202023] flex justify-between items-center transition-colors"
                        >
                            <div>
                                <div className="text-white font-medium">{e.title}</div>
                                <div className="text-xs text-zinc-500 mt-1">{e.sub_title}</div>
                            </div>
                            <div className="text-zinc-600">
                                {expandedEvent === e.event_ticker ? '▲' : '▼'}
                            </div>
                        </button>

                        {expandedEvent === e.event_ticker && (
                            <div className="bg-[#111113] border-t border-zinc-800 p-4">
                                {markets[e.event_ticker] ? (
                                    <div className="grid gap-2">
                                        {markets[e.event_ticker].map(m => (
                                            <button
                                                key={m.ticker}
                                                onClick={() => onSelectMarket(m.ticker)}
                                                className={`flex justify-between items-center p-3 rounded bg-[#18181b] hover:bg-zinc-800 border transition-all text-left ${getStatusColor(m.status)}`}
                                            >
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-sm text-zinc-300">{m.subtitle || m.ticker}</span>
                                                        <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase ${getStatusColor(m.status)}`}>{m.status}</span>
                                                    </div>
                                                    <div className="text-xs text-zinc-500 font-mono mt-0.5">Vol: {formatNumber(m.volume_24h)}</div>
                                                </div>
                                                <div className="flex gap-4 text-sm font-mono">
                                                    <div className="text-right">
                                                        <div className="text-[10px] text-zinc-600 uppercase">Yes</div>
                                                        <div className="text-green-400">{formatPrice(m.yes_ask)}</div>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-[10px] text-zinc-600 uppercase">No</div>
                                                        <div className="text-red-400">{formatPrice(m.no_ask)}</div>
                                                    </div>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-zinc-600 text-sm animate-pulse">Loading markets...</div>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

const Orderbook = ({ ticker }) => {
    const [book, setBook] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!ticker) return;
        setLoading(true);
        // Initial fetch
        fetch(`/api/markets/${ticker}/orderbook`)
            .then(res => res.json())
            .then(data => {
                setBook(data);
                setLoading(false);
            })
            .catch(e => setLoading(false));

        const interval = setInterval(() => {
            fetch(`/api/markets/${ticker}/orderbook`)
                .then(res => res.json())
                .then(data => setBook(data))
                .catch(e => { });
        }, 3000);

        return () => clearInterval(interval);
    }, [ticker]);

    if (loading && !book) return <div className="h-full flex items-center justify-center text-zinc-600 text-xs uppercase tracking-wide animate-pulse">Loading Depth...</div>;

    // Safety check mostly for initial state
    const yesLevels = book?.orderbook?.yes || [];
    const noLevels = book?.orderbook?.no || [];

    const topYesBids = [...yesLevels].sort((a, b) => b[0] - a[0]).slice(0, 20);
    const topNoBids = [...noLevels].sort((a, b) => b[0] - a[0]).slice(0, 20);

    return (
        <div className="flex flex-col h-full bg-[#111113] rounded-lg border border-zinc-800 overflow-hidden shadow-xl">
            <div className="px-4 py-3 border-b border-zinc-800 flex justify-between items-center bg-[#131316]">
                <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Depth / Ladder</h3>
                <div className="flex gap-2">
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-kalshi-green"></span><span className="text-[10px] text-zinc-500">YES</span></div>
                    <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-kalshi-red"></span><span className="text-[10px] text-zinc-500">NO</span></div>
                </div>
            </div>

            <div className="grid grid-cols-2 flex-1 overflow-hidden">
                {/* YES SIDE */}
                <div className="border-r border-zinc-800 flex flex-col">
                    <div className="flex justify-between text-[10px] uppercase text-zinc-500 px-3 py-2 bg-zinc-900/50">
                        <span>Bid (Yes)</span>
                        <span>Qty</span>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-1">
                        {topYesBids.map(([price, qty], i) => (
                            <div key={i} className="flex justify-between items-center px-2 py-0.5 mb-px rounded cursor-pointer hover:bg-green-900/10 group">
                                <span className="font-mono text-green-400 text-sm">{price}¢</span>
                                <span className="font-mono text-zinc-400 text-xs group-hover:text-white">{formatNumber(qty)}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* NO SIDE */}
                <div className="flex flex-col">
                    <div className="flex justify-between text-[10px] uppercase text-zinc-500 px-3 py-2 bg-zinc-900/50">
                        <span>Bid (No)</span>
                        <span>Qty</span>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-1">
                        {topNoBids.map(([price, qty], i) => (
                            <div key={i} className="flex justify-between items-center px-2 py-0.5 mb-px rounded cursor-pointer hover:bg-red-900/10 group">
                                <span className="font-mono text-red-400 text-sm">{price}¢</span>
                                <span className="font-mono text-zinc-400 text-xs group-hover:text-white">{formatNumber(qty)}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

const MarketTerminal = ({ ticker, onBack }) => {
    const [market, setMarket] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Fetch detailed market info
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
        <div className="flex-1 flex flex-col h-screen overflow-hidden bg-[#0e0e10]">
            {/* Header */}
            <div className="px-8 py-5 border-b border-zinc-800 bg-[#0e0e10] flex justify-between items-center">
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
                        </div>
                        <div className="flex items-center gap-2 text-xs text-zinc-500 font-mono">
                            <span className="bg-zinc-900 border border-zinc-800 px-1.5 rounded">{market.ticker}</span>
                            <span>•</span>
                            <span className="hidden md:inline">{market.subtitle}</span>
                        </div>
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-3xl font-mono text-white tracking-tight">{formatPrice(market.last_price)}</div>
                    <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">Last Price</div>
                </div>
            </div>

            {/* Main Layout */}
            <div className="flex-1 flex overflow-hidden p-6 gap-6">
                {/* Left Panel: Chart & Stats */}
                <div className="flex-1 flex flex-col min-w-0">

                    {/* Stats Row */}
                    <div className="grid grid-cols-4 gap-4 mb-6">
                        <div className="bg-[#131316] p-4 rounded-xl border border-zinc-800/60">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Volume (24h)</div>
                            <div className="text-xl font-mono text-white">{formatNumber(market.volume_24h)}</div>
                        </div>
                        <div className="bg-[#131316] p-4 rounded-xl border border-zinc-800/60">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">Open Interest</div>
                            <div className="text-xl font-mono text-white">{formatNumber(market.open_interest)}</div>
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

                    {/* Chart Area */}
                    <div className="flex-1 bg-[#111113] rounded-xl border border-zinc-800 flex flex-col items-center justify-center mb-6 relative group overflow-hidden shadow-lg">
                        <div className="absolute inset-0 bg-gradient-to-tr from-kalshi-green/5 to-transparent opacity-20"></div>
                        <div className="z-10 text-center">
                            <span className="text-2xl text-zinc-700 mb-2 block">Chart Component Placeholder</span>
                        </div>
                    </div>

                    {/* Rules Section (Collapsible or truncated) */}
                    <div className="bg-[#131316] p-4 rounded-xl border border-zinc-800/60 max-h-40 overflow-y-auto custom-scrollbar">
                        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-2 sticky top-0 bg-[#131316] pb-2">Market Rules</h3>
                        <div className="text-zinc-500 text-xs leading-relaxed font-sans" dangerouslySetInnerHTML={{ __html: market.rules_primary }}></div>
                    </div>
                </div>

                {/* Right Panel: Orderbook & Execution */}
                <div className="w-[400px] flex flex-col gap-6">
                    <div className="flex-1">
                        <Orderbook ticker={market.ticker} />
                    </div>

                    <div className="bg-[#131316] p-6 rounded-xl border border-zinc-800 shadow-xl">
                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <button className="flex flex-col items-center justify-center bg-green-900/10 border border-green-500/20 text-green-400 font-bold py-4 rounded-lg hover:bg-green-500 hover:text-black hover:scale-[1.02] transition-all group">
                                <span className="text-[10px] uppercase opacity-60 mb-1 group-hover:text-black/70">Buy Yes</span>
                                <span className="text-2xl tracking-tight">{formatPrice(market.yes_ask)}</span>
                            </button>
                            <button className="flex flex-col items-center justify-center bg-red-900/10 border border-red-500/20 text-red-400 font-bold py-4 rounded-lg hover:bg-red-500 hover:text-black hover:scale-[1.02] transition-all group">
                                <span className="text-[10px] uppercase opacity-60 mb-1 group-hover:text-black/70">Buy No</span>
                                <span className="text-2xl tracking-tight">{formatPrice(market.no_ask)}</span>
                            </button>
                        </div>
                        <div className="flex justify-between items-center text-xs text-zinc-500 pt-2 border-t border-zinc-800">
                            <span>Wallet Balance</span>
                            <span className="font-mono text-zinc-300">$0.00</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

const App = () => {
    // URL state management
    const getParams = () => {
        const params = new URLSearchParams(window.location.search);
        return {
            ticker: params.get('ticker'),
            series: params.get('series')
        };
    };

    const [params, setParams] = useState(getParams());

    useEffect(() => {
        const handlePopState = () => setParams(getParams());
        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, []);

    const navigate = (newParams, seriesTicker) => {
        // Handle "Series List" request by just setting series
        if (seriesTicker) {
            const url = `?series=${seriesTicker}`;
            window.history.pushState({}, '', url);
            setParams({ series: seriesTicker });
            return;
        }

        const urlParams = new URLSearchParams();
        if (newParams && newParams.series) urlParams.set('series', newParams.series);
        if (newParams && newParams.ticker) urlParams.set('ticker', newParams.ticker);

        const queryString = urlParams.toString();
        const url = queryString ? `?${queryString}` : '/';

        window.history.pushState({}, '', url);
        setParams(newParams || {});
    };

    return (
        <div className="text-zinc-200 font-sans selection:bg-kalshi-green/30 bg-[#0e0e10] min-h-screen">
            {params.ticker ? (
                <MarketTerminal
                    ticker={params.ticker}
                    onBack={() => navigate(params.series ? { series: params.series } : {})}
                />
            ) : params.series ? (
                <EventList
                    seriesTicker={params.series}
                    onBack={() => navigate({})}
                    onSelectMarket={(ticker) => navigate({ series: params.series, ticker })}
                />
            ) : (
                <LandingPage onSearch={(ticker, series) => navigate(ticker ? { ticker } : {}, series)} />
            )}
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
