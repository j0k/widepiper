// BSC Network Configuration
const BSC_CONFIG = {
    chainId: 56,
    chainName: 'Binance Smart Chain',
    nativeCurrency: {
        name: 'BNB',
        symbol: 'BNB',
        decimals: 18,
    },
    rpcUrls: ['https://bsc-dataseed.binance.org/'],
    blockExplorerUrls: ['https://bscscan.com/'],
};

// Configuration constants
const CONFIG = {
    WALLETCONNECT_PROJECT_ID: (typeof window !== 'undefined' && window.WALLETCONNECT_PROJECT_ID) ? window.WALLETCONNECT_PROJECT_ID : '',
    SESSION_TIMEOUT: 24 * 60 * 60 * 1000, // 24 hours
    RECONNECT_DELAY: 100,
    FALLBACK_DELAY: 500,
    DEFAULT_BNB_PRICE: 300,
    // Enable debug mode via window.DEBUG_WALLET or localStorage key 'debugWallet'
    DEBUG_MODE: (typeof window !== 'undefined' && !!window.DEBUG_WALLET) || (() => {
        try {
            const fromLS = !!localStorage.getItem('debugWallet');
            const fromQS = typeof window !== 'undefined' && window.location && window.location.search && window.location.search.includes('debugWallet=1');
            return fromLS || fromQS;
        } catch (_) { return false; }
    })()
};

const debug = {
    log: (...args) => CONFIG.DEBUG_MODE && console.log(...args),
    warn: (...args) => CONFIG.DEBUG_MODE && console.warn(...args),
    error: (...args) => console.error(...args) // Always log errors
};

class WalletManager {
    constructor() {
        this.provider = null;
        this.web3Provider = null;
        this.account = null;
        this.chainId = null;
        this.isConnected = false;
        this.walletConnectProvider = null;
        this.walletBalance = 0;
        this.walletBalanceUsdt = 0;
        this.walletTokensInfo = null;
        this.connectBtnOriginalHTML = null;
        this.connectLiOriginalStyle = null;
        this._consoleRestore = null;
    }

    // Heuristic to detect WalletConnect "expirer" noise errors
    isExpirerError(err) {
        try {
            if (!err) return false;
            const checkString = (s) => typeof s === 'string' && (s.toLowerCase().includes('expirer') || s.toLowerCase().includes('no matching key'));
            if (checkString(err)) return true;
            if (checkString(err?.message)) return true;
            if (err && typeof err === 'object') {
                if (err.context && (err.context === 'core/expirer' || err.context === 'expirer')) return true;
                const str = (typeof err.toString === 'function') ? err.toString() : '';
                if (checkString(str)) return true;
            }
            return false;
        } catch (_) {
            return false;
        }
    }

