const { useState, useEffect } = React;

const App = () => {
    const getParams = () => {
        const params = new URLSearchParams(window.location.search);
        return {
            ticker: params.get('ticker'),
            series: params.get('series') ? params.get('series').toUpperCase() : null,
            page: params.get('page'),
        };
    };

    const [params, setParams] = useState(getParams());

    useEffect(() => {
        const handlePopState = () => setParams(getParams());
        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, []);

    const navigate = (newParams, seriesTicker) => {
        if (seriesTicker) {
            const url = `?series=${seriesTicker}`;
            window.history.pushState({}, '', url);
            setParams({ series: seriesTicker });
            return;
        }

        const urlParams = new URLSearchParams();
        if (newParams && newParams.series) urlParams.set('series', newParams.series);
        if (newParams && newParams.ticker) urlParams.set('ticker', newParams.ticker);
        if (newParams && newParams.page) urlParams.set('page', newParams.page);

        const queryString = urlParams.toString();
        const url = queryString ? `?${queryString}` : '/';

        window.history.pushState({}, '', url);
        setParams(newParams || {});
    };

    return (
        <div className="text-zinc-200 font-sans selection:bg-kalshi-green/30 bg-[#0e0e10] min-h-screen">
            {params.page === 'status' ? (
                <StatusPage onBack={() => navigate({})} />
            ) : params.page === 'portfolio' ? (
                <PortfolioPage
                    onBack={() => navigate({})}
                    onSelectMarket={(ticker) => navigate({ ticker })}
                />
            ) : params.ticker ? (
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
                <LandingPage
                    onSearch={(ticker, series) => navigate(ticker ? { ticker } : {}, series)}
                    onNavigate={(page) => navigate({ page })}
                />
            )}
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
