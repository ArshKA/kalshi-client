/**
 * useMarketFeed - Custom hook for real-time market data via WebSocket
 *
 * Manages WebSocket connection to the market feed proxy, handling:
 * - Connection lifecycle and reconnection with exponential backoff
 * - Orderbook state (snapshots + deltas)
 * - Live ticker updates (price, volume, OI, bid/ask)
 * - Connection health metrics (latency, message count, reconnects)
 */
function useMarketFeed(ticker) {
    const [orderbook, setOrderbook] = useState({ yes: [], no: [] });
    const [connected, setConnected] = useState(false);
    const [liveData, setLiveData] = useState({
        price: null,
        volume: null,
        openInterest: null,
        yesBid: null,
        yesAsk: null,
    });

    // Connection health metrics
    const [metrics, setMetrics] = useState({
        latencyMs: null,
        messageCount: 0,
        reconnectCount: 0,
        lastMessageAt: null,
    });

    useEffect(() => {
        if (!ticker) return;

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/market/${ticker}`;

        let ws = null;
        let reconnectTimeout = null;
        let reconnectDelay = 1000;
        const orderbookState = { yes: new Map(), no: new Map() };

        // Track levels pending removal (price -> timeout ID)
        // This prevents jarring shifts when levels briefly go to 0
        const pendingRemovals = { yes: new Map(), no: new Map() };
        const REMOVAL_DELAY_MS = 3000;


        // Debounce display updates to batch rapid deltas together
        let updatePending = false;
        const updateOrderbookDisplay = () => {
            if (updatePending) return;
            updatePending = true;
            requestAnimationFrame(() => {
                setOrderbook({
                    yes: Array.from(orderbookState.yes.entries()),
                    no: Array.from(orderbookState.no.entries())
                });
                updatePending = false;
            });
        };

        const scheduleRemoval = (side, price) => {
            // Cancel any existing pending removal for this level
            const existing = pendingRemovals[side].get(price);
            if (existing) clearTimeout(existing);

            // Schedule removal after delay
            const timeoutId = setTimeout(() => {
                // Only remove if still at 0
                if (orderbookState[side].get(price) === 0) {
                    orderbookState[side].delete(price);
                    updateOrderbookDisplay();
                }
                pendingRemovals[side].delete(price);
            }, REMOVAL_DELAY_MS);

            pendingRemovals[side].set(price, timeoutId);
        };

        const cancelPendingRemoval = (side, price) => {
            const existing = pendingRemovals[side].get(price);
            if (existing) {
                clearTimeout(existing);
                pendingRemovals[side].delete(price);
            }
        };

        const handleMessage = (event) => {
            const receiveTime = Date.now();

            try {
                const data = JSON.parse(event.data);
                const msgType = data.type;
                const msg = data.msg || {};

                // Update metrics on every message
                setMetrics(prev => {
                    const newMetrics = {
                        ...prev,
                        messageCount: prev.messageCount + 1,
                        lastMessageAt: receiveTime,
                    };
                    // Calculate latency if server timestamp is available
                    if (msg.ts) {
                        newMetrics.latencyMs = receiveTime - msg.ts;
                    }
                    return newMetrics;
                });

                if (msgType === 'orderbook_snapshot') {
                    const newYes = new Map((msg.yes || []).map(([p, q]) => [p, q]));
                    const newNo = new Map((msg.no || []).map(([p, q]) => [p, q]));

                    // For levels that exist in old state but not in new (or are 0),
                    // apply delayed removal instead of instant disappearance
                    for (const [price, qty] of orderbookState.yes) {
                        if (qty > 0 && (!newYes.has(price) || newYes.get(price) === 0)) {
                            newYes.set(price, 0);
                            scheduleRemoval('yes', price);
                        }
                    }
                    for (const [price, qty] of orderbookState.no) {
                        if (qty > 0 && (!newNo.has(price) || newNo.get(price) === 0)) {
                            newNo.set(price, 0);
                            scheduleRemoval('no', price);
                        }
                    }

                    // Cancel pending removals for levels that came back
                    for (const [price, qty] of newYes) {
                        if (qty > 0) cancelPendingRemoval('yes', price);
                    }
                    for (const [price, qty] of newNo) {
                        if (qty > 0) cancelPendingRemoval('no', price);
                    }

                    orderbookState.yes = newYes;
                    orderbookState.no = newNo;
                    updateOrderbookDisplay();
                }
                else if (msgType === 'orderbook_delta') {
                    const side = msg.side === 'yes' ? 'yes' : 'no';
                    const currentQty = orderbookState[side].get(msg.price) || 0;
                    const newQty = Math.max(0, currentQty + msg.delta);

                    if (newQty <= 0) {
                        // Set to 0 but don't remove immediately - schedule delayed removal
                        orderbookState[side].set(msg.price, 0);
                        scheduleRemoval(side, msg.price);
                    } else {
                        // Cancel any pending removal if quantity is back
                        cancelPendingRemoval(side, msg.price);
                        orderbookState[side].set(msg.price, newQty);
                    }
                    updateOrderbookDisplay();
                }
                else if (msgType === 'ticker') {
                    setLiveData(prev => ({
                        price: msg.price ?? prev.price,
                        volume: msg.volume ?? prev.volume,
                        openInterest: msg.open_interest ?? prev.openInterest,
                        yesBid: msg.yes_bid ?? prev.yesBid,
                        yesAsk: msg.yes_ask ?? prev.yesAsk,
                    }));
                }
            } catch (e) {
                // Silently ignore malformed messages
            }
        };

        let isFirstConnect = true;

        const connect = () => {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                setConnected(true);
                reconnectDelay = 1000;

                // Clear any pending removals from previous connection
                pendingRemovals.yes.forEach(id => clearTimeout(id));
                pendingRemovals.no.forEach(id => clearTimeout(id));
                pendingRemovals.yes.clear();
                pendingRemovals.no.clear();

                // Track reconnects (not the initial connection)
                if (!isFirstConnect) {
                    setMetrics(prev => ({
                        ...prev,
                        reconnectCount: prev.reconnectCount + 1,
                    }));
                }
                isFirstConnect = false;
            };

            ws.onclose = (e) => {
                setConnected(false);
                if (!e.wasClean) {
                    reconnectTimeout = setTimeout(connect, reconnectDelay);
                    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
                }
            };

            ws.onerror = () => {
                // Error handling - reconnect will be triggered by onclose
            };

            ws.onmessage = handleMessage;
        };

        connect();

        return () => {
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
            if (ws) {
                ws.onclose = null; // Prevent reconnect on intentional close
                ws.close();
            }
            // Clear all pending removal timeouts
            pendingRemovals.yes.forEach(timeoutId => clearTimeout(timeoutId));
            pendingRemovals.no.forEach(timeoutId => clearTimeout(timeoutId));
        };
    }, [ticker]);

    return { orderbook, connected, liveData, metrics };
}
