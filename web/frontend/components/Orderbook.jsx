/**
 * Orderbook Display Component
 *
 * Pure display component that renders the order book depth ladder.
 * Receives orderbook data as a prop from parent component.
 */
const Orderbook = ({ book, connected }) => {
    const yesLevels = book?.yes || [];
    const noLevels = book?.no || [];

    // Sort by price descending (highest first)
    const topYesBids = [...yesLevels].sort((a, b) => b[0] - a[0]);
    const topNoBids = [...noLevels].sort((a, b) => b[0] - a[0]);

    // Filter out 0-quantity levels for analytics only (they're pending removal)
    const activeYesBids = topYesBids.filter(([_, qty]) => qty > 0);
    const activeNoBids = topNoBids.filter(([_, qty]) => qty > 0);

    // Calculate analytics from active levels only
    const bestYesBid = activeYesBids.length > 0 ? activeYesBids[0][0] : null;
    const bestNoBid = activeNoBids.length > 0 ? activeNoBids[0][0] : null;
    const bestYesAsk = bestNoBid !== null ? 100 - bestNoBid : null;

    const spread = (bestYesBid !== null && bestYesAsk !== null) ? bestYesAsk - bestYesBid : null;
    const mid = (bestYesBid !== null && bestYesAsk !== null) ? (bestYesBid + bestYesAsk) / 2 : null;

    // Imbalance: (yes_depth - no_depth) / total (using active levels only)
    const yesDepth = activeYesBids.reduce((sum, [_, qty]) => sum + qty, 0);
    const noDepth = activeNoBids.reduce((sum, [_, qty]) => sum + qty, 0);
    const totalDepth = yesDepth + noDepth;
    const imbalance = totalDepth > 0 ? (yesDepth - noDepth) / totalDepth : 0;

    return (
        <div className="flex flex-col h-full bg-[#111113] rounded-lg border border-zinc-800 overflow-hidden shadow-xl">
            <div className="px-4 py-3 border-b border-zinc-800 flex justify-between items-center bg-[#131316]">
                <div className="flex items-center gap-2">
                    <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Depth / Ladder</h3>
                    {connected !== undefined && (
                        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-zinc-600'}`}
                              title={connected ? 'Live' : 'Connecting...'}></span>
                    )}
                </div>
                <div className="flex gap-2">
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-kalshi-green"></span>
                        <span className="text-[10px] text-zinc-500">YES</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-kalshi-red"></span>
                        <span className="text-[10px] text-zinc-500">NO</span>
                    </div>
                </div>
            </div>

            {/* Analytics Row */}
            <div className="grid grid-cols-3 gap-2 px-3 py-2 border-b border-zinc-800 bg-zinc-900/30">
                <div className="text-center">
                    <div className="text-[9px] text-zinc-500 uppercase">Mid</div>
                    <div className="font-mono text-sm text-white">{mid !== null ? `${mid.toFixed(1)}¢` : '—'}</div>
                </div>
                <div className="text-center">
                    <div className="text-[9px] text-zinc-500 uppercase">Spread</div>
                    <div className="font-mono text-sm text-white">{spread !== null ? `${spread}¢` : '—'}</div>
                </div>
                <div className="text-center">
                    <div className="text-[9px] text-zinc-500 uppercase">Imbalance</div>
                    <div className={`font-mono text-sm ${imbalance > 0.1 ? 'text-green-400' : imbalance < -0.1 ? 'text-red-400' : 'text-zinc-400'}`}>
                        {totalDepth > 0 ? `${(imbalance * 100).toFixed(0)}%` : '—'}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 flex-1 overflow-hidden">
                {/* YES Bids Column */}
                <div className="border-r border-zinc-800 flex flex-col">
                    <div className="flex justify-between text-[10px] uppercase text-zinc-500 px-3 py-2 bg-zinc-900/50">
                        <span>Bid (Yes)</span>
                        <span>Qty</span>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-1">
                        {topYesBids.length === 0 ? (
                            <div className="text-zinc-600 text-xs text-center py-4">No bids</div>
                        ) : (
                            topYesBids.map(([price, qty], i) => (
                                <div key={`yes-${price}`}
                                     className={`flex justify-between items-center px-2 py-0.5 mb-px rounded cursor-pointer hover:bg-green-900/10 group transition-opacity duration-300 ${qty === 0 ? 'opacity-25' : ''}`}>
                                    <span className="font-mono text-green-400 text-sm">{price}¢</span>
                                    <span className="font-mono text-zinc-400 text-xs group-hover:text-white">{formatNumber(qty)}</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* NO Bids Column */}
                <div className="flex flex-col">
                    <div className="flex justify-between text-[10px] uppercase text-zinc-500 px-3 py-2 bg-zinc-900/50">
                        <span>Bid (No)</span>
                        <span>Qty</span>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-1">
                        {topNoBids.length === 0 ? (
                            <div className="text-zinc-600 text-xs text-center py-4">No bids</div>
                        ) : (
                            topNoBids.map(([price, qty], i) => (
                                <div key={`no-${price}`}
                                     className={`flex justify-between items-center px-2 py-0.5 mb-px rounded cursor-pointer hover:bg-red-900/10 group transition-opacity duration-300 ${qty === 0 ? 'opacity-25' : ''}`}>
                                    <span className="font-mono text-red-400 text-sm">{price}¢</span>
                                    <span className="font-mono text-zinc-400 text-xs group-hover:text-white">{formatNumber(qty)}</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
