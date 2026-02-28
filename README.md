# DeFi Transaction Failure Diagnosis Agent

An AI-powered agent built with Python, Streamlit, Web3.py, and Google Gemini.
This application allows a user to input a Web3 transaction hash, fetches the detailed execution logs from an RPC node, determines if the transaction succeeded or failed, and uses a Large Language Model (Gemini 1.5 Flash) to explain the failure in human-readable terms, along with actionable fixes.

## Features
- Connects to any EVM-compatible blockchain via RPC.
- Detects if the transaction is successful or if it reverted.
- Attempts to capture the required revert reason by simulating the transaction before it was mined.
- Provides a comprehensive, easy-to-understand explanation using Google Gemini AI.

## Requirements
- Python 3.8+
- An Ethereum RPC URL (e.g., Alchemy, Infura, Cloudflare)
- Google Gemini API Key

## Setup & Installation

1. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   streamlit run app.py
   ```

## Usage
1. Open the local link provided by Streamlit (usually `http://localhost:8501`).
2. Enter your RPC Node URL (or use the default Cloudflare one for Ethereum Mainnet).
3. Enter your Google Gemini API Key.
4. Paste the Transaction Hash you want to analyze.
5. Click **Analyze Transaction** and review the AI findings!
