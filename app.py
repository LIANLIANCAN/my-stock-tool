import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

# 網頁基本設定
st.set_page_config(page_title="My Tool", page_icon="📈", layout="wide")

# 自定義 CSS 讓介面更漂亮
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 My Tool | 智慧股市分析")

# --- 側邊欄 ---
st.sidebar.header("🔍 查詢設定")
ticker_symbol = st.sidebar.text_input("請輸入股票代號", value="AAPL").upper()
st.sidebar.info("美股如: NVDA, TSLA\n台股如: 2330.TW, 0050.TW")

# 建立 yf.Ticker 物件
stock = yf.Ticker(ticker_symbol)

# --- 1. 抓取資料函數 (增加快取與偽裝) ---
@st.cache_data(ttl=3600)
def get_stock_history(ticker):
    # 使用 history 獲取 1 個月資料
    df = stock.history(period="1mo")
    return df

@st.cache_data(ttl=3600)
def get_stock_news(ticker):
    return stock.news[:10]

# --- 2. 顯示邏輯 ---
col1, col2 = st.columns([2, 1])

# --- 左側：股價與圖表 ---
with col1:
    try:
        df = get_stock_history(ticker_symbol)
        if not df.empty:
            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[0]
            price_diff = current_price - prev_price
            pct_change = (price_diff / prev_price) * 100
            
            # 顯示現價指標
            st.metric(label=f"{ticker_symbol} 目前價格", 
                      value=f"{current_price:.2f}", 
                      delta=f"{price_diff:.2f} ({pct_change:.2f}%)")

            # Plotly 走勢圖
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', 
                                     line=dict(color='#007BFF', width=3), name='收盤價'))
            fig.update_layout(title="最近 30 天走勢", hovermode="x unified",
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 股價抓取受限，請稍後再試。")
    except Exception as e:
        st.error(f"股價載入失敗: {e}")

# --- 右側：AI 智慧分析 ---
with col2:
    st.subheader("🤖 AI 趨勢洞察")
    try:
        if not df.empty:
            # 簡單的 AI 分析邏輯
            avg_price = df['Close'].mean()
            volatility = df['Close'].std()
            
            st.info(f"""
            **【行銷分析觀點】**
            * **趨勢判讀**：該股目前較月初{'上升' if current_price > prev_price else '下跌'}了 {abs(pct_change):.1f}%。
            * **市場情緒**：波動率為 {volatility:.2f}，顯示市場情緒{'相對穩定' if volatility < (avg_price*0.05) else '較為波動'}。
            * **操作建議**：作為品牌策略考量，建議關注後續{'支撐位' if current_price < avg_price else '回檔風險'}。
            """)
        else:
            st.write("等待數據載入以產生 AI 分析...")
    except:
        st.write("暫時無法產生分析報告。")

# --- 下方：新聞區塊 (獨立運作) ---
st.divider()
st.subheader("📰 相關市場情報")
try:
    news_items = get_stock_news(ticker_symbol)
    if news_items:
        for n in news_items:
            with st.expander(n['title']):
                st.write(f"來源: {n['publisher']}")
                st.write(f"發布時間: {datetime.fromtimestamp(n['providerPublishTime'])}")
                st.markdown(f"[點我閱讀完整新聞]({n['link']})")
    else:
        st.write("目前沒有相關新聞。")
except Exception as e:
    st.write("新聞模組暫時無法運作，請稍後。")
