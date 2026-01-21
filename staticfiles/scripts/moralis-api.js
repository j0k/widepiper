//Moralis API Client для работы с блокчейн данными

function checkDependencies() {
    if (!window.ethers) {
        console.error('Ethers.js not loaded');
        return false;
    }
    return true;
}

class MoralisAPI {
    constructor() {
        // API key should be configured via init() method or loaded from backend
        this.apiKey = null;
        this.baseUrl = 'https://deep-index.moralis.io/api/v2.2';
        this.chain = 'bsc';
        
        // Check dependencies when creating
        if (!checkDependencies()) {
            console.warn('Some dependencies not loaded, some features may not work');
        }
    }

    /**
     * Initialize API key
     * @param {string} apiKey - Moralis API ключ
     */
    init(apiKey) {
        this.apiKey = apiKey;
        if (!window.MATTER_TOKEN_ADDRESS || !window.IDEA_TOKEN_ADDRESS) {
            console.error('Token addresses not configured properly');
        }
    }

    /**
     * Execute HTTP request to Moralis API
     * @param {string} endpoint
     * @param {Object} params
     * @returns {Promise<Object>}
     */
    async makeRequest(endpoint, params = {}) {
        if (!this.apiKey) {
            throw new Error('Moralis API key not initialized');
        }

        const url = new URL(`${this.baseUrl}${endpoint}`);
        
        if (params && typeof params === 'object') {
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined) {
                    url.searchParams.append(key, params[key]);
                }
            });
        }

        try {
            const response = await fetch(url.toString(), {
                method: 'GET',
                headers: {
                    'X-API-Key': this.apiKey,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Moralis API error: ${response.status} - ${errorData.message || response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Moralis API request failed:', error);
            throw error;
        }
    }

    /**
     * Get all tokens of the wallet with prices
     * @param {string} walletAddress
     * @returns {Promise<Array>}
     */
    async getWalletTokenBalances(walletAddress) {
        try {
            const params = {
                chain: this.chain,
                address: walletAddress,
                // Add cache busting
                _t: Date.now()
            };

            // Add cache busting parameter
            const result = await this.makeRequest(`/${walletAddress}/erc20`, params);
            return (result && Array.isArray(result)) ? result : [];
        } catch (error) {
            console.warn('Moralis API error getting wallet token balances:', error);
            // If it's a rate limit error, log it specifically
            if (error.message && error.message.includes('401')) {
                console.error('Moralis API rate limit exceeded. Please upgrade your plan or wait for reset.');
            }
            return [];
        }
    }

        /**
     * Get native balance of BNB
     * @param {string} walletAddress
     * @returns {Promise<Object>}
     */
    async getNativeBalance(walletAddress) {
        try {
            console.log('Getting native balance for address:', walletAddress);
            const params = {
                chain: this.chain
            };

            const result = await this.makeRequest(`/${walletAddress}/balance`, params);
            console.log('Native balance result:', result);
            
            if (result && result.balance) {
                const balanceWei = result.balance;
                const balanceEther = parseFloat(balanceWei) / Math.pow(10, 18);
                console.log('Balance Wei:', balanceWei, 'Balance Ether:', balanceEther);
                
                return {
                    balance: balanceWei,
                    balance_formatted: balanceEther.toString()
                };
            }
            
            return { balance: '0', balance_formatted: '0' };
        } catch (error) {
            console.warn('Error getting native balance, returning zero:', error);
            return { balance: '0', balance_formatted: '0' };
        }
    }

    /**
     * Get information about a specific token in the wallet
     * @param {string} walletAddress
     * @param {string} tokenAddress
     * @returns {Promise<Object|null>}
     */
    async getTokenInfo(walletAddress, tokenAddress) {
        try {
            const tokens = await this.getWalletTokenBalances(walletAddress);
            
            // Normalize token address for comparison
            const normalizedTokenAddress = this.normalizeAddress(tokenAddress);
            
            for (const token of tokens) {
                if (this.normalizeAddress(token.token_address) === normalizedTokenAddress) {
                    return token;
                }
            }
            
            return null;
        } catch (error) {
            console.warn('Error getting token info, returning null:', error);
            return null;
        }
    }

    /**
     * Get information about the MATTER token
     * @param {string} walletAddress
     * @returns {Promise<Object|null>}
     */
    async getMatterInfo(walletAddress) {
        const MATTER_TOKEN_ADDRESS = window.MATTER_TOKEN_ADDRESS;
        if (!MATTER_TOKEN_ADDRESS) {
            console.error('MATTER_TOKEN_ADDRESS not configured');
            return null;
        }
        return await this.getTokenInfo(walletAddress, MATTER_TOKEN_ADDRESS);
    }

    /**
     * Get information about the IDEA token
     * @param {string} walletAddress
     * @returns {Promise<Object|null>}
     */
    async getIdeaInfo(walletAddress) {
        const IDEA_TOKEN_ADDRESS = window.IDEA_TOKEN_ADDRESS;
        if (!IDEA_TOKEN_ADDRESS) {
            console.error('IDEA_TOKEN_ADDRESS not configured');
            return null;
        }
        return await this.getTokenInfo(walletAddress, IDEA_TOKEN_ADDRESS);
    }

    /**
     * Get information about the BNB token
     * @param {string} walletAddress
     * @returns {Promise<Object|null>}
     */
    async getBnbInfo(walletAddress) {
        try {
            // Get native balance of BNB
            const nativeBalance = await this.getNativeBalance(walletAddress);
            
            // Get price of BNB
            const bnbPrice = await this.getBnbPriceUsdt();
            
            // Moralis API already returns formatted values
            const balanceFormatted = parseFloat(nativeBalance.balance_formatted || '0');
            
            return {
                symbol: 'BNB',
                name: 'Binance Coin',
                balance: nativeBalance.balance || '0',
                balance_formatted: balanceFormatted.toString(),
                usd_price: bnbPrice.toString(),
                usd_value: (balanceFormatted * bnbPrice).toString(),
                token_address: null,
                decimals: 18
            };
        } catch (error) {
            console.error('Error getting BNB info:', error);
            // Return safe default values
            return {
                symbol: 'BNB',
                name: 'Binance Coin',
                balance: '0',
                balance_formatted: '0',
                usd_price: '0',
                usd_value: '0',
                token_address: null,
                decimals: 18
            };
        }
    }

    /**
     * Get information about stablecoins (USDT, USDC, BUSD, DAI)
     * @param {string} walletAddress
     * @returns {Promise<Object|null>}
     */
    async getUsdtInfo(walletAddress) {
        try {
            // Get all tokens and find stablecoins
            const tokens = await this.getWalletTokenBalances(walletAddress);
            const stablecoins = ['USDT', 'USDC', 'BUSD', 'DAI'];
            
            let totalUsdtValue = 0;
            let usdtToken = null;
            
            for (const token of tokens) {
                if (token.symbol && stablecoins.includes(token.symbol.toUpperCase())) {
                    const balance = parseFloat(token.balance_formatted || 0);
                    const usdValue = parseFloat(token.usd_value || 0);
                    
                    // Only log if there's actually a balance
                    if (balance > 0) {
                        console.log(`Found ${token.symbol}: ${balance} tokens, $${usdValue} USD`);
                    }
                    
                    // If usd_value is 0 but balance > 0, calculate manually
                    let actualUsdValue = usdValue;
                    if (usdValue === 0 && balance > 0) {
                        // For stablecoins, assume 1:1 USD ratio
                        actualUsdValue = balance;
                        console.log(`Calculated USD value for ${token.symbol}: ${actualUsdValue}`);
                    }
                    
                    totalUsdtValue += actualUsdValue;
                    
                    // Use the first USDT token as primary, or the one with highest balance
                    if (!usdtToken || (token.symbol.toUpperCase() === 'USDT' && balance > 0)) {
                        usdtToken = {
                            ...token,
                            totalUsdValue: totalUsdtValue,
                            calculatedUsdValue: actualUsdValue
                        };
                    }
                }
            }
            
            if (usdtToken) {
                console.log('Primary stablecoin token:', usdtToken);
                return usdtToken;
            }
            
            console.log('No stablecoins found in wallet');
            return null;
        } catch (error) {
            console.warn('Error getting stablecoin info:', error);
            return null;
        }
    }

    /**
     * Get the balance of the MATTER token
     * @param {string} walletAddress
     * @returns {Promise<string|null>}
     */
    async getMatterBalance(walletAddress) {
        try {
            const matterInfo = await this.getMatterInfo(walletAddress);
            return matterInfo ? matterInfo.balance_formatted : null;
        } catch (error) {
            console.warn('Error getting MATTER balance, returning 0:', error);
            return '0';
        }
    }

    /**
     * Get the balance of the IDEA token
     * @param {string} walletAddress
     * @returns {Promise<string|null>}
     */
    async getIdeaBalance(walletAddress) {
        try {
            const ideaInfo = await this.getIdeaInfo(walletAddress);
            return ideaInfo ? ideaInfo.balance_formatted : null;
        } catch (error) {
            console.warn('Error getting IDEA balance, returning 0:', error);
            return '0';
        }
    }

    /**
     * Get the balance of the BNB token
     * @param {string} walletAddress
     * @returns {Promise<string|null>}
     */
    async getBnbBalance(walletAddress) {
        try {
            const bnbInfo = await this.getBnbInfo(walletAddress);
            return bnbInfo ? bnbInfo.balance_formatted : null;
        } catch (error) {
            console.warn('Error getting BNB balance, returning 0:', error);
            return '0';
        }
    }

    /**
     * Get the price of the gas in USDT
     * @returns {Promise<number>}
     */
    async getGasPriceInUsdt() {
        try {
            // Get the price of the gas through BSC RPC
            const bscUrls = [
                'https://bsc-dataseed.binance.org/',
                'https://bsc-dataseed1.binance.org/',
                'https://bsc-dataseed2.binance.org/',
                'https://bsc-dataseed3.binance.org/',
                'https://bsc-dataseed4.binance.org/'
            ];

            let gasPriceWei = null;
            
            for (const url of bscUrls) {
                try {
                    const response = await fetch(url, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            jsonrpc: '2.0',
                            method: 'eth_gasPrice',
                            params: [],
                            id: 1
                        })
                    });

                    if (response.ok) {
                        const data = await response.json();
                        gasPriceWei = parseInt(data.result, 16);
                        break;
                    }
                } catch (error) {
                    console.warn(`Failed to get gas price from ${url}:`, error);
                    continue;
                }
            }

            if (!gasPriceWei) {
                throw new Error('Failed to get gas price from any BSC RPC');
            }

            const gasPriceGwei = gasPriceWei / 1e9;
            const estimatedGasCost = 21000;
            const gasCostInBnb = (gasPriceGwei * estimatedGasCost) / 1e9;
            const bnbPriceUsdt = await this.getBnbPriceUsdt();
        
            return gasCostInBnb * bnbPriceUsdt;
    } catch (error) {
            console.error('Error getting gas price:', error);
            throw error;
        }
    }

    /**
     * Get the price of the BNB in USDT
     * @returns {Promise<number>}
     */
    async getBnbPriceUsdt() {
        try {
            const params = {
                chain: this.chain,
                include: 'percent_change'
            };
            const result = await this.makeRequest('/erc20/0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c/price', params);
    
            return parseFloat(result.usdPrice || result.usdPriceFormatted || '0');
        } catch (error) {
            console.error('Error getting BNB price:', error);
            return 300; // fallback
        }
    }

    /**
 * Get all tokens of the wallet with full information
 * @param {string} walletAddress
 * @returns {Promise<Object>}
 */
