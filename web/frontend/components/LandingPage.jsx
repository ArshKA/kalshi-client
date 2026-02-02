const LandingPage = ({ onSearch, onNavigate }) => {
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
        <div className="min-h-screen bg-[#0e0e10] flex flex-col items-center justify-center p-4 relative">
            <div className="absolute top-4 right-4 flex gap-4">
                <button
                    onClick={() => onNavigate && onNavigate('portfolio')}
                    className="text-xs text-zinc-600 hover:text-kalshi-green transition-colors"
                >
                    Portfolio
                </button>
                <button
                    onClick={() => onNavigate && onNavigate('status')}
                    className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
                >
                    Status
                </button>
            </div>
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
