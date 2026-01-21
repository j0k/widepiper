/**
 * Ethers API Client для работы с BSC без индексера
 * Функции: нативный баланс, gas price, стоимость простой транзакции, баланс ERC-20, цена BNB через Chainlink
 */

(function() {
    if (!window.ethers) {
        console.warn('ethers.js not found; ethersAPI will be unavailable');
        return;
    }

    class EthersAPI {
        constructor() {
            this.provider = null;
            this.chain = 'bsc';
            this.rpcUrls = [
                'https://bsc-dataseed.binance.org/',
                'https://bsc-dataseed1.binance.org/',
                'https://bsc-dataseed2.binance.org/',
                'https://bsc-dataseed3.binance.org/',
                'https://bsc-dataseed4.binance.org/'
            ];
            // Chainlink BNB/USD feed (BSC mainnet)
            this.chainlinkBnbUsdAddress = '0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE';
            this.aggregatorV3InterfaceAbi = [
                {
                    inputs: [],
                    name: 'decimals',
                    outputs: [{ internalType: 'uint8', name: '', type: 'uint8' }],
                    stateMutability: 'view',
                    type: 'function'
                },
                {
                    inputs: [],
                    name: 'latestRoundData',
                    outputs: [
                        { internalType: 'uint80', name: 'roundId', type: 'uint80' },
                        { internalType: 'int256', name: 'answer', type: 'int256' },
                        { internalType: 'uint256', name: 'startedAt', type: 'uint256' },
                        { internalType: 'uint256', name: 'updatedAt', type: 'uint256' },
                        { internalType: 'uint80', name: 'answeredInRound', type: 'uint80' }
                    ],
                    stateMutability: 'view',
                    type: 'function'
                }
            ];
            this.erc20Abi = [
                { constant: true, inputs: [{ name: 'owner', type: 'address' }], name: 'balanceOf', outputs: [{ name: 'balance', type: 'uint256' }], type: 'function' },
                { constant: true, inputs: [], name: 'decimals', outputs: [{ name: '', type: 'uint8' }], type: 'function' },
                { constant: true, inputs: [], name: 'symbol', outputs: [{ name: '', type: 'string' }], type: 'function' },
                { constant: true, inputs: [], name: 'name', outputs: [{ name: '', type: 'string' }], type: 'function' }
            ];
        }

        init(rpcUrl) {
            const url = rpcUrl || this.rpcUrls[0];
            this.provider = new window.ethers.providers.JsonRpcProvider(url);
        }

        ensureProvider() {
            if (!this.provider) {
                this.init();
            }
        }

        async getNativeBalance(address) {
            this.ensureProvider();
            const balanceWei = await this.provider.getBalance(address);
            const balance = Number(window.ethers.utils.formatEther(balanceWei));
            return { balanceWei: balanceWei.toString(), balance, balance_formatted: String(balance) };
        }

        async getGasPriceWei() {
            this.ensureProvider();
            const gasPrice = await this.provider.getGasPrice();
            return gasPrice; // BigNumber wei
        }

        async getGasPriceGwei() {
            const wei = await this.getGasPriceWei();
            return Number(window.ethers.utils.formatUnits(wei, 'gwei'));
        }

        async getGasCostSimpleTxInBnb() {
            const gasPriceWei = await this.getGasPriceWei();
            const gasLimit = window.ethers.BigNumber.from(21000);
            const costWei = gasPriceWei.mul(gasLimit);
            return Number(window.ethers.utils.formatEther(costWei));
        }

        async getBnbPriceUsd() {
            this.ensureProvider();
            const feed = new window.ethers.Contract(
                this.chainlinkBnbUsdAddress,
                this.aggregatorV3InterfaceAbi,
                this.provider
            );
            const decimals = await feed.decimals(); // typically 8
            const data = await feed.latestRoundData();
            const answer = Number(data.answer.toString());
            const price = answer / Math.pow(10, decimals);
            return price; // USD per BNB
        }

        async getGasCostSimpleTxInUsd() {
            const [bnbCost, bnbUsd] = await Promise.all([
                this.getGasCostSimpleTxInBnb(),
                this.getBnbPriceUsd()
            ]);
            return bnbCost * bnbUsd;
        }

        isValidAddress(address) {
            return /^0x[a-fA-F0-9]{40}$/.test(address || '');
        }

        normalizeAddress(address) {
            return (address || '').toLowerCase();
        }

        async getTokenInfo(walletAddress, tokenAddress) {
            if (!this.isValidAddress(walletAddress) || !this.isValidAddress(tokenAddress)) return null;
            this.ensureProvider();
            const token = new window.ethers.Contract(tokenAddress, this.erc20Abi, this.provider);
            const [rawBalance, decimals, symbol, name] = await Promise.all([
                token.balanceOf(walletAddress),
                token.decimals(),
                token.symbol().catch(() => ''),
                token.name().catch(() => '')
            ]);
            const balance = Number(window.ethers.utils.formatUnits(rawBalance, decimals));
            return {
                token_address: this.normalizeAddress(tokenAddress),
                symbol: symbol || '',
                name: name || '',
                balance: rawBalance.toString(),
                balance_formatted: String(balance),
                decimals: Number(decimals)
            };
        }

        async getMatterInfo(walletAddress) {
            const addr = window.MATTER_TOKEN_ADDRESS;
            if (!addr) return null;
            return await this.getTokenInfo(walletAddress, addr);
        }

        async getIdeaInfo(walletAddress) {
            const addr = window.IDEA_TOKEN_ADDRESS;
            if (!addr) return null;
            return await this.getTokenInfo(walletAddress, addr);
        }

        async getBnbInfo(walletAddress) {
            const [native, usd] = await Promise.all([
                this.getNativeBalance(walletAddress),
                this.getBnbPriceUsd().catch(() => 0)
            ]);
            return {
                symbol: 'BNB',
                name: 'Binance Coin',
                balance: native.balanceWei,
                balance_formatted: String(native.balance),
                usd_price: String(usd),
                usd_value: String(native.balance * usd),
                token_address: null,
                decimals: 18
            };
        }

        async getUsdtInfo(walletAddress) {
            try {
                // Common stablecoin addresses on BSC
                const stablecoinAddresses = [
                    { address: '0x55d398326f99059fF775485246999027b3197955', symbol: 'USDT' },
                    { address: '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d', symbol: 'USDC' },
                    { address: '0xe9e7cea3dedca5984780bafc599bd69add087d56', symbol: 'BUSD' },
                    { address: '0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3', symbol: 'DAI' }
                ];
                
                let totalUsdValue = 0;
                let primaryToken = null;
                
                for (const { address, symbol } of stablecoinAddresses) {
                    try {
                        const tokenInfo = await this.getTokenInfo(walletAddress, address);
                        if (tokenInfo && tokenInfo.balance_formatted && parseFloat(tokenInfo.balance_formatted) > 0) {
                            const balance = parseFloat(tokenInfo.balance_formatted);
                            console.log(`Found ${symbol}: ${balance} tokens`);
                            
                            // For stablecoins, assume 1:1 USD ratio
                            const usdValue = balance;
                            totalUsdValue += usdValue;
                            
                            // Use USDT as primary if available, otherwise first found
                            if (!primaryToken || symbol === 'USDT') {
                                primaryToken = {
                                    ...tokenInfo,
                                    symbol: symbol,
                                    totalUsdValue: totalUsdValue
                                };
                            }
                        }
                    } catch (e) {
                        // Try next address
                        continue;
                    }
                }
                
                if (primaryToken) {
                    console.log('Primary stablecoin token:', primaryToken);
                    return primaryToken;
                }
                
                console.log('No stablecoins found');
                return null;
            } catch (error) {
                console.warn('Error getting stablecoin info:', error);
                return null;
            }
        }

        async getWalletInfo(walletAddress) {
            const [matter, idea, bnb, usdt] = await Promise.all([
                this.getMatterInfo(walletAddress).catch(() => null),
                this.getIdeaInfo(walletAddress).catch(() => null),
                this.getBnbInfo(walletAddress).catch(() => null),
                this.getUsdtInfo(walletAddress).catch(() => null)
            ]);
            const bnbPriceUsdt = bnb ? Number(bnb.usd_price || 0) : 0;
            
            // Calculate total USDT balance
            // Handle both balance_formatted and balance fields
            let usdtBalance = 0;
            if (usdt) {
                if (usdt.balance_formatted) {
                    usdtBalance = Number(usdt.balance_formatted);
                } else if (usdt.balance) {
                    // Convert from wei to tokens using decimals
                    const decimals = usdt.decimals || 18;
                    usdtBalance = Number(usdt.balance) / Math.pow(10, decimals);
                }
            }
            
            // For stablecoins, if usd_value is 0 or undefined, use balance as USD value (1:1 ratio)
            let usdtUsdValue = 0;
            if (usdt) {
                usdtUsdValue = Number(usdt.totalUsdValue || usdt.balance_formatted || usdt.balance || 0);
                // If USD value is 0 but we have balance, assume 1:1 USD ratio for stablecoins
                if (usdtUsdValue === 0 && usdtBalance > 0) {
                    usdtUsdValue = usdtBalance;
                }
            }
            const bnbBalance = bnb ? Number(bnb.balance_formatted) : 0;
            const bnbInUsdt = bnbBalance * bnbPriceUsdt;
            const totalUsdtBalance = usdtUsdValue + bnbInUsdt;
            
            return {
                matter,
                idea,
                bnb,
                usdt,
                bnbPriceUsdt,
                matterBalance: matter ? Number(matter.balance_formatted) : 0,
                ideaBalance: idea ? Number(idea.balance_formatted) : 0,
                bnbBalance: bnbBalance,
                usdtBalance: usdtBalance,
                totalUsdtBalance: totalUsdtBalance,
                matterPriceUsdt: matter ? Number(matter.usd_price || 0) : 0,
                ideaPriceUsdt: idea ? Number(idea.usd_price || 0) : 0
            };
        }
    }

    // Глобальный экземпляр и init
    window.ethersAPI = new EthersAPI();
    window.initEthersAPI = function(rpcUrl) { window.ethersAPI.init(rpcUrl); };
})();


