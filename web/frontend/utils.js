// Destructure React hooks for use in all components
const { useState, useEffect, useRef, useMemo, useCallback } = React;

const formatPrice = (cents) => {
    if (cents === null || cents === undefined) return '-';
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
