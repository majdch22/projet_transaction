import os
import time
import requests
from groq import Groq
from web3 import Web3
from chains import get_chain

# ─── 1. FUNCTION SIGNATURE DECODER ────────────────────────────────────────────

def decode_function_signature(input_data: str) -> str:
    """Decode the first 4 bytes of calldata using the 4byte.directory API."""
    if not input_data or input_data == "0x" or len(input_data) < 10:
        return "ETH Transfer (no calldata)"
    selector = input_data[:10]  # e.g. '0xa9059cbb'
    try:
        resp = requests.get(
            f"https://www.4byte.directory/api/v1/signatures/?hex_signature={selector}",
            timeout=5
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                # Return the most common (latest id) signature text
                return results[-1]["text_signature"]
    except Exception:
        pass
    return f"Unknown function ({selector})"


# ─── 2. EVENT LOG DECODER ──────────────────────────────────────────────────────

# Common ERC-20 / DeFi event topic signatures
KNOWN_TOPICS = {
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef": "Transfer(address,address,uint256)",
    "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925": "Approval(address,address,uint256)",
    "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822": "Swap(address,uint256,uint256,uint256,uint256,address)",
    "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1": "Sync(uint112,uint112)",
    "0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c": "Deposit(address,uint256)",
    "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65": "Withdrawal(address,uint256)",
    "0x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee": "LiquidityAdded",
    "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9": "PairCreated",
}

def decode_event_logs(logs: list) -> list:
    """Extract and label known events from transaction receipt logs."""
    decoded = []
    for log in logs:
        topics = log.get("topics", [])
        if not topics:
            continue
        topic0 = topics[0].hex() if hasattr(topics[0], "hex") else str(topics[0])
        event_name = KNOWN_TOPICS.get(topic0, f"Unknown Event ({topic0[:10]}...)")
        decoded.append({
            "contract": log.get("address", ""),
            "event": event_name,
            "log_index": log.get("logIndex", 0),
        })
    return decoded


# ─── 3. REVERT REASON DECODER ─────────────────────────────────────────────────

def decode_revert_reason(error_str: str) -> str:
    """Extract a human-readable revert reason from a raw Web3 error string."""
    try:
        if "0x08c379a0" in error_str:
            hex_start = error_str.find("0x08c379a0")
            hex_data = error_str[hex_start:].split("'")[0].strip()
            raw = bytes.fromhex(hex_data[10:])
            length = int.from_bytes(raw[32:64], "big")
            reason = raw[64: 64 + length].decode("utf-8", errors="ignore")
            if reason:
                return reason
    except Exception:
        pass
    if "execution reverted:" in error_str.lower():
        parts = error_str.lower().split("execution reverted:")
        if len(parts) > 1:
            return "execution reverted: " + parts[1].strip().split("'")[0]
    return error_str if len(error_str) < 200 else "execution reverted (no reason string)"


# ─── 4. TRANSACTION FETCHER ───────────────────────────────────────────────────

def get_transaction_details(tx_hash, chain_key="ethereum", rpc_url=None):
    """Fetch raw transaction and receipt data from the blockchain."""
    try:
        chain = get_chain(chain_key)
        url = rpc_url if rpc_url else chain["rpc_url"]

        w3 = Web3(Web3.HTTPProvider(url))
        if not w3.is_connected():
            return None, f"Failed to connect to {chain['name']} node."

        tx = w3.eth.get_transaction(tx_hash)
        receipt = w3.eth.get_transaction_receipt(tx_hash)

        status = receipt.get("status", None)
        is_success = status == 1

        revert_reason = "Unknown/Not provided"
        if not is_success:
            try:
                tx_call = {
                    "to": tx["to"],
                    "from": tx["from"],
                    "value": tx["value"],
                    "data": tx["input"],
                    "gas": tx["gas"],
                }
                if "gasPrice" in tx:
                    tx_call["gasPrice"] = tx["gasPrice"]
                elif "maxFeePerGas" in tx:
                    tx_call["maxFeePerGas"] = tx["maxFeePerGas"]
                    tx_call["maxPriorityFeePerGas"] = tx.get("maxPriorityFeePerGas", 0)
                w3.eth.call(tx_call, receipt["blockNumber"])
            except Exception as e:
                revert_reason = decode_revert_reason(str(e))

        input_data = tx["input"].hex() if hasattr(tx["input"], "hex") else str(tx["input"])
        function_name = decode_function_signature(input_data)
        events = decode_event_logs(receipt.get("logs", []))

        gas_used = receipt.get("gasUsed", 0)
        gas_limit = tx.get("gas", 0)
        gas_usage_pct = round((gas_used / gas_limit) * 100, 2) if gas_limit > 0 else 0
        effective_gas_price = receipt.get("effectiveGasPrice", tx.get("gasPrice", 0))
        tx_fee_eth = w3.from_wei(gas_used * effective_gas_price, "ether")

        return {
            "hash": tx_hash,
            "chain": chain["name"],
            "from": tx["from"],
            "to": tx["to"],
            "value_eth": w3.from_wei(tx["value"], "ether"),
            "token_symbol": chain["native_token"],
            "gas_used": gas_used,
            "gas_limit": gas_limit,
            "gas_usage_pct": gas_usage_pct,
            "tx_fee_eth": tx_fee_eth,
            "block_number": receipt["blockNumber"],
            "status": "Success" if is_success else "Failed",
            "revert_reason": revert_reason if not is_success else None,
            "function_name": function_name,
            "events": events,
            "input_data": input_data,
        }, None

    except Exception as e:
        return None, f"Blockchain Error: {str(e)}"

def find_transaction_across_chains(tx_hash):
    """Iterate through all supported chains to find where the transaction hash exists."""
    from chains import CHAINS
    
    # Prioritized order (optional, here we just go through the dict)
    for chain_key in CHAINS.keys():
        try:
            details, error = get_transaction_details(tx_hash, chain_key)
            if details and not error:
                return details, chain_key, None
        except Exception:
            continue
            
    return None, None, "Transaction not found on any supported blockchain."

def get_token_info(token_address: str, chain_key: str):
    """Get metadata for an ERC-20 token address."""
    try:
        chain = get_chain(chain_key)
        w3 = Web3(Web3.HTTPProvider(chain["rpc_url"]))
        # Minimal ABI for name/symbol/decimals
        abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
        ]
        contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=abi)
        return {
            "name": contract.functions.name().call(),
            "symbol": contract.functions.symbol().call(),
            "decimals": contract.functions.decimals().call()
        }, None
    except Exception as e:
        return None, str(e)


