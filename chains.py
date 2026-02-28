# chains.py — All supported blockchain configurations

CHAINS = {
    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "native_token": "ETH",
        "rpc_url": "https://eth.llamarpc.com",
        "explorer": "https://etherscan.io",
        "explorer_api": "https://api.etherscan.io/api",
    },
    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "native_token": "MATIC",
        "rpc_url": "https://polygon-rpc.com",
        "explorer": "https://polygonscan.com",
        "explorer_api": "https://api.polygonscan.com/api",
    },
    "bsc": {
        "name": "BNB Smart Chain",
        "chain_id": 56,
        "native_token": "BNB",
        "rpc_url": "https://bsc-dataseed.binance.org",
        "explorer": "https://bscscan.com",
        "explorer_api": "https://api.bscscan.com/api",
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "native_token": "ETH",
        "rpc_url": "https://arb1.arbitrum.io/rpc",
        "explorer": "https://arbiscan.io",
        "explorer_api": "https://api.arbiscan.io/api",
    },
    "optimism": {
        "name": "Optimism",
        "chain_id": 10,
        "native_token": "ETH",
        "rpc_url": "https://mainnet.optimism.io",
        "explorer": "https://optimistic.etherscan.io",
        "explorer_api": "https://api-optimistic.etherscan.io/api",
    },
    "base": {
        "name": "Base",
        "chain_id": 8453,
        "native_token": "ETH",
        "rpc_url": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "explorer_api": "https://api.basescan.org/api",
    },
    "avalanche": {
        "name": "Avalanche C-Chain",
        "chain_id": 43114,
        "native_token": "AVAX",
        "rpc_url": "https://api.avax.network/ext/bc/C/rpc",
        "explorer": "https://snowtrace.io",
        "explorer_api": "https://api.snowtrace.io/api",
    },
}

def get_chain(chain_key: str) -> dict:
    return CHAINS.get(chain_key, CHAINS["ethereum"])

def get_chain_names() -> list:
    return [(k, v["name"]) for k, v in CHAINS.items()]
