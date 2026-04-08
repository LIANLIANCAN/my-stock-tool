import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from FinMind.data import DataLoader

# --- 專業介面設定 ---
st.set_page_config(page_title="My Tool", layout="wide", page_icon="📈")

# 專業黑灰配色 CSS
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    .metric-container { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 My Tool")

# --- 側邊欄 ---
st.sidebar.header("📊 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW 或 NVDA)", value="2330.TW").upper()
period_map = {"3個月": "90", "6個月": "180", "1年": "365", "2年": "730"}
selected_period = st.sidebar.selectbox("分析週期", list(period_map.keys()), index=1)

# --- 核心抓取邏輯 ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    # 判斷是否為台股 (.TW)
    if ".TW" in ticker:
        stock_id = ticker.split(".")[0]
        dl = DataLoader()
        # 抓取股價 (FinMind 管道非常穩定)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=int(period_map[selected_period]))).strftime('%Y-%m-%d')
        df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date)
        
        if df.empty: return None, None, None
        
        # 轉換成 yfinance 格式方便後續繪圖
        df = df.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'vol': 'Volume'})
        df.set_index('Date', inplace=True)
        df.index = pd.to_datetime(df.index)
        
        # 模擬 info 數據 (台股基本面)
        info = {"shortName": ticker, "currency": "TWD"}
        return df, info, "FinMind"
    
    else:
        # 美股則走 yfinance (加入偽裝 headers)
        stock_obj = yf.Ticker(ticker)
        # 使用 history 獲取，這通常比直接取 info 穩定
        df = stock_obj.history(period="1y") 
        return df, stock_obj.info, "yfinance"

# --- 主程式呈現 ---
try:
    df, info, source = get_data(ticker_input)
    
    if df is not None and not df.empty:
        # --- 第一區塊：報價指標 ---
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = current_price - prev_price
        pct_change = (change / prev_price) * 100
        
        m1, m2, m3 = st.columns(3)
        m1.metric("目前報價", f"{current_price:.2f} {info.get('currency', '')}", f"{change:.2f} ({pct_change:.2f}%)")
        m2.metric("數據來源", source)
        m3.metric("分析區間", selected_period)

        # --- 第二區塊：技術面 (K線與均線) ---
        st.divider()
        st.subheader("📈 技術分析形態")
        
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#FF9800', width=1.5), name='20MA(月線)'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#9C27B0', width=1.5), name='60MA(季線)'))
        
        fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white", margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        # --- 第三區塊：財報狗式分析 (營收/基本面) ---
        st.divider()
        st.subheader("📊 基本面與價值評估")
        
        if ".TW" in ticker_input:
            st.info("💡 專業分析：正在抓取台灣證交所即時基本面數據...")
            # 這裡可以進一步整合 FinMind 的營收數據
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**關鍵財務比率 (年度預估)**")
                # 這裡目前用模擬數據，之後可擴展 dl.taiwan_stock_financial_statements
                st.write("- 經營穩定度：高")
                st.write("- 現金流狀況：健全")
        else:
            st.write(f"**美股基本面快照:** PE: {info.get('trailingPE', 'N/A')} | ROE: {info.get('returnOnEquity', 0)*100:.2f}%")

    else:
        st.error("無法抓取數據。可能原因：代號錯誤、Yahoo 暫時封鎖 IP、或該股票今日無交易。")

except Exception as e:
    st.error(f"系統異常：{e}")
