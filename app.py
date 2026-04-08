import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

try:
    from FinMind.data import DataLoader
except ImportError:
    st.error("Modules installing... Please click 'Manage app' -> 'Reboot App'.")

# --- 專業介面與時區設定 ---
st.set_page_config(page_title="my tool", layout="wide", page_icon="📈")
TW_OFFSET = timedelta(hours=8)
now_tw = datetime.utcnow() + TW_OFFSET

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; font-size: 18px; }
    .ai-insight { background: #fdfdfd; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; border-top: 6px solid #28a745; margin-bottom: 25px; }
    .news-card { background: white; padding: 15px; border-radius: 8px; border-left: 5px solid #1f77b4; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# 網站主標題更名為 my tool
st.title("📈 my tool")

# --- 側邊欄 ---
st.sidebar.header("Analysis Target")
ticker_input = st.sidebar.text_input("Ticker Symbol (e.g. 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"Taipei Time: {now_tw.strftime('%Y-%m-%d %H:%M')}")

# --- 數據抓取模組 ---
@st.cache_data(ttl=300)
def get_full_analysis_data(ticker):
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    
    # 1. Price & Volume
    df_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date=(now_tw - timedelta(days=365)).strftime('%Y-%m-%d'))
    if not df_price.empty:
        df_price = df_price.rename(columns={'date':'Date','open':'Open','max':'High','min':'Low','close':'Close','vol':'Volume'})
        df_price['Date'] = pd.to_datetime(df_price['Date'])
        df_price.set_index('Date', inplace=True)

    # 2. News & Info (yfinance)
    y_stock = yf.Ticker(ticker)
    try:
        y_info = y_stock.info
        y_news = y_stock.news
    except:
        y_info = {}
        y_news = []
    
    # 3. Monthly Revenue
    df_rev = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    
    return df_price, y_news, df_rev, y_info

# --- 計算 RSI ---
def calculate_rsi(data, window=14):
    diff = data.diff(1)
    gain = diff.where(diff > 0, 0)
    loss = -diff.where(diff < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- AI 投資觀察總結 ---
def generate_advanced_ai_insight(df_p, df_r, info, ticker):
    try:
        curr_p = df_p['Close'].iloc[-1]
        rsi = calculate_rsi(df_p['Close']).iloc[-1]
        ma20 = df_p['Close'].rolling(20).mean().iloc[-1]
        pb_ratio = info.get('priceToBook', 'N/A')
        rev_mom = ((df_r['revenue'].iloc[-1] - df_r['revenue'].iloc[-2]) / df_r['revenue'].iloc[-2]) * 100
        
        insight = f"""
        <div class="ai-insight">
            <h3 style="margin-top:0;">🤖 AI Investment Insight ({ticker})</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div><b>Technical:</b> {'Overbought' if rsi > 70 else 'Oversold' if rsi < 30 else 'Neutral'} (RSI: {rsi:.1f})<br>
                     <b>Trend:</b> {'Bullish' if curr_p > ma20 else 'Bearish'} (Above MA20: {'Yes' if curr_p > ma20 else 'No'})</div>
                <div><b>Valuation:</b> P/B Ratio: {pb_ratio if isinstance(pb_ratio, float) else 'N/A'}<br>
                     <b>Revenue:</b> MoM Growth: {rev_mom:.1f}%</div>
            </div>
            <p style="margin-top:15px; border-top: 1px solid #eee; padding-top:10px;">
                <b>Summary:</b> Currently the asset shows {'strong' if rev_mom > 0 and curr_p > ma20 else 'weak'} momentum. 
                Keep track of support levels if RSI remains below 50.
            </p>
        </div>
        """
        return insight
    except:
        return "<div class='ai-insight'>⚠️ Generating AI report... Please wait.</div>"

# --- Main Logic ---
try:
    df_p, news_list, df_r, info = get_full_analysis_data(ticker_input)

    tab1, tab2, tab3 = st.tabs(["📉 Technicals", "📊 Fundamentals", "📰 News Feed"])

    with tab1:
        if not df_p.empty:
            c1, c2, c3 = st.columns(3)
            curr_p = df_p['Close'].iloc[-1]
            c1.metric("Last Price", f"{curr_p:.2f}")
            c2.metric("P/B Ratio", f"{info.get('priceToBook', 'N/A')}")
            c3.metric("RSI (14)", f"{calculate_rsi(df_p['Close']).iloc[-1]:.1f}")

            # Advance Charting
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.05, row_heights=[0.5, 0.2, 0.3])
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], 
                                         low=df_p['Low'], close=df_p['Close'], name='Candlestick'), row=1, col=1)
            rsi_series = calculate_rsi(df_p['Close'])
            fig.add_trace(go.Scatter(x=df_p.index, y=rsi_series, line=dict(color='#FF5722'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color='#1f77b4'), row=3, col=1)
            fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if not df_r.empty:
            df_r['date_fixed'] = pd.to_datetime(df_r['revenue_year'].astype(str) + '-' + df_r['revenue_month'].astype(str) + '-01')
            st.markdown(generate_advanced_ai_insight(df_p, df_r, info, ticker_input), unsafe_allow_html=True)
            fig_rev = go.Figure()
            fig_rev.add_trace(go.Bar(x=df_r['date_fixed'], y=df_r['revenue'], name='Revenue'))
            fig_rev.update_layout(title="Monthly Revenue Trend", template="plotly_white")
            st.plotly_chart(fig_rev, use_container_width=True)

    with tab3:
        if news_list:
            for n in news_list[:12]:
                raw_time = n.get('providerPublishTime', 0)
                pub_date = datetime.fromtimestamp(raw_time).strftime('%Y-%m-%d %H:%M') if raw_time else "Today"
                st.markdown(f'<div class="news-card"><b><a href="{n.get("link","#")}" target="_blank">{n.get("title")}</a></b><br><small>{n.get("publisher")} | {pub_date}</small></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Analysis Error: {e}")
