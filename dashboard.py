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

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #c3e6cb;
        margin-bottom: 1rem;
    }
    .stDataFrame {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

def load_json_from_github(repo_owner, repo_name, file_path, branch="main"):
    """Load JSON data from GitHub raw URL with cache busting"""
    try:
        # GitHub raw URL format with cache busting
        cache_bust = int(time.time())
        url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/{file_path}?cb={cache_bust}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None  # File doesn't exist yet
        else:
            return None
            
    except Exception as e:
        st.error(f"Error loading {file_path}: {str(e)}")
        return None

def format_currency(value):
    """Format currency values"""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"

def format_percentage(value):
    """Format percentage values"""
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        if timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        pass
    return "Unknown"

def get_signal_color(action, rsi=None):
    """Get emoji color for signal"""
    if action == "BUY":
        return "🟢"
    elif rsi and rsi < 30:
        return "🟡"  # Oversold but not buying
    else:
        return "🔴"  # Hold

def main():
    st.title("🚀 Coinbase Trading Bot Dashboard")
    st.markdown("**Real-time monitoring via GitHub auto-sync**")
    
    # Sidebar configuration
    st.sidebar.header("⚙️ GitHub Configuration")
    
    # GitHub repository settings
    repo_owner = st.sidebar.text_input(
        "GitHub Username/Organization", 
        value="",
        placeholder="your-username",
        help="Your GitHub username (case-sensitive)"
    )
    repo_name = st.sidebar.text_input(
        "Repository Name", 
        value="",
        placeholder="coinbase-trading-bot", 
        help="Your repository name (case-sensitive)"
    )
    
    # Auto-refresh controls
    st.sidebar.header("🔄 Refresh Settings")
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    refresh_interval = st.sidebar.selectbox("Refresh interval (seconds)", [30, 60, 120], index=0)
    
    # Manual refresh button
    if st.sidebar.button("🔃 Refresh Now", use_container_width=True):
        st.rerun()
    
    # Show connection status
    if repo_owner and repo_name:
        st.sidebar.success(f"📂 Target: `{repo_owner}/{repo_name}`")
        github_url = f"https://github.com/{repo_owner}/{repo_name}/tree/main/data"
        st.sidebar.markdown(f"[📁 View Data Files]({github_url})")
    
    st.markdown("---")
    
    # Check if GitHub settings are provided
    if not repo_owner or not repo_name:
        st.warning("⚙️ Please configure your GitHub repository in the sidebar.")
        st.info("""
        **📋 Setup Steps:**
        
        1. **Enter your GitHub details** in the sidebar (exact username and repo name)
        2. **Make sure your bot is running** on Render and pushing data
        3. **Check your repository** has a `data/` folder with JSON files
        
        **Example:**
        - Username: `john-doe` 
        - Repository: `coinbase-trading-bot`
        """)
        return
    
    # Load data from GitHub
    with st.spinner("📡 Loading latest data from GitHub..."):
        portfolio_data = load_json_from_github(repo_owner, repo_name, "data/portfolio.json")
        positions_data = load_json_from_github(repo_owner, repo_name, "data/positions.json")
        signals_data = load_json_from_github(repo_owner, repo_name, "data/signals.json")
        trade_history = load_json_from_github(repo_owner, repo_name, "data/trade_history.json")
    
    # Check if data was loaded successfully
    if not portfolio_data:
        st.error("❌ No portfolio data found!")
        st.info(f"""
        **🔍 Troubleshooting:**
        
        1. **Check repository exists:** https://github.com/{repo_owner}/{repo_name}
        2. **Check data folder:** https://github.com/{repo_owner}/{repo_name}/tree/main/data
        3. **Verify bot is running** on Render and pushing data every 2 minutes
        4. **Check recent commits** for "🤖 Bot data update" messages
        
        **Expected files:**
        - `data/portfolio.json`
        - `data/signals.json` 
        - `data/positions.json`
        - `data/trade_history.json`
        """)
        
        # Try to show recent commits for debugging
        try:
            commits_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits?per_page=5"
            commits_response = requests.get(commits_url, timeout=5)
            if commits_response.status_code == 200:
                commits = commits_response.json()
                st.subheader("🔍 Recent Repository Activity")
                for commit in commits[:3]:
                    msg = commit['commit']['message']
                    date = commit['commit']['author']['date']
                    if "🤖 Bot data update" in msg:
                        st.success(f"✅ {msg} - {date}")
                    else:
                        st.info(f"📝 {msg} - {date}")
            elif commits_response.status_code == 404:
                st.error("❌ Repository not found or private")
        except:
            st.warning("Could not fetch repository information")
        
        return
    
    # Success indicator
    last_update = portfolio_data.get('updated_at', 'Unknown')
    st.markdown(f"""
    <div class="success-box">
        ✅ <strong>Successfully connected to GitHub!</strong><br>
        📂 Repository: <code>{repo_owner}/{repo_name}</code><br>
        🕒 Last bot update: <strong>{format_timestamp(last_update)}</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # Main dashboard content
    # Header metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_return = portfolio_data.get('total_return_pct', 0)
        st.metric(
            "💰 Total Balance", 
            format_currency(portfolio_data.get('total_balance')),
            format_percentage(total_return)
        )
    
    with col2:
        st.metric(
            "📈 Realized P&L", 
            format_currency(portfolio_data.get('realized_pnl')),
            f"{portfolio_data.get('winning_trades', 0)}/{portfolio_data.get('total_trades', 0)} wins"
        )
    
    with col3:
        st.metric(
            "💵 Available Cash", 
            format_currency(portfolio_data.get('current_cash')),
            f"{(portfolio_data.get('current_cash', 0) / portfolio_data.get('total_balance', 1) * 100):.1f}% cash"
        )
    
    with col4:
        st.metric(
            "📊 Open Positions", 
            f"{portfolio_data.get('open_positions', 0)}/{portfolio_data.get('max_positions', 4)}",
            f"Exposure: {portfolio_data.get('portfolio_exposure', 0):.1f}%"
        )
    
    st.markdown("---")
    
    # Two main columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Market signals table
        st.subheader("📊 Live Market Signals")
        
        if signals_data:
            df_signals = pd.DataFrame(signals_data)
            
            # Create a clean display table
            display_data = []
            for _, row in df_signals.iterrows():
                # Convert can_buy to action for display
                action = "BUY" if row.get('can_buy', False) else "HOLD"
                display_data.append({
                    "🚦": get_signal_color(action, row['rsi']),
                    "Trading Pair": row['pair'],
                    "Price": f"${row['price']:,.4f}",
                    "RSI": f"{row['rsi']:.1f}",
                    "Signal": action,
                    "EMA Trend": "📈" if row.get('ema_uptrend', False) else "📉",
                    "MACD": "🚀" if row.get('macd_bullish', False) else "🔻"
                })
            
            display_df = pd.DataFrame(display_data)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # RSI Distribution Chart
            st.subheader("📈 RSI Distribution Across All Pairs")
            
            fig = px.bar(
                df_signals, 
                x='pair', 
                y='rsi',
                color='rsi',
                color_continuous_scale='RdYlGn_r',
                title="Current RSI Levels"
            )
            
            # Add reference lines
            fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
            fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
            
            fig.update_layout(height=400, showlegend=False)
            fig.update_xaxes(title="Trading Pairs", tickangle=45)
            fig.update_yaxes(title="RSI Value", range=[0, 100])
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No signals data available")
    
    with col2:
        # Current positions
        st.subheader("💼 Current Positions")
        
        if positions_data and positions_data:
            for pair, position in positions_data.items():
                pnl_color = "🟢" if position.get('unrealized_pnl', 0) >= 0 else "🔴"
                
                with st.container():
                    st.write(f"**{pair}**")
                    st.write(f"Entry: {format_currency(position.get('entry_price'))}")
                    st.write(f"Current: {format_currency(position.get('current_price'))}")
                    st.write(f"P&L: {pnl_color} {format_currency(position.get('unrealized_pnl'))} ({position.get('unrealized_pnl_pct', 0):+.2f}%)")
                    st.write(f"Stop Loss: {format_currency(position.get('stop_loss'))}")
                    st.markdown("---")
        else:
            st.info("No open positions")
        
        # Quick stats
        st.subheader("📊 Market Summary")
        
        if signals_data:
            df_signals = pd.DataFrame(signals_data)
            
            oversold_count = len(df_signals[df_signals['rsi'] < 30])
            overbought_count = len(df_signals[df_signals['rsi'] > 70])
            uptrend_count = len(df_signals[df_signals['ema_uptrend'] == True])
            bullish_macd = len(df_signals[df_signals['macd_bullish'] == True])
            
            st.metric("🔴 Oversold Pairs", oversold_count, help="RSI < 30")
            st.metric("🟢 Overbought Pairs", overbought_count, help="RSI > 70") 
            st.metric("📈 Uptrend Pairs", uptrend_count, help="Price > 50 EMA")
            st.metric("🚀 Bullish MACD", bullish_macd, help="MACD > Signal Line")
    
    # Trade history
    if trade_history and trade_history:
        st.subheader("📝 Recent Trade History")
        
        df_trades = pd.DataFrame(trade_history)
        if not df_trades.empty:
            # Format for display
            display_trades = df_trades.copy()
            display_trades['timestamp'] = display_trades['timestamp'].apply(format_timestamp)
            display_trades['total'] = display_trades['total'].apply(format_currency)
            display_trades['price'] = display_trades['price'].apply(format_currency)
            
            st.dataframe(display_trades, use_container_width=True, hide_index=True)
        else:
            st.info("No trades yet")
    
    # Footer with last update time
    st.markdown("---")
    st.caption(f"📅 Dashboard last refreshed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Auto-refresh functionality
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()