    // Clear the local WalletConnect storage when damaged/expired sessions
    clearWalletConnectStorage() {
        try {
            const keysToRemove = [];
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (!key) continue;
                if (key.startsWith('@walletconnect')) {
                    keysToRemove.push(key);
                }
            }
            keysToRemove.forEach((k) => localStorage.removeItem(k));
        } catch (e) {
            debug.warn('Failed to clear WalletConnect storage', e);
        }
    }

    // Temporarily suppress expirer noise across console methods
    suppressExpirerConsole() {
        if (this._consoleRestore) return;
        const originalConsole = {
            error: console.error,
            warn: console.warn,
            log: console.log,
            info: console.info,
            debug: console.debug,
        };
        const shouldSkip = (...args) => args.some(a => this.isExpirerError(a));
        console.error = function(...args) {
            if (shouldSkip(...args)) return;
            return originalConsole.error.apply(console, args);
        };
        console.warn = function(...args) {
            if (shouldSkip(...args)) return;
            return originalConsole.warn.apply(console, args);
        };
        console.log = function(...args) {
            if (shouldSkip(...args)) return;
            return originalConsole.log.apply(console, args);
        };
        console.info = function(...args) {
            if (shouldSkip(...args)) return;
            return originalConsole.info.apply(console, args);
        };
        console.debug = function(...args) {
            if (shouldSkip(...args)) return;
            return originalConsole.debug.apply(console, args);
        };
        this._consoleRestore = () => {
            console.error = originalConsole.error;
            console.warn = originalConsole.warn;
            console.log = originalConsole.log;
            console.info = originalConsole.info;
            console.debug = originalConsole.debug;
        };
    }

    restoreConsole() {
        try {
            if (this._consoleRestore) {
                this._consoleRestore();
            }
        } finally {
            this._consoleRestore = null;
        }
    }

    async initWalletConnect() {
        try {
            const WCProvider = window["@walletconnect/ethereum-provider"];
            if (!WCProvider) {
                throw new Error('WalletConnect library not loaded');
            }
            
            let EthereumProvider;
            if (WCProvider.EthereumProvider) {
                EthereumProvider = WCProvider.EthereumProvider;
            } else if (WCProvider.default) {
                EthereumProvider = WCProvider.default;
            } else if (typeof WCProvider === 'function') {
                EthereumProvider = WCProvider;
            } else {
                throw new Error('Cannot find EthereumProvider constructor');
            }
            
            this.walletConnectProvider = await EthereumProvider.init({
                projectId: CONFIG.WALLETCONNECT_PROJECT_ID,
                chains: [BSC_CONFIG.chainId],
                showQrModal: true,
                rpcMap: {
                    [BSC_CONFIG.chainId]: BSC_CONFIG.rpcUrls[0]
                },
                metadata: {
                    name: 'Liquidity App',
                    description: 'Liquidity betting application',
                    url: window.location.origin,
                    icons: []
                },
                disableProviderPing: false,
                relayUrl: 'wss://relay.walletconnect.com',
                storageOptions: {
                    rootStorageKey: '@walletconnect/ethereum-provider'
                }
            });

            debug.log('WalletConnect initialized successfully');
            return true;
        } catch (error) {
            debug.error('Failed to initialize WalletConnect:', error);
            return false;
        }
    }

    async isWalletAvailable() {
        if (!this.walletConnectProvider) {
            return await this.initWalletConnect();
        }
        return true;
    }

    async connect() {
        try {
            debug.log('[wallet] connect() called');
            const isAvailable = await this.isWalletAvailable();
            if (!isAvailable) {
                throw new Error('WalletConnect initialization failed. Please try again.');
            }

            const accounts = await this.walletConnectProvider.enable();
            if (!accounts || accounts.length === 0) {
                throw new Error("No accounts found");
            }

            this.account = accounts[0];
            this.provider = this.walletConnectProvider;
            this.web3Provider = new ethers.providers.Web3Provider(this.walletConnectProvider);
            this.chainId = this.walletConnectProvider.chainId;
            this.isConnected = true;

            await this.updateWalletBalance();

            if (this.chainId !== BSC_CONFIG.chainId) {
                try {
                    await this.switchToBSC();
                } catch (switchError) {
                    debug.warn('Failed to switch to BSC automatically:', switchError);
                }
            }

            this.setupEventListeners();
            debug.log('[wallet] provider enabled', { account: this.account, chainId: this.chainId });

            // Connect wallet to current user account
            this.showLoading('Signature...');
            const connectResult = await this.connectWalletToAccount();
            if (!connectResult.success) {
                throw new Error(connectResult.error);
            }

            this.onWalletConnected(this.account);
            debug.log('[wallet] connected and verified with backend');

            return {
                success: true,
                account: this.account,
                chainId: this.chainId,
                user: connectResult.user
            };

        } catch (error) {
            this.hideLoading();
            if (typeof error?.message === 'string' && error.message.includes('No matching key') && error.message.includes('expirer')) {
                this.clearWalletConnectStorage();
            }
            this.handleConnectionError(error);
            debug.warn('[wallet] connect() failed', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    handleConnectionError(error) {
        if (error.code === 4001 || error.message.includes('User rejected')) {
            this.onWalletError("Connection was rejected by the user");
        } else if (error.message.includes('signature was rejected')) {
            this.onWalletError("Message signature was rejected");
        } else if (error.message.includes('Connection request reset')) {
            return;
        } else {
            this.onWalletError(error.message);
        }
    }

    setupEventListeners() {
        if (!this.walletConnectProvider) return;

        this.walletConnectProvider.on('accountsChanged', (accounts) => {
            debug.log('[wallet] accountsChanged', accounts);
            this.handleAccountsChanged(accounts);
        });

        this.walletConnectProvider.on('chainChanged', (chainId) => {
            debug.log('[wallet] chainChanged', chainId);
            this.handleChainChanged(chainId);
        });

        this.walletConnectProvider.on('disconnect', (error) => {
            debug.warn('[wallet] disconnect event', error);
            this.handleDisconnect();
        });

        this.walletConnectProvider.on('display_uri', (uri) => {
            debug.log('WalletConnect URI generated');
        });
    }

    async disconnect() {
        try {
            if (this.walletConnectProvider && this.isConnected) {
                try {
                    if (typeof this.walletConnectProvider.removeAllListeners === 'function') {
                        this.walletConnectProvider.removeAllListeners('disconnect');
                    }
                } catch (_) {}

                // Suppress expirer noise while disconnecting
                this.suppressExpirerConsole();

                try {
                    debug.log('[wallet] manual disconnect()');
                    await this.walletConnectProvider.disconnect();
                } catch (e) {
                    if (this.isExpirerError(e)) {
                        this.clearWalletConnectStorage();
                    } else {
                        throw e;
                    }
                } finally {
                    // Держим подавление немного дольше, чтобы перехватить отложенные логи WC
                    setTimeout(() => this.restoreConsole(), 800);
                }
            }
            this.handleDisconnect();
        } catch (error) {
            const isExpirerError = this.isExpirerError(error);
            if (!isExpirerError) {
                debug.error("Error disconnecting wallet:", error);
            }
            // When any errors occur, clean up locally and disconnect the state
            this.clearWalletConnectStorage();
            this.handleDisconnect();
        }
    }

    async getBalance(address = null) {
        try {
            if (!this.web3Provider) {
                throw new Error("Wallet not connected");
            }

            const targetAddress = address || this.account;
            const balance = await this.web3Provider.getBalance(targetAddress);
            return ethers.utils.formatEther(balance);
        } catch (error) {
            debug.error("Error getting balance:", error);
            throw error;
        }
    }

    async updateWalletBalance() {
        try {
            if (!this.isConnected) {
                this.resetBalances();
                return;
            }

            // Try Moralis API first
            if (window.moralisAPI && this.account) {
                try {
                    const walletInfo = await window.moralisAPI.getWalletInfo(this.account);
                    this.walletBalance = walletInfo.bnbBalance || 0;
                    this.walletBalanceUsdt = this.walletBalance * walletInfo.bnbPriceUsdt;
                    
                    this.walletTokensInfo = {
                        matter: walletInfo.matter,
                        idea: walletInfo.idea,
                        bnb: walletInfo.bnb,
                        matterBalance: walletInfo.matterBalance,
                        ideaBalance: walletInfo.ideaBalance,
                        matterPriceUsdt: walletInfo.matterPriceUsdt,
                        ideaPriceUsdt: walletInfo.ideaPriceUsdt
                    };
                    
                    this.updateWalletUI();
                    return;
                } catch (moralisError) {
                    debug.warn("Moralis API failed, falling back to backend API");
                }
            }

            // Fallback to backend API
            const response = await fetch('/api/v1/wallet/balance/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                this.walletBalance = data.balance || 0;
                this.walletBalanceUsdt = data.balance_usdt || 0;
            } else {
                // Direct Web3 fallback
                if (this.web3Provider) {
                    const balance = await this.getBalance();
                    this.walletBalance = parseFloat(balance);
                    this.walletBalanceUsdt = this.walletBalance * CONFIG.DEFAULT_BNB_PRICE;
                } else {
                    this.resetBalances();
                }
            }
            
            this.updateWalletUI();
        } catch (error) {
            debug.error("Error updating wallet balance:", error);
            this.resetBalances();
        }
    }

    resetBalances() {
        this.walletBalance = 0;
        this.walletBalanceUsdt = 0;
        this.updateWalletUI();
    }

    updateWalletUI() {
        if (typeof updateWalletBalanceDisplay === 'function') {
            updateWalletBalanceDisplay(this.isConnected, this.walletBalance, this.walletBalanceUsdt);
        }
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (token) return token.value;

        // Fallback: get from cookies
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const trimmed = cookie.trim();
            if (trimmed.startsWith(name + '=')) {
                return decodeURIComponent(trimmed.substring(name.length + 1));
            }
        }
        return '';
    }

    async signMessage(message) {
        try {
            if (!this.web3Provider) {
                throw new Error("Wallet not connected");
            }

            const signer = this.web3Provider.getSigner();
            return await signer.signMessage(message);
        } catch (error) {
            if (error.code === 4001 || error.message.includes('User rejected') || error.message.includes('denied')) {
                throw new Error("Message signature was rejected by user");
            }
            
            if (error.code === -32602) {
                throw new Error("Invalid parameters for signature");
            }
            
            throw new Error(`Signature error: ${error.message}`);
        }
    }

    async connectWalletToAccount() {
        try {
            // Get authentication challenge
            const challengeResponse = await fetch('/api/v1/wallet/auth_challenge/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    wallet_address: this.account
                })
            });

            if (!challengeResponse.ok) {
                const errorData = await challengeResponse.json();
                throw new Error(errorData.error || 'Failed to get authentication challenge');
            }

            const challenge = await challengeResponse.json();
            const signature = await this.signMessage(challenge.message);

            // Connect wallet to current user account
            const connectResponse = await fetch('/api/v1/wallet/connect/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    wallet_address: this.account,
                    signature: signature,
                    message: challenge.message
                })
            });

            if (!connectResponse.ok) {
                const errorData = await connectResponse.json();
                throw new Error(errorData.error || 'Wallet connection failed');
            }

            const connectData = await connectResponse.json();
            
            // Show appropriate message based on whether wallet was already connected
            if (connectData.message.includes("already connected")) {
                this.showSuccess(`Wallet is already connected to your account, ${connectData.user}!`);
            } else {
            }
            
            return {
                success: true,
                user: connectData.user
            };

        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }


    async switchToBSC() {
        try {
            await this.walletConnectProvider.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: `0x${BSC_CONFIG.chainId.toString(16)}` }],
            });
        } catch (error) {
            if (error.code === 4902) {
                await this.addBSCNetwork();
            } else {
                throw error;
            }
        }
    }

    async addBSCNetwork() {
        await this.walletConnectProvider.request({
            method: 'wallet_addEthereumChain',
            params: [{
                chainId: `0x${BSC_CONFIG.chainId.toString(16)}`,
                chainName: BSC_CONFIG.chainName,
                nativeCurrency: BSC_CONFIG.nativeCurrency,
                rpcUrls: BSC_CONFIG.rpcUrls,
                blockExplorerUrls: BSC_CONFIG.blockExplorerUrls
            }],
        });
    }

    handleAccountsChanged(accounts) {
        if (accounts.length === 0) {
            this.handleDisconnect();
        } else if (accounts[0] !== this.account) {
            this.account = accounts[0];
            this.onWalletConnected(this.account);
        }
    }

    handleChainChanged(chainId) {
        this.chainId = parseInt(chainId);
        this.onChainChanged(this.chainId);
    }

    handleDisconnect() {
        debug.warn('[wallet] handleDisconnect()');
        this.account = null;
        this.chainId = null;
        this.isConnected = false;
        this.provider = null;
        this.web3Provider = null;
        this.walletConnectProvider = null;
        this.walletBalance = 0;
        this.walletBalanceUsdt = 0;
        this.hideLoading();
        this.updateWalletUI();
        this.onWalletDisconnected();
        // Гарантированно очищаем мусорные ключи WC
        this.clearWalletConnectStorage();
        const connectBtnAnchor = document.getElementById('connect-wallet-btn');
        if (connectBtnAnchor && this.connectBtnOriginalHTML !== null) {
            connectBtnAnchor.innerHTML = this.connectBtnOriginalHTML;
            connectBtnAnchor.disabled = false;
        }
    }

    // Event handlers
    onWalletConnected(account, isReconnect = false) {
        debug.log('[wallet] onWalletConnected', { account, isReconnect });
        this.updateConnectionStatus(true, account);
        
        if (!isReconnect) {
            this.showSuccess("Wallet connected successfully");
        }
        
        const connectionData = {
            account: account,
            timestamp: Date.now(),
            type: 'walletconnect',
            chainId: this.chainId,
            sessionTopic: this.walletConnectProvider?.session?.topic || null
        };
        
        localStorage.setItem('walletConnection', JSON.stringify(connectionData));
    }

    onWalletDisconnected() {
        debug.warn('[wallet] onWalletDisconnected');
        this.updateConnectionStatus(false, null);
        this.showSuccess("Wallet disconnected successfully");
        localStorage.removeItem('walletConnection');
    }

    onChainChanged(chainId) {
        if (chainId !== BSC_CONFIG.chainId) {
            this.showNetworkWarning();
        }
    }

    onWalletError(error) {
        this.showError(error);
    }

    // UI Methods
    updateConnectionStatus(isConnected, account) {
        const connectBtn = document.getElementById('connect-wallet__li');
        const walletInfo = document.getElementById('wallet-info');
        const disconnectBtn = document.getElementById('disconnect-wallet__li');
        
        if (connectBtn) {
            if (isConnected) {
                connectBtn.style.display = 'none';
                
                if (disconnectBtn) {
                    disconnectBtn.style.display = 'inline-block';
                    disconnectBtn.onclick = () => this.disconnect();
                }
                
                if (walletInfo) {
                    walletInfo.textContent = `${account.slice(0, 6)}...${account.slice(-4)}`;
                    walletInfo.style.display = 'block';
                }
            } else {
                connectBtn.style.display = 'inline-block';
                const connectBtnAnchor = document.getElementById('connect-wallet-btn');
                if (connectBtnAnchor) {
                    if (this.connectBtnOriginalHTML !== null) {
                        connectBtnAnchor.innerHTML = this.connectBtnOriginalHTML;
                    }
                    connectBtnAnchor.disabled = false;
                    connectBtnAnchor.onclick = (e) => {
                        e.preventDefault();
                        this.connect();
                    };
                }
                
                if (disconnectBtn) {
                    disconnectBtn.style.display = 'none';
                    disconnectBtn.onclick = null;
                }
                
                if (walletInfo) {
                    walletInfo.style.display = 'none';
                }
            }
        }
    }

    showLoading(message = 'Connecting...') {
        const connectBtn = document.getElementById('connect-wallet-btn');
        if (connectBtn) {
            if (this.connectBtnOriginalHTML === null) {
                this.connectBtnOriginalHTML = connectBtn.innerHTML;
            }
            connectBtn.innerHTML = `
                <div class="loading-spinner" style="display: inline-block; width: 16px; height: 16px; border: 2px solid #ffffff; border-top: 2px solid transparent; border-radius: 50%; animation: spin 1s linear infinite; margin-right: 8px;"></div>
                ${message}
            `;
            connectBtn.disabled = true;
        }

        // Растягиваем li#connect-wallet__li на весь контейнер
        const connectLi = document.getElementById('connect-wallet__li');
        if (connectLi) {
            if (this.connectLiOriginalStyle === null) {
                this.connectLiOriginalStyle = connectLi.getAttribute('style') || '';
            }
            connectLi.style.position = 'absolute';
            connectLi.style.top = '0';
            connectLi.style.left = '0';
            connectLi.style.right = '0';
            connectLi.style.bottom = '0';
            connectLi.style.pointerEvents = 'none';
        }

        // На этапе подписи показываем кнопку отключения, чтобы можно было отменить
        const disconnectLi = document.getElementById('disconnect-wallet__li');
        const disconnectAnchor = document.getElementById('disconnect-wallet');
        if (disconnectLi && disconnectAnchor) {
            disconnectLi.style.display = 'inline-block';
            disconnectAnchor.onclick = (e) => {
                e.preventDefault();
                this.disconnect();
            };
        }
    }
    
    hideLoading() {
        const connectBtn = document.getElementById('connect-wallet-btn');
        if (connectBtn && !this.isConnected) {
            connectBtn.disabled = false;
            if (this.connectBtnOriginalHTML !== null) {
                connectBtn.innerHTML = this.connectBtnOriginalHTML;
            }
        }

        // Если подключение не завершилось, скрываем кнопку отключения обратно
        if (!this.isConnected) {
            const disconnectLi = document.getElementById('disconnect-wallet__li');
            if (disconnectLi) {
                disconnectLi.style.display = 'none';
            }

            // Восстанавливаем стили li#connect-wallet__li
            const connectLi = document.getElementById('connect-wallet__li');
            if (connectLi) {
                if (this.connectLiOriginalStyle !== null) {
                    if (this.connectLiOriginalStyle.trim() === '') {
                        connectLi.removeAttribute('style');
                    } else {
                        connectLi.setAttribute('style', this.connectLiOriginalStyle);
                    }
                }
            }
        }
    }

    showNetworkWarning() {
        if (document.getElementById('network-warning')) return;

        const warning = document.createElement('div');
        warning.id = 'network-warning';
        warning.className = 'wallet-error';
        warning.style.cssText = 'z-index: -1;';
        warning.innerHTML = '';
        document.body.appendChild(warning);

        setTimeout(() => {
            if (warning.parentNode) {
                warning.remove();
            }
        }, 10000);
    }

    showError(message) {
        this.showNotification(message, 'error', '#ff4757');
    }

    showSuccess(message) {
        this.showNotification(message, 'success', '#2ed573');
    }

    showNotification(message, type, color) {
        const notification = document.createElement('div');
        notification.className = `wallet-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${color};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 10001;
            max-width: 90%;
            text-align: center;
        `;
        notification.innerHTML = `
            <div><strong>${type === 'error' ? 'Error' : 'Success'}</strong></div>
            <div style="margin-top: 5px;">${message}</div>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, type === 'error' ? 5000 : 3000);
    }

    // API Methods
    getConnectionStatus() {
        return {
            isConnected: this.isConnected,
            account: this.account,
            chainId: this.chainId,
            walletBalance: this.walletBalance || 0,
            walletBalanceUsdt: this.walletBalanceUsdt || 0,
            walletTokensInfo: this.walletTokensInfo || null
        };
    }

    async getWalletTokensInfo() {
        if (!this.isConnected || !this.account) {
            throw new Error('Wallet not connected');
        }

        if (!window.moralisAPI) {
            throw new Error('Moralis API not available');
        }

        return await window.moralisAPI.getWalletInfo(this.account);
    }

    async getGasPriceUsdt() {
        if (!window.moralisAPI) {
            throw new Error('Moralis API not available');
        }
        return await window.moralisAPI.getGasPriceInUsdt();
    }

    async getTokenInfo(tokenType) {
        if (!this.isConnected || !this.account) {
            throw new Error('Wallet not connected');
        }

        if (!window.moralisAPI) {
            throw new Error('Moralis API not available');
        }

        const tokenMethods = {
            matter: 'getMatterInfo',
            idea: 'getIdeaInfo',
            bnb: 'getBnbInfo'
        };

        const methodName = tokenMethods[tokenType.toLowerCase()];
        if (!methodName) {
            throw new Error(`Unknown token type: ${tokenType}`);
        }

        return await window.moralisAPI[methodName](this.account);
    }

    async getTokenBalance(tokenType) {
        if (!this.isConnected || !this.account) {
            throw new Error('Wallet not connected');
        }

        if (!window.moralisAPI) {
            throw new Error('Moralis API not available');
        }

        const balanceMethods = {
            matter: 'getMatterBalance',
            idea: 'getIdeaBalance',
            bnb: 'getBnbBalance'
        };

        const methodName = balanceMethods[tokenType.toLowerCase()];
        if (!methodName) {
            throw new Error(`Unknown token type: ${tokenType}`);
        }

        return await window.moralisAPI[methodName](this.account);
    }

    // Auto-reconnect functionality
    async autoReconnect() {
        try {
            const storedConnection = localStorage.getItem('walletConnection');
            if (!storedConnection) {
                return false;
            }
    
            const connectionData = JSON.parse(storedConnection);
            
            // Check if connection is not too old
            if (Date.now() - connectionData.timestamp > CONFIG.SESSION_TIMEOUT) {
                localStorage.removeItem('walletConnection');
                return false;
            }
    
            // Only auto-reconnect WalletConnect sessions
            if (connectionData.type !== 'walletconnect') {
                return false;
            }
    
            const isAvailable = await this.isWalletAvailable();
            if (!isAvailable) {
                return false;
            }
    
            // Check if there's an active session
            if (this.walletConnectProvider && this.walletConnectProvider.session) {
                const currentSessionTopic = this.walletConnectProvider.session.topic;
                if (connectionData.sessionTopic && connectionData.sessionTopic !== currentSessionTopic) {
                    localStorage.removeItem('walletConnection');
                    return false;
                }
                
                const accounts = this.walletConnectProvider.accounts;
                if (accounts && accounts.length > 0) {
                    if (connectionData.account && accounts[0].toLowerCase() !== connectionData.account.toLowerCase()) {
                        localStorage.removeItem('walletConnection');
                        return false;
                    }
                    
                    // Restore connection state
                    this.account = accounts[0];
                    this.provider = this.walletConnectProvider;
                    this.web3Provider = new ethers.providers.Web3Provider(this.walletConnectProvider);
                    this.chainId = this.walletConnectProvider.chainId;
                    this.isConnected = true;
    
                    this.setupEventListeners();
                    debug.log('[wallet] autoReconnect restored session', { account: this.account, chainId: this.chainId });
                    await this.updateWalletBalance();
                    
                    // For auto-reconnect, we assume the session is still valid
                    // The backend will handle authentication when needed
                    this.onWalletConnected(this.account, true);
                    return true;
                } else {
                    localStorage.removeItem('walletConnection');
                    return false;
                }
            } else {
                localStorage.removeItem('walletConnection');
                return false;
            }
        } catch (error) {
            debug.error("Auto-reconnect failed:", error);
            localStorage.removeItem('walletConnection');
            return false;
        }
    }
}

// Initialize global wallet manager
const walletManager = new WalletManager();
// Expose for debugging
try { window.walletManager = walletManager; } catch (_) {}

// Navigation diagnostics: log before navigation and after load
document.addEventListener('click', (e) => {
    try {
        const a = e.target.closest && e.target.closest('a[href]');
        if (!a) return;
        const href = a.getAttribute('href');
        if (!href) return;
        const status = walletManager.getConnectionStatus();
        debug.log('[nav] navigating to', href, 'status=', status);
    } catch (_) {}
}, true);

// Persist status before page unload and print on next load
window.addEventListener('beforeunload', () => {
    try {
        const status = walletManager.getConnectionStatus();
        const payload = {
            ts: Date.now(),
            url: window.location.pathname,
            status
        };
        localStorage.setItem('walletDiag:last', JSON.stringify(payload));
    } catch (_) {}
});

document.addEventListener('DOMContentLoaded', () => {
    try {
        if (!CONFIG.DEBUG_MODE) return;
        const raw = localStorage.getItem('walletDiag:last');
        if (raw) {
            const data = JSON.parse(raw);
            console.log('[nav] last page status', data);
        }
        console.log('[wallet] debug enabled');
    } catch (_) {}
});

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    const navWalletLink = document.querySelector('.wallet-icon#connect-wallet-btn');
    if (navWalletLink) {
        navWalletLink.addEventListener('click', function(e) {
            e.preventDefault();
            walletManager.connect();
        });
    }
    
    const navDisconnectLink = document.querySelector('.wallet-icon#disconnect-wallet');
    if (navDisconnectLink) {
        navDisconnectLink.addEventListener('click', function(e) {
            e.preventDefault();
            walletManager.disconnect();
        });
    }
});

// Initialize wallet connection
async function initializeWalletConnection() {
    await new Promise(resolve => setTimeout(resolve, CONFIG.RECONNECT_DELAY));
    
    try {
        const reconnected = await walletManager.autoReconnect();
        debug.log(reconnected ? "Auto-reconnected successfully" : "No existing connection to restore");
    } catch (error) {
        debug.error("Error during auto-reconnect:", error);
    }
}

// Multiple initialization strategies
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeWalletConnection);
} else if (document.readyState === 'interactive') {
    setTimeout(initializeWalletConnection, CONFIG.RECONNECT_DELAY);
} else {
    initializeWalletConnection();
}

// Fallback initialization
window.addEventListener('load', () => {
    if (!walletManager.isConnected) {
        setTimeout(initializeWalletConnection, CONFIG.FALLBACK_DELAY);
    }
});