async getWalletInfo(walletAddress) {
    try {
        console.log('Getting wallet info for address:', walletAddress);
        const [tokens, bnbInfo, usdtInfo] = await Promise.all([
            this.getWalletTokenBalances(walletAddress).catch(err => {
                console.warn('Failed to get ERC20 tokens:', err);
                return [];
            }),
            this.getBnbInfo(walletAddress).catch(err => {
                console.warn('Failed to get BNB info:', err);
                return null;
            }),
            this.getUsdtInfo(walletAddress).catch(err => {
                console.warn('Failed to get USDT info:', err);
                return null;
            })
        ]);

        // Only log if there are tokens with balance
        if (tokens.length > 0) {
            const tokensWithBalance = tokens.filter(t => parseFloat(t.balance_formatted || 0) > 0);
            if (tokensWithBalance.length > 0) {
                console.log('Tokens with balance:', tokensWithBalance.map(t => `${t.symbol}: ${t.balance_formatted}`));
            }
        }

        // Find the needed tokens in the array
        const matterInfo = this.findTokenInList(tokens, window.MATTER_TOKEN_ADDRESS);
        const ideaInfo = this.findTokenInList(tokens, window.IDEA_TOKEN_ADDRESS);
        
        // Get the price of BNB from bnbInfo
        const bnbPriceUsdt = bnbInfo ? parseFloat(bnbInfo.usd_price || 0) : 0;
        
        // Calculate total USDT balance (stablecoins + BNB converted to USDT)
        // Handle both balance_formatted and balance fields
        let usdtBalance = 0;
        if (usdtInfo) {
            if (usdtInfo.balance_formatted) {
                usdtBalance = parseFloat(usdtInfo.balance_formatted);
            } else if (usdtInfo.balance) {
                // Convert from wei to tokens using decimals
                const decimals = usdtInfo.decimals || 18;
                usdtBalance = parseFloat(usdtInfo.balance) / Math.pow(10, decimals);
            }
        }
        
        console.log('USDT Info debug:', {
            usdtInfo: usdtInfo,
            balance: usdtInfo?.balance,
            balance_formatted: usdtInfo?.balance_formatted,
            decimals: usdtInfo?.decimals,
            totalUsdValue: usdtInfo?.totalUsdValue,
            calculatedUsdValue: usdtInfo?.calculatedUsdValue,
            usd_value: usdtInfo?.usd_value,
            usdtBalance: usdtBalance
        });
        
        // For stablecoins, if usd_value is 0 or undefined, use balance as USD value (1:1 ratio)
        let usdtUsdValue = 0;
        if (usdtInfo) {
            usdtUsdValue = parseFloat(usdtInfo.totalUsdValue || usdtInfo.calculatedUsdValue || usdtInfo.usd_value || 0);
            console.log('Initial usdtUsdValue:', usdtUsdValue);
            // If USD value is 0 but we have balance, assume 1:1 USD ratio for stablecoins
            if (usdtUsdValue === 0 && usdtBalance > 0) {
                usdtUsdValue = usdtBalance;
                console.log(`Using balance as USD value for stablecoin: ${usdtUsdValue}`);
            }
        }
        console.log('Final usdtUsdValue:', usdtUsdValue);
        const bnbBalance = bnbInfo ? parseFloat(bnbInfo.balance_formatted) : 0;
        const bnbInUsdt = bnbBalance * bnbPriceUsdt;
        const totalUsdtBalance = usdtUsdValue + bnbInUsdt;
        
        // Only log if there's a meaningful balance
        if (totalUsdtBalance > 0) {
            console.log(`Total balance: $${totalUsdtBalance.toFixed(2)} (USDT: $${usdtUsdValue.toFixed(2)}, BNB: $${bnbInUsdt.toFixed(2)})`);
        }

        const result = {
            matter: matterInfo,
            idea: ideaInfo,
            bnb: bnbInfo,
            usdt: usdtInfo,
            bnbPriceUsdt: bnbPriceUsdt,
            matterBalance: matterInfo ? parseFloat(matterInfo.balance_formatted) : 0,
            ideaBalance: ideaInfo ? parseFloat(ideaInfo.balance_formatted) : 0,
            bnbBalance: bnbBalance,
            usdtBalance: usdtBalance,
            totalUsdtBalance: totalUsdtBalance,
            matterPriceUsdt: matterInfo ? parseFloat(matterInfo.usd_price || 0) : 0,
            ideaPriceUsdt: ideaInfo ? parseFloat(ideaInfo.usd_price || 0) : 0,
            bnbPriceUsdt: bnbPriceUsdt
        };

        console.log('Final wallet info result:', result);
        return result;
    } catch (error) {
        console.error('Error getting wallet info:', error);
        throw error;
    }
}

        /**
     * Find a token in the list by address
     * @param {Array} tokens
     * @param {string} tokenAddress
     * @returns {Object|null}
     */
        findTokenInList(tokens, tokenAddress) {
            if (!Array.isArray(tokens) || !tokenAddress) return null;
            
            const normalizedAddress = this.normalizeAddress(tokenAddress);
            return tokens.find(token => 
                token && token.token_address && 
                this.normalizeAddress(token.token_address) === normalizedAddress
            ) || null;
        }

    /**
     * Normalization of the address for comparison
     * @param {string} address
     * @returns {string}
     */
    normalizeAddress(address) {
        if (!address) return '';
        return address.toLowerCase();
    }

    /**
     * Check the validity of the address
     * @param {string} address
     * @returns {boolean}
     */
    isValidAddress(address) {
        if (!address) return false;
        return /^0x[a-fA-F0-9]{40}$/.test(address);
    }
}

// Create a global instance
window.moralisAPI = new MoralisAPI();

// Function to initialize the API key
window.initMoralisAPI = function(apiKey) {
    window.moralisAPI.init(apiKey);
};

// Export the class for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MoralisAPI;
}
