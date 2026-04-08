import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
try:
    from FinMind.data import DataLoader
except ImportError:
    st.error("系統正在安裝組件，請點擊右下角 Manage app -> Reboot 確保環境完整。")

# --- 專業介面設定 ---
st.set_page_config(page_title="My Tool", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .news-card { background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #1f77b4; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stMetric { background-color: white; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 My Tool")

# --- 側邊欄 ---
st.sidebar.header("📊 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW 或 NVDA)", value="2330.TW").upper()
period_map = {"3個月": 90, "6個月": 180, "1年": 365, "2年": 730}
selected_label = st.sidebar.selectbox("分析週期", list(period_map.keys()), index=1)
days = period_map[selected_label]

# --- 數據抓取函數 ---
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker, days):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    try:
        if ".TW" in ticker:
            dl = DataLoader()
            df = dl.taiwan_stock_daily(stock_id=ticker.split(".")[0], 
                                       start_date=start_date.strftime('%Y-%m-%d'), 
                                       end_date=end_date.strftime('%Y-%m-%d'))
            df = df.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close'})
            df.set_index('Date', inplace=True)
            df.index = pd.to_datetime(df.index)
            return df, "FinMind (台股通道)"
        else:
            df = yf.Ticker(ticker).history(period=f"{days}d")
            return df, "yfinance (美股通道)"
    except:
        return None, "連線失敗"

@st.cache_data(ttl=3600)
def fetch_market_news(ticker):
    """專屬新聞抓取邏輯：台股走 FinMind，美股走 Yahoo"""
    news_list = []
    if ".TW" in ticker:
        try:
            dl = DataLoader()
            # 抓取最近 7 天的新聞
            raw_news = dl.taiwan_stock_news(stock_id=ticker.split(".")[0], 
                                            start_date=(datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d'))
            for _, row in raw_news.iterrows():
                news_list.append({
                    "title": row['title'],
                    "publisher": row['source'],
                    "link": row['link'],
                    "date": row['date']
                })
        except: pass
    else:
        try:
            y_news = yf.Ticker(ticker).news
            for n in y_news:
                news_list.append({
                    "title": n['title'],
                    "publisher": n['publisher'],
                    "link": n['link'],
                    "date": datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d')
                })
        except: pass
    return news_list

# --- 介面呈現 ---
try:
    df, source_name = fetch_stock_data(ticker_input, days)
    
    if df is not None and not df.empty:
        # 1. 頂部指標
        c1, c2, c3 = st.columns(3)
        curr_p = df['Close'].iloc[-1]
        prev_p = df['Close'].iloc[-2]
        diff = curr_p - prev_p
        c1.metric(f"{ticker_input} 最新價格", f"{curr_p:.2f}", f"{diff:.2f} ({ (diff/prev_p)*100 :.2f}%)")
        c2.metric("數據來源", source_name)
        c3.metric("更新時間", datetime.now().strftime('%H:%M:%S'))

        # 2. 技術圖表
        st.subheader("📈 價格走勢與技術形態")
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#FFA500', width=1), name='20MA'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#800080', width=1), name='60MA'))
        fig.update_layout(height=450, xaxis_rangeslider_visible=False, template="plotly_white", margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

        # 3. 新聞區塊 (獨立渲染)
        st.divider()
        st.subheader("📰 重大訊息與相關新聞")
        news_data = fetch_market_news(ticker_input)
        
        if news_data:
            for n in news_data:
                st.markdown(f"""
                <div class="news-card">
                    <div style="font-weight: bold; font-size: 16px;"><a href="{n['link']}" target="_blank" style="text-decoration: none; color: #1f77b4;">{n['title']}</a></div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">來源: {n['publisher']} | 日期: {n['date']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ 目前無法從 Yahoo/FinMind 獲取新聞。這通常是 API 流量限制，請稍候再試。")

    else:
        st.error("無法載入股價數據。請檢查代碼是否正確或重啟 App。")

except Exception as e:
    st.error(f"系統異常：{e}")
