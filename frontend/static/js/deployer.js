class CounterDeployer {
    constructor() {
        this.isConnected = false;
        this.address = null;
        this.init();
    }

    async init() {
        this.renderApp();
        this.attachEventListeners();
    }

    renderApp() {
        const container = document.getElementById('counter-deployer-app');
        container.innerHTML = `
            <div class='min-h-screen py-12 px-4 sm:px-6 lg:px-8'>
                <div class='max-w-md mx-auto bg-green-500 rounded-lg shadow-md p-8'>
                    <h2 class='text-center text-3xl font-bold text-black mb-8'>
                        DEPLOY COUNTER
                    </h2>

                    <div id='wallet-section'>
                        <button id='connect-wallet' class='w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-black hover:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500'>
                            CONNECT WALLET
                        </button>
                    </div>

                    <div id='deploy-section' class='hidden'>
                        <button id='deploy-button' class='w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-900 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'>
                            DEPLOY
                        </button>
                    </div>

                    <div id='status-message' class='mt-4'></div>
                    <div id='wallet-status' class='mt-4 text-sm text-center font-bold text-black'></div>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        document.getElementById('connect-wallet').addEventListener('click', () => this.connectWallet());
        document.getElementById('deploy-button').addEventListener('click', () => this.deployCounter());
    }

    async connectWallet() {
        try {
            if (!window.ethereum) {
                throw new Error('Please install MetaMask');
            }

            const provider = new ethers.BrowserProvider(window.ethereum);
            const accounts = await provider.send('eth_requestAccounts', []);

            try {
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: '0x2B74' }], // 11124 in hex
                });
            } catch (err) {
                // Adds chain if non-existent
                await window.ethereum.request({
                    method: 'wallet_addEthereumChain',
                    params: [{
                        chainId: '0x2B74',
                        chainName: 'Abstract Testnet',
                        rpcUrls: ['https://api.testnet.abs.xyz'],
                        nativeCurrency: {
                            name: 'Ethereum',
                            symbol: 'ETH',
                            decimals: 18,
                        },
                        blockExplorerUrls: ['https://explorer.testnet.abs.xyz']
                    }],
                });
            };

            const network = await provider.getNetwork();
            if (network.chainId !== 11124n) {
                throw new Error('Please switch to Abstract Testnet');
            }

            this.address = accounts[0];
            this.isConnected = true;
            
            document.getElementById('wallet-section').classList.add('hidden');
            document.getElementById('deploy-section').classList.remove('hidden');
            document.getElementById('wallet-status').textContent = 
                `Connected: ${this.address.slice(0, 6)}...${this.address.slice(-4)}`;

        } catch (err) {
            if (typeof err.message === 'string' && err.message.includes("user rejected")) {
                this.showError('User rejected the request.');
            } else {
                this.showError(err.message || 'Connection failed');
            }  
        }
    }

    async deployCounter() {
        this.showStatus('preparing deployment...');

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();

            // Get contract data from backend
            const response = await fetch('/api/prepare-deployment/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });

            const data = await response.json();

            if (response.status === 429) {
                throw new Error('Rate limit exceeded. Wait a few seconds.' );
            }

            if (!data.success) {
                throw new Error(data.error || 'Failed to prepare deployment');
            }

            if (!data.contract_data.contract_data_value) {
                throw new Error('Invalid contract data received from server');
            }

            // Create transaction
            const tx = {
                from: await signer.getAddress(),
                to: "0x0000000000000000000000000000000000008006",
                data: data.contract_data.contract_data_value,
                nonce: await provider.getTransactionCount(await signer.getAddress(), "latest"),
                chainId: 11124,
            };

            const response2 = await signer.sendTransaction(tx);
            this.showStatus('waiting for confirmation...');
            
            const receipt = await response2.wait();
            this.showStatus('verifying contract...');

            // verify contract
            const response3 = await fetch('/api/verify-contract/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contract_address: receipt.contractAddress,
                }),
            });

            const data2 = await response3.json();

            if (!data2.success) {
                throw new Error(data.error || 'Failed to verify contract');
            }

            this.showSuccess(`CONTRACT ADDRESS: ${receipt.contractAddress}`);

        } catch (err) {
            if (typeof err.message === 'string' && err.message.includes("user rejected")) {
                this.showError('User rejected the request.');
            } else {
                this.showError(err.message || 'Deployment failed');
            }  
        }
    }

    showError(message) {
        const statusEl = document.getElementById('status-message');
        statusEl.innerHTML = `<div class="p-2 text-center text-red-600 text-sm bg-red-50 font-bold rounded">${message}</div>`;
    }

    showSuccess(message) {
        const statusEl = document.getElementById('status-message');
        statusEl.innerHTML = `<div class="p-2 text-center text-green-500 text-sm bg-green-50 font-bold rounded">${message}</div>`;
    }

    showStatus(message) {
        const statusEl = document.getElementById('status-message');
        statusEl.innerHTML = `<div class="p-2 text-center text-blue-600 text-sm bg-blue-50 font-bold rounded">${message}</div>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CounterDeployer();
});