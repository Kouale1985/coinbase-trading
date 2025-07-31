import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime, timezone
import plotly.express as px
import plotly.graph_objects as go
import time

# Page config
st.set_page_config(
    page_title="🚀 Coinbase Trading Bot Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_json_from_private_github(repo_owner, repo_name, file_path, github_token, branch="main"):
    """Load JSON data from private GitHub repo using token"""
    try:
        # GitHub API URL for private repos
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3.raw"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            st.error(f"GitHub API error {response.status_code}")
            return None
            
    except Exception as e:
        st.error(f"Error loading {file_path}: {str(e)}")
        return None

def format_currency(value):
    if value is None:
        return "N/A"
    return f"${value:,.2f}"

def format_percentage(value):
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"

def get_signal_color(action, rsi=None):
    if action == "BUY":
        return "🟢"
    elif rsi and rsi < 30:
        return "🟡"
    else:
        return "🔴"

def main():
    st.title("🚀 Coinbase Trading Bot Dashboard")
    st.markdown("**Secure private repository monitoring**")
    
    # Sidebar configuration
    st.sidebar.header("🔐 Private GitHub Access")
    
    repo_owner = st.sidebar.text_input("GitHub Username", value="", placeholder="Kouale1985")
    repo_name = st.sidebar.text_input("Repository Name", value="", placeholder="your-private-repo")
    
    # GitHub token input (hidden)
    github_token = st.sidebar.text_input(
        "GitHub Personal Access Token", 
        type="password",
        help="Create a token at: https://github.com/settings/tokens"
    )
    
    if st.sidebar.button("🔃 Refresh Now"):
        st.rerun()
    
    if not repo_owner or not repo_name or not github_token:
        st.warning("⚙️ Please provide all GitHub credentials in the sidebar.")
        st.info("""
        **🔐 For Private Repository Access:**
        
        1. **Enter your GitHub username and private repo name**
        2. **Create a Personal Access Token:**
           - Go to: https://github.com/settings/tokens
           - Generate new token (classic)
           - Select: `repo` scope for private access
           - Copy the token
        3. **Paste the token** in the sidebar (it will be hidden)
        """)
        return
    
    # Load data from private GitHub
    with st.spinner("🔐 Loading data from private repository..."):
        portfolio_data = load_json_from_private_github(repo_owner, repo_name, "data/portfolio.json", github_token)
        signals_data = load_json_from_private_github(repo_owner, repo_name, "data/signals.json", github_token)
        positions_data = load_json_from_private_github(repo_owner, repo_name, "data/positions.json", github_token)
        trade_history = load_json_from_private_github(repo_owner, repo_name, "data/trade_history.json", github_token)
    
    if not portfolio_data:
        st.error("❌ No portfolio data found in private repository!")
        st.info(f"""
        **🔍 Troubleshooting Private Access:**
        
        1. **Repository exists:** https://github.com/{repo_owner}/{repo_name}
        2. **Token has `repo` scope** for private repository access
        3. **Bot is running** and creating data files
        4. **Data folder exists:** Check for `data/` in your private repo
        """)
        return
    
    # Success indicator
    st.success(f"🔐 Successfully connected to private repository: `{repo_owner}/{repo_name}`")
    
    # Rest of dashboard code (same as public version)
    # Header metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_return = portfolio_data.get('total_return_pct', 0)
        st.metric("💰 Total Balance", format_currency(portfolio_data.get('total_balance')), format_percentage(total_return))
    
    with col2:
        st.metric("📈 Realized P&L", format_currency(portfolio_data.get('realized_pnl')), 
                 f"{portfolio_data.get('winning_trades', 0)}/{portfolio_data.get('total_trades', 0)} wins")
    
    with col3:
        st.metric("💵 Available Cash", format_currency(portfolio_data.get('current_cash')),
                 f"{(portfolio_data.get('current_cash', 0) / portfolio_data.get('total_balance', 1) * 100):.1f}% cash")
    
    with col4:
        st.metric("📊 Open Positions", f"{portfolio_data.get('open_positions', 0)}/{portfolio_data.get('max_positions', 4)}",
                 f"Exposure: {portfolio_data.get('portfolio_exposure', 0):.1f}%")
    
    # Market signals
    if signals_data:
        st.subheader("📊 Live Market Signals")
        df_signals = pd.DataFrame(signals_data)
        
        display_data = []
        for _, row in df_signals.iterrows():
            display_data.append({
                "🚦": get_signal_color(row['action'], row['rsi']),
                "Trading Pair": row['pair'],
                "Price": f"${row['price']:,.4f}",
                "RSI": f"{row['rsi']:.1f}",
                "Signal": row['action']
            })
        
        display_df = pd.DataFrame(display_data)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Auto-refresh
    time.sleep(30)
    st.rerun()

if __name__ == "__main__":
    main()