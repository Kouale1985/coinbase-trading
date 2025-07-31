import streamlit as st
import pandas as pd
import json
import os
import requests
from datetime import datetime, timezone
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# Page config
st.set_page_config(
    page_title="🚀 Coinbase Trading Bot Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .stDataFrame {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

def load_json_data(filename):
    """Load JSON data with error handling"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading {filename}: {e}")
    return None

def load_json_from_github(repo_owner, repo_name, file_path, branch="main"):
    """Load JSON data from GitHub raw URL"""
    try:
        # GitHub raw URL format
        url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/{file_path}"
        
        # Add cache busting parameter to ensure fresh data
        import time
        cache_bust = int(time.time())
        url += f"?cb={cache_bust}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None  # File doesn't exist yet
        else:
            st.error(f"GitHub API error {response.status_code} for {file_path}")
            return None
            
    except requests.exceptions.Timeout:
        st.error(f"Timeout loading {file_path} from GitHub")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error loading {file_path}: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON in {file_path}: {e}")
        return None
    except Exception as e:
        st.error(f"Error loading {file_path} from GitHub: {e}")
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

def get_signal_color(can_buy, rsi, throttle_status):
    """Get color for signal status"""
    if can_buy and "Ready" in throttle_status:
        return "🟢"
    elif can_buy and "remaining" in throttle_status:
        return "🟡"
    elif rsi and rsi < 35:
        return "🟡"
    else:
        return "🔴"

# Main dashboard
def main():
    st.title("🚀 Coinbase Trading Bot Dashboard")
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")
    
    # GitHub repository settings
    st.sidebar.subheader("📂 GitHub Repository")
    
    # Get GitHub repo info from user
    repo_owner = st.sidebar.text_input("GitHub Username/Organization", 
                                      value="", 
                                      help="Your GitHub username or organization name")
    repo_name = st.sidebar.text_input("Repository Name", 
                                     value="", 
                                     help="The name of your repository (e.g., 'trading-bot')")
    
    # Auto-refresh setting
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=True)
    
    # Manual refresh button
    if st.sidebar.button("🔃 Refresh Now"):
        st.rerun()
    
    st.markdown("---")
    
    # Check if GitHub settings are provided
    if not repo_owner or not repo_name:
        st.warning("⚙️ Please configure your GitHub repository in the sidebar to load live data.")
        st.info("""
        **📋 Setup Instructions:**
        
        1. **Enter your GitHub username** and **repository name** in the sidebar
        2. Make sure your trading bot is **pushing data to GitHub**
        3. The dashboard will automatically load the latest data
        
        **Example:**
        - GitHub Username: `john-doe`
        - Repository Name: `coinbase-trading-bot`
        """)
        return
    
    # Auto-refresh mechanism
    placeholder = st.empty()
    
    with placeholder.container():
        # Load data from GitHub
        with st.spinner("📡 Loading data from GitHub..."):
            portfolio_data = load_json_from_github(repo_owner, repo_name, "data/portfolio.json")
            positions_data = load_json_from_github(repo_owner, repo_name, "data/positions.json")
            signals_data = load_json_from_github(repo_owner, repo_name, "data/signals.json")
            trade_history = load_json_from_github(repo_owner, repo_name, "data/trade_history.json")
        
        if not portfolio_data:
            st.warning("⚠️ No portfolio data found on GitHub.")
            st.info(f"""
            **🔍 Troubleshooting:**
            
            1. **Check repository:** Is `{repo_owner}/{repo_name}` correct?
            2. **Check bot status:** Is your Render bot running and pushing data?
            3. **Check GitHub:** Look for `data/portfolio.json` in your repository
            4. **Wait a moment:** Your bot updates every 2 minutes
            
            **Expected GitHub structure:**
            ```
            {repo_name}/
            ├── data/
            │   ├── portfolio.json
            │   ├── positions.json
            │   ├── signals.json
            │   └── trade_history.json
            ```
            """)
            return
        
        # Success indicator
        st.success(f"✅ Successfully loaded data from `{repo_owner}/{repo_name}`")
        
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
                f"Position value: {format_currency(portfolio_data.get('position_value', 0))}"
            )
        
        st.markdown("---")
        
        # Two main columns
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            # Market Signals Table
            st.subheader("📊 Live Market Signals")
            
            if signals_data:
                df_signals = pd.DataFrame(signals_data)
                
                # Add signal indicators
                df_signals['Signal'] = df_signals.apply(
                    lambda row: get_signal_color(
                        row.get('can_buy', False), 
                        row.get('rsi'), 
                        row.get('throttle_status', '')
                    ), axis=1
                )
                
                # Display table
                display_cols = ['Signal', 'pair', 'price', 'rsi', 'ema_uptrend', 'macd_bullish', 'throttle_status']
                df_display = df_signals[display_cols].copy()
                df_display['price'] = df_display['price'].apply(lambda x: f"${x:.4f}" if x else "N/A")
                df_display['rsi'] = df_display['rsi'].apply(lambda x: f"{x:.1f}" if x else "N/A")
                df_display['ema_uptrend'] = df_display['ema_uptrend'].apply(lambda x: "✅" if x else "❌")
                df_display['macd_bullish'] = df_display['macd_bullish'].apply(lambda x: "✅" if x else "❌")
                
                df_display.columns = ['Signal', 'Pair', 'Price', 'RSI', 'EMA Trend', 'MACD', 'Throttle Status']
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                # RSI Distribution Chart
                st.subheader("📈 RSI Distribution")
                df_rsi = df_signals[df_signals['rsi'].notna()].copy()
                if not df_rsi.empty:
                    fig_rsi = px.bar(
                        df_rsi, 
                        x='pair', 
                        y='rsi',
                        title="Current RSI Levels by Pair",
                        color='rsi',
                        color_continuous_scale=['red', 'yellow', 'green']
                    )
                    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
                    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
                    st.plotly_chart(fig_rsi, use_container_width=True)
            else:
                st.info("📡 Waiting for signal data...")
        
        with col_right:
            # Current Positions
            st.subheader("💼 Current Positions")
            
            if positions_data and len(positions_data) > 0:
                for position in positions_data:
                    pnl = position.get('unrealized_pnl', 0)
                    pnl_pct = (pnl / position.get('entry_value', 1)) * 100
                    pnl_color = "green" if pnl >= 0 else "red"
                    
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;">
                        <h4>{position['pair']}</h4>
                        <p><strong>Entry:</strong> ${position['entry_price']:.4f}</p>
                        <p><strong>Quantity:</strong> {position['quantity']:.6f}</p>
                        <p style="color: {pnl_color}"><strong>P&L:</strong> ${pnl:.2f} ({pnl_pct:+.2f}%)</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📭 No open positions")
            
            # Quick Stats
            st.subheader("📊 Quick Stats")
            
            if signals_data:
                buy_signals = len([s for s in signals_data if s.get('can_buy', False)])
                oversold = len([s for s in signals_data if s.get('rsi', 100) < 30])
                uptrend = len([s for s in signals_data if s.get('ema_uptrend', False)])
                
                st.markdown(f"""
                - 🟢 **Buy Signals:** {buy_signals}/{len(signals_data)}
                - 📉 **Oversold (RSI<30):** {oversold}/{len(signals_data)}
                - 📈 **Uptrend (Price>EMA):** {uptrend}/{len(signals_data)}
                """)
            
            # Last Update
            if portfolio_data.get('timestamp'):
                last_update = datetime.fromisoformat(portfolio_data['timestamp'].replace('Z', '+00:00'))
                time_ago = datetime.now(timezone.utc) - last_update
                st.info(f"🕐 Last update: {time_ago.seconds // 60}m ago")
        
        # Trade History
        if trade_history and len(trade_history) > 0:
            st.markdown("---")
            st.subheader("📜 Recent Trade History")
            
            df_trades = pd.DataFrame(trade_history[-10:])  # Last 10 trades
            if not df_trades.empty:
                df_trades['pnl_color'] = df_trades['pnl'].apply(lambda x: '🟢' if x > 0 else '🔴')
                display_trades = df_trades[['pnl_color', 'pair', 'entry_price', 'exit_price', 'pnl', 'pnl_percent']].copy()
                display_trades.columns = ['Result', 'Pair', 'Entry $', 'Exit $', 'P&L $', 'P&L %']
                st.dataframe(display_trades, use_container_width=True, hide_index=True)
    
    # Auto-refresh every 30 seconds if enabled
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()