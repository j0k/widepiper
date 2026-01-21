function updateWalletBalanceDisplay(isConnected, balance, balanceUsdt) {
    const balanceEl = document.getElementById('wallet-balance');
    const balanceUsdtEl = document.getElementById('wallet-balance-usdt');

    const fmt = (num) => {
        const n = typeof num === 'number' ? num : parseFloat(num || '0');
        if (!isFinite(n)) return '0.0';
        return n.toFixed(1);
    };

    if (balanceEl) {
        balanceEl.textContent = fmt(balance);
    }
    if (balanceUsdtEl) {
        balanceUsdtEl.textContent = `${fmt(balanceUsdt)}$`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    updateWalletBalanceDisplay(false, 0, 0);
});


