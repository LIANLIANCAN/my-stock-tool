import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# --- 專業介面設定 ---
st.set_page_config(page_title="My Tool", layout="wide", page_icon="📈")

# 自定義深色系專業風格
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .metric-card { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 8px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-top: 5px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# 修改標題為 My Tool
st.title("📈 My Tool")

# --- 側邊欄：研究參數 ---
st.sidebar.header("📊 研究對象")
ticker_symbol = st.sidebar.text_input("輸入證券代碼 (如 2330.TW 或 NVDA)", value="2330.TW").upper()
period = st.sidebar.selectbox("分析週期", ["3mo", "6mo", "1y", "2y", "5y"], index=2)

@st.cache_data(ttl=3600)
def fetch_analysis_data(ticker):
    stock = yf.Ticker(ticker)
    # 抓取歷史股價
    hist = stock.history(period=period)
    # 抓取基本面數據
    info = stock.info
    return stock, hist, info

try:
    stock_obj, df, info = fetch_analysis_data(ticker_symbol)
    
    # --- 第一區塊：核心獲利指標 (Key Financial Metrics) ---
    st.subheader("📌 獲利能力與估值分析")
    m1, m2, m3, m4 = st.columns(4)
    
    pe_ratio = info.get('trailingPE', 0)
    eps = info.get('trailingEps', 0)
    roe = info.get('returnOnEquity', 0) * 100
    div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
    
    with m1:
        st.metric("本益比 (PE)", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
    with m2:
        st.metric("每股盈餘 (EPS)", f"{eps:.2f}" if eps else "N/A")
    with m3:
        st.metric("ROE (股東權益報酬)", f"{roe:.2f}%" if roe else "N/A")
    with m4:
        st.metric("股息殖利率", f"{div_yield:.2f}%" if div_yield else "0.00%")

    # --- 第二區塊：技術形態分析 (Advanced Charting) ---
    st.divider()
    st.subheader("📈 技術分析走勢圖")
    
    # 計算專業分析師必看：月線(20MA)、季線(60MA)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()

    fig = go.Figure()
    # K線圖
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'], name='K線'))
    # 疊加均線
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#FF9800', width=1.5), name='20MA (月線)'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#9C27B0', width=1.5), name='60MA (季線)'))

    fig.update_layout(height=500, xaxis_rangeslider_visible=False, 
                      template="plotly_white", hovermode="x unified",
                      margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # --- 第三區塊：財務健康度與新聞 ---
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("🔍 財務結構快照")
        # 整理財報關鍵數據
        health_data = {
            "項目": ["總市值 (Market Cap)", "營收成長率 (YoY)", "營業利益率", "負債股本比 (D/E)"],
            "數值": [
                f"{info.get('marketCap', 0):,}",
                f"{info.get('revenueGrowth', 0)*100:.2f}%",
                f"{info.get('operatingMargins', 0)*100:.2f}%",
                f"{info.get('debtToEquity', 'N/A')}"
            ]
        }
        st.table(pd.DataFrame(health_data))

    with col_right:
        st.subheader("📰 全球市場即時情報")
        news = stock_obj.news[:6]
        if news:
            for n in news:
                with st.container():
                    st.write(f"**{n['title']}**")
                    st.caption(f"{n['publisher']} | {datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d')}")
                    st.markdown(f"[查看完整報告]({n['link']})")
                    st.divider()
        else:
            st.info("目前無相關重大訊息。")

except Exception as e:
    st.error(f"數據載入失敗。請檢查代碼是否輸入正確。錯誤資訊：{e}")
