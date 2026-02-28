import streamlit as st
from analyzer import get_transaction_details, analyze_with_ai, find_transaction_across_chains
from chains import get_chain_names, get_chain

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DeFi Diagnostics AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a premium feel with Light Theme for the center
st.markdown("""
    <style>
    /* Main Content Area - White Theme */
    .stApp {
        background-color: #FFFFFF !important;
        color: #1E1E1E !important;
    }
    
    /* Ensure text visibility in light mode */
    .stMarkdown, p, span, label {
        color: #1E1E1E !important;
    }

    /* Sidebar - Keep Dark/Premium */
    section[data-testid="stSidebar"] {
        background-color: #0e1117 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] label {
        color: #FAFAFA !important;
    }

    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        color: #1E1E1E !important;
    }
    
    .stAlert {
        border-radius: 10px;
    }
    
    div[data-testid="stExpander"] {
        border: 1px solid #dee2e6 !important;
        background-color: #f8f9fa !important;
        border-radius: 10px !important;
    }
    
    /* Input field styling */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #1E1E1E !important;
        border: 1px solid #dee2e6 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=80)
    st.title("DeFi Guardian AI")
    st.markdown("---")
    
    st.header("⚙️ Settings")
    
    # Optional Override
    st.markdown("**Manual Override** (Optional)")
    use_manual = st.checkbox("Manual Chain Selection")
    
    selected_chain_key = "ethereum"
    if use_manual:
        chain_options = get_chain_names()
        chain_display_names = [name for key, name in chain_options]
        selected_display_name = st.selectbox("Select Blockchain", options=chain_display_names, index=0)
        selected_chain_key = [key for key, name in chain_options if name == selected_display_name][0]
    
    api_key = st.text_input(
        "Groq API Key",
        type="password",
        help="Get a free key at https://console.groq.com"
    )
    
    st.markdown("---")
    st.info("💡 **Auto-Detect:** The agent will scan Ethereum, Polygon, BSC, and more to find your transaction automatically.")

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.title("🛡️ DeFi Transaction Failure Diagnosis Agent")
st.markdown("Enter a transaction hash to begin cross-chain analysis.")

# ─── MAIN INPUT ───────────────────────────────────────────────────────────────
with st.container():
    col_input, col_button = st.columns([4, 1])
    with col_input:
        tx_hash = st.text_input("Transaction Hash", placeholder="0x...", label_visibility="collapsed")
    with col_button:
        analyze_clicked = st.button("🚀 Run Diagnosis", use_container_width=True, type="primary")

st.markdown("---")

if analyze_clicked:
    if not tx_hash or not api_key:
        st.warning("⚠️ Please provide both a Transaction Hash and a Groq API Key.")
    else:
        # ── Step 1: Fetch blockchain data
        tx_details = None
        with st.status("📡 Searching across blockchains...", expanded=True) as status:
            if use_manual:
                st.write(f"Fetching from {selected_display_name}...")
                tx_details, error = get_transaction_details(tx_hash, selected_chain_key)
            else:
                st.write("Automatically detecting network...")
                tx_details, chain_key, error = find_transaction_across_chains(tx_hash)
            
            if error:
                status.update(label="❌ Search Failed", state="error", expanded=False)
                st.error(error)
            else:
                status.update(label=f"✅ Found on {tx_details['chain']}", state="complete", expanded=False)

        if tx_details:
            # ── Section 1: Dashboard Metrics
            st.subheader(f"📊 Transaction Summary ({tx_details['chain']})")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            
            status_color = "normal" if tx_details["status"] == "Success" else "inverse"
            m_col1.metric("Status", tx_details["status"], delta_color=status_color)
            m_col2.metric("Gas Usage", f"{tx_details['gas_usage_pct']}%")
            m_col3.metric("Fee Paid", f"{float(tx_details['tx_fee_eth']):.6f} {tx_details['token_symbol']}")
            m_col4.metric("Value Sent", f"{tx_details['value_eth']} {tx_details['token_symbol']}")
            
            with st.expander("🔍 View Technical Details"):
                st.json(tx_details)

            # ── Section 2: Failure Analysis (if applicable)
            if tx_details["status"] == "Failed":
                st.markdown("---")
                st.subheader("⛔ Revert Information")
                st.error(f"**Revert Reason:** {tx_details.get('revert_reason', 'Not detailed by contract')}")
                
                if not tx_details.get("events"):
                    st.warning("⚠️ **Execution Stop:** The transaction reverted before any events were logged.")
                else:
                    st.info(f"💡 {len(tx_details['events'])} events were emitted before the crash.")

            # ── Section 3: AI Diagnosis
            st.markdown("---")
            st.subheader("🤖 AI Smart Diagnosis")
            with st.spinner("🧠 Reasoning through the failure..."):
                analysis_text, ai_error = analyze_with_ai(tx_details, api_key)

            if ai_error:
                st.error(f"AI Analysis failed: {ai_error}")
            else:
                st.container(border=True).markdown(analysis_text)
                st.success("Analysis Complete")
