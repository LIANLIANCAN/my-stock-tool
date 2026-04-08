import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# --- 專業介面設定 ---
st.set_page_config(page_title="Pro Equity Research Terminal", layout="wide")

st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { border: 1px solid #d1d4d9; padding: 10px; border-radius: 5px; background: white; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 專業投資決策支援系統 (Beta)")

# --- 側邊欄：研究參數 ---
ticker_symbol = st.sidebar.text_input("輸入證券代碼 (如 2330.TW 或 NVDA)", value="2330.TW").upper()
period = st.sidebar.selectbox("分析週期", ["3mo", "6mo", "1y", "2y", "5y"], index=2)

@st.cache_data(ttl=3600)
def fetch_analysis_data(ticker):
    stock = yf.Ticker(ticker)
    # 抓取歷史股價
    hist = stock.history(period=period)
    # 抓取基本面快照 (接近財報狗核心數據)
    info = stock.info
    return stock, hist, info

try:
    stock_obj, df, info = fetch_analysis_data(ticker_symbol)
    
    # --- 第一區塊：基本面估值 (Fundamental Valuation) ---
    st.subheader("📌 基本面估值與獲利能力")
    m1, m2, m3, m4 = st.columns(4)
    
    # 處理美股與台股不同的數據欄位
    pe_ratio = info.get('trailingPE', 'N/A')
    eps = info.get('trailingEps', 'N/A')
    roe = info.get('returnOnEquity', 0) * 100
    div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
    
    m1.metric("本益比 (PE)", f"{pe_ratio if isinstance(pe_ratio, (int, float)) else 'N/A':.2f}")
    m2.metric("每股盈餘 (EPS)", f"{eps if isinstance(eps, (int, float)) else 'N/A':.2f}")
    m3.metric("股東權益報酬率 (ROE)", f"{roe:.2f}%")
    m4.metric("股息殖利率", f"{div_yield:.2f}%")

    # --- 第二區塊：技術面與價格行為 (Price Action) ---
    st.divider()
    st.subheader("📈 技術面分析 (均線系統)")
    
    # 計算專業分析常用的均線: 月線(20MA)、季線(60MA)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()

    fig = go.Figure()
    # K線圖 (Candlestick)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'], name='K線'))
    # 均線
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1), name='20MA (月線)'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='purple', width=1), name='60MA (季線)'))

    fig.update_layout(height=600, xaxis_rangeslider_visible=False, 
                      template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # --- 第三區塊：研究洞察與市場訊息 ---
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("🔍 財務健康度摘要")
        metrics_df = pd.DataFrame({
            "指標項目": ["市值", "營收成長 (YoY)", "營業利益率", "負債比率 (Debt/Equity)"],
            "數據": [
                f"{info.get('marketCap', 0):,}",
                f"{info.get('revenueGrowth', 0)*100:.2f}%",
                f"{info.get('operatingMargins', 0)*100:.2f}%",
                f"{info.get('debtToEquity', 'N/A')}"
            ]
        })
        st.table(metrics_df)

    with col_right:
        st.subheader("📰 市場關鍵情報 (News Feed)")
        news = stock_obj.news[:8]
        if news:
            for n in news:
                st.write(f"**{n['title']}**")
                st.caption(f"來源: {n['publisher']} | {datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d')}")
                st.markdown(f"[閱讀分析報告]({n['link']})")
                st.divider()
        else:
            st.info("目前無即時重大訊息。")

except Exception as e:
    st.error(f"數據解析異常。提示：如果是台股，請確保代碼後方有加上 .TW (例如 2330.TW)。詳細錯誤：{e}")