# ─── 5. FEW-SHOT EXAMPLES ─────────────────────────────────────────────────────

FEW_SHOT_EXAMPLES = """
### Example 1 — Out of Gas
Transaction: transfer(address,uint256) | Gas Used: 100% | Revert: Unknown
**Root Cause:** The transaction ran out of gas. The gas limit set by the sender was too low for the operation.
**Impact:** The transaction was reverted and all state changes were undone, but the gas fee was still charged.
**Fix:** Retry with a higher gas limit (try 150,000+). Use a gas estimator before sending.

### Example 2 — Access Control
Transaction: mint(address,uint256) | Gas Used: 15% | Revert: execution reverted: Ownable: caller is not the owner
**Root Cause:** The caller does not have the required `OWNER` role on the contract. Only the contract deployer or admin can call this function.
**Impact:** The minting operation was rejected entirely.
**Fix:** Ensure you are calling from the correct authorized wallet address. Check contract ownership with `owner()`.

### Example 3 — Slippage / DEX Swap
Transaction: swapExactTokensForTokens(...) | Gas Used: 65% | Revert: execution reverted: UniswapV2Router: INSUFFICIENT_OUTPUT_AMOUNT
**Root Cause:** The price moved between when the transaction was submitted and when it was mined. The output amount fell below the minimum specified.
**Impact:** The swap was reverted to protect the user from an unfavorable rate.
**Fix:** Increase slippage tolerance in your DEX interface (e.g. from 0.5% to 1-2%), or use a faster gas price to get mined sooner.
"""


