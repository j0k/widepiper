//Moralis API в JavaScript

// Пример 1: Получение информации о кошельке
async function getWalletInfoExample() {
    try {
        if (!window.moralisAPI) {
            throw new Error('Moralis API not initialized');
        }

        const walletAddress = window.walletManager.account;
        const walletInfo = await window.moralisAPI.getWalletInfo(walletAddress);
        
        console.log('Wallet Info:', walletInfo);
        console.log('MATTER Balance:', walletInfo.matterBalance);
        console.log('IDEA Balance:', walletInfo.ideaBalance);
        console.log('BNB Balance:', walletInfo.bnbBalance);
        console.log('BNB Price (USDT):', walletInfo.bnbPriceUsdt);
        
        return walletInfo;
    } catch (error) {
        console.error('Error getting wallet info:', error);
        throw error;
    }
}

// Пример 2: Получение информации о конкретном токене
async function getTokenInfoExample() {
    try {
        if (!window.moralisAPI) {
            throw new Error('Moralis API not initialized');
        }

        const walletAddress = window.walletManager.account;
        
        // Получение информации о MATTER токене
        const matterInfo = await window.moralisAPI.getMatterInfo(walletAddress);
        console.log('MATTER Info:', matterInfo);
        
        // Получение информации о IDEA токене
        const ideaInfo = await window.moralisAPI.getIdeaInfo(walletAddress);
        console.log('IDEA Info:', ideaInfo);
        
        // Получение информации о BNB
        const bnbInfo = await window.moralisAPI.getBnbInfo(walletAddress);
        console.log('BNB Info:', bnbInfo);
        
        return { matterInfo, ideaInfo, bnbInfo };
    } catch (error) {
        console.error('Error getting token info:', error);
        throw error;
    }
}

// Пример 3: Получение баланса токена
async function getTokenBalanceExample() {
    try {
        if (!window.moralisAPI) {
            throw new Error('Moralis API not initialized');
        }

        const walletAddress = window.walletManager.account;
        
        // Получение баланса MATTER
        const matterBalance = await window.moralisAPI.getMatterBalance(walletAddress);
        console.log('MATTER Balance:', matterBalance);
        
        // Получение баланса IDEA
        const ideaBalance = await window.moralisAPI.getIdeaBalance(walletAddress);
        console.log('IDEA Balance:', ideaBalance);
        
        // Получение баланса BNB
        const bnbBalance = await window.moralisAPI.getBnbBalance(walletAddress);
        console.log('BNB Balance:', bnbBalance);
        
        return { matterBalance, ideaBalance, bnbBalance };
    } catch (error) {
        console.error('Error getting token balances:', error);
        throw error;
    }
}

// Пример 4: Получение цены газа
async function getGasPriceExample() {
    try {
        if (!window.moralisAPI) {
            throw new Error('Moralis API not initialized');
        }

        const gasPriceUsdt = await window.moralisAPI.getGasPriceInUsdt();
        console.log('Gas Price (USDT):', gasPriceUsdt);
        
        return gasPriceUsdt;
    } catch (error) {
        console.error('Error getting gas price:', error);
        throw error;
    }
}

// Пример 5: Получение цены BNB
async function getBnbPriceExample() {
    try {
        if (!window.moralisAPI) {
            throw new Error('Moralis API not initialized');
        }

        const bnbPriceUsdt = await window.moralisAPI.getBnbPriceUsdt();
        console.log('BNB Price (USDT):', bnbPriceUsdt);
        
        return bnbPriceUsdt;
    } catch (error) {
        console.error('Error getting BNB price:', error);
        throw error;
    }
}

// Пример 6: Использование с WalletManager
async function useWithWalletManagerExample() {
    try {
        if (!window.walletManager) {
            throw new Error('WalletManager not available');
        }

        const connectionStatus = window.walletManager.getConnectionStatus();
        if (!connectionStatus.isConnected) {
            throw new Error('Wallet not connected');
        }

        const walletTokensInfo = await window.walletManager.getWalletTokensInfo();
        console.log('Wallet Tokens Info:', walletTokensInfo);

        const gasPrice = await window.walletManager.getGasPriceUsdt();
        console.log('Gas Price:', gasPrice);
        
        const matterInfo = await window.walletManager.getTokenInfo('matter');
        console.log('MATTER Info:', matterInfo);
        
        return { walletTokensInfo, gasPrice, matterInfo };
    } catch (error) {
        console.error('Error using WalletManager with Moralis:', error);
        throw error;
    }
}

// Пример 7: Обновление UI с данными от Moralis
async function updateUIWithMoralisData() {
    try {
        if (!window.walletManager || !window.walletManager.isConnected) {
            console.log('Wallet not connected, skipping UI update');
            return;
        }

        const walletInfo = await window.walletManager.getWalletTokensInfo();
        
        // Обновляем отображение балансов
        updateBalanceDisplay('matter-balance', walletInfo.matterBalance);
        updateBalanceDisplay('idea-balance', walletInfo.ideaBalance);
        updateBalanceDisplay('bnb-balance', walletInfo.bnbBalance);
        
        // Обновляем отображение цен
        updatePriceDisplay('matter-price', walletInfo.matterPriceUsdt);
        updatePriceDisplay('idea-price', walletInfo.ideaPriceUsdt);
        updatePriceDisplay('bnb-price', walletInfo.bnbPriceUsdt);
        
        // Получаем и обновляем цену газа
        const gasPrice = await window.walletManager.getGasPriceUsdt();
        updatePriceDisplay('gas-price', gasPrice);
        
        console.log('UI updated with Moralis data');
    } catch (error) {
        console.error('Error updating UI with Moralis data:', error);
    }
}

function updateBalanceDisplay(elementId, balance) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = balance ? balance.toFixed(6) : '0.000000';
    }
}

function updatePriceDisplay(elementId, price) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = price ? `$${price.toFixed(2)}` : '$0.00';
    }
}

async function robustWalletInfoExample() {
    try {
        if (!window.walletManager || !window.walletManager.isConnected) {
            throw new Error('Wallet not connected');
        }

        let walletInfo = null;
        
        try {
            walletInfo = await window.walletManager.getWalletTokensInfo();
            console.log('Data obtained via Moralis API');
        } catch (moralisError) {
            console.warn('Moralis API failed, trying backend API:', moralisError);
            
            // Fallback к backend API
            try {
                const response = await fetch('/api/v1/wallet/balance/', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.walletManager.getCSRFToken()
                    },
                    credentials: 'same-origin'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    walletInfo = {
                        bnbBalance: data.balance || 0,
                        bnbPriceUsdt: data.balance_usdt / (data.balance || 1) || 0
                    };
                    console.log('Data obtained via backend API');
                } else {
                    throw new Error('Backend API failed');
                }
            } catch (backendError) {
                console.error('Both Moralis and backend API failed:', backendError);
                throw new Error('Unable to get wallet information');
            }
        }
        
        return walletInfo;
    } catch (error) {
        console.error('Error in robust wallet info example:', error);
        throw error;
    }
}

// Экспорт функций для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getWalletInfoExample,
        getTokenInfoExample,
        getTokenBalanceExample,
        getGasPriceExample,
        getBnbPriceExample,
        useWithWalletManagerExample,
        updateUIWithMoralisData,
        robustWalletInfoExample
    };
}