# ─── STEP 1: CLASSIFY FAILURE ─────────────────────────────────────────────────

def classify_failure(tx_details, client) -> str:
    """Use the LLM to classify the failure type in one fast call."""
    classify_prompt = f"""Classify this failed blockchain transaction into ONE of these categories:
- OUT_OF_GAS
- SLIPPAGE_EXCEEDED
- ACCESS_CONTROL
- INSUFFICIENT_BALANCE
- CONTRACT_LOGIC_REVERT
- UNKNOWN

Transaction:
- Function called: {tx_details.get('function_name')}
- Gas Used: {tx_details['gas_usage_pct']}% of limit
- Revert Reason: {tx_details.get('revert_reason')}
- Events emitted before revert: {[e['event'] for e in tx_details.get('events', [])]}

Respond with ONLY the category name, nothing else."""
    try:
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": classify_prompt}],
            model="llama-3.3-70b-versatile",
            max_tokens=20,
        )
        return resp.choices[0].message.content.strip().upper()
    except Exception:
        return "UNKNOWN"


# ─── STEP 2: EXPLAIN + FIX ────────────────────────────────────────────────────

def analyze_with_ai(tx_details, api_key, retries=3, backoff=5):
    if not api_key or len(api_key) < 10:
        return None, "Invalid API Key. Get a free Groq key at https://console.groq.com"

    client = Groq(api_key=api_key)

    # Step 1: classify
    failure_type = "N/A"
    if tx_details["status"] == "Failed":
        failure_type = classify_failure(tx_details, client)

    events_summary = "\n".join(
        [f"  - {e['event']} at {e['contract']}" for e in tx_details.get("events", [])]
    ) or "  None (transaction reverted before any events were emitted)"

    # Step 2: full explanation prompt with few-shot examples
    prompt = f"""You are an expert DeFi transaction analyst. Use the examples below as a guide for the format and depth expected.

{FEW_SHOT_EXAMPLES}
---
Now analyze this NEW transaction and provide your diagnosis in the EXACT same format (Root Cause, Impact, Fix).

### Transaction Data:
- **Hash:** {tx_details['hash']}
- **From:** {tx_details['from']}
- **To:** {tx_details['to']}
- **Function Called:** {tx_details.get('function_name', 'Unknown')}
- **Value Sent:** {tx_details['value_eth']} ETH
- **Transaction Fee:** {tx_details['tx_fee_eth']} ETH
- **Gas Limit:** {tx_details['gas_limit']}
- **Gas Used:** {tx_details['gas_used']} ({tx_details['gas_usage_pct']}% of limit)
- **Status:** {tx_details['status']}
- **Failure Category:** {failure_type}
- **Revert Reason:** {tx_details.get('revert_reason', 'N/A')}
- **Events emitted:**
{events_summary}
- **Input Data (first 600 chars):** {tx_details.get('input_data', '')[:600]}

Respond ONLY with the structured markdown analysis. Do not include any preamble."""

    last_error = None
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            result = resp.choices[0].message.content
            # Prepend the failure classification badge
            badge = f"> **🏷️ Failure Category: `{failure_type}`**\n\n" if tx_details["status"] == "Failed" else ""
            return badge + result, None

        except Exception as e:
            last_error = str(e)
            is_rate = "429" in last_error or "rate_limit" in last_error.lower()
            if is_rate and attempt < retries - 1:
                time.sleep(backoff * (2 ** attempt))
                continue
            break

    if "401" in last_error or "invalid_api_key" in last_error.lower():
        return None, "Groq API Error: Invalid API key. Get one free at https://console.groq.com"
    elif "429" in last_error or "rate_limit" in last_error.lower():
        return None, "Groq API Error: Rate limit exceeded. Wait a moment and retry."
    else:
        return None, f"AI Generation Error: {last_error}"
