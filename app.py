import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
try:
    from FinMind.data import DataLoader
except ImportError:
    st.error("組件安裝中，請執行 Reboot App。")

# --- 專業介面與時區設定 ---
st.set_page_config(page_title="My Tool", layout="wide", page_icon="📈")
TW_OFFSET = timedelta(hours=8)
now_tw = datetime.utcnow() + TW_OFFSET

st.markdown("""
    <style>
    .reportview-container { background: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 My Tool")

# --- 側邊欄：研究參數 ---
st.sidebar.header("📊 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.caption(f"台北時間: {now_tw.strftime('%Y-%m-%d %H:%M:%S')}")

# --- 數據抓取模組 (強化即時性) ---
@st.cache_data(ttl=600) # 縮短快取至 10 分鐘，確保新聞即時
def get_pro_data(ticker):
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    
    # 1. 抓取股價 (1年期)
    start_p = (now_tw - timedelta(days=365)).strftime('%Y-%m-%d')
    df_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_p)
    if not df_price.empty:
        df_price = df_price.rename(columns={'date':'Date','open':'Open','max':'High','min':'Low','close':'Close'})
        df_price['Date'] = pd.to_datetime(df_price['Date'])
        df_price.set_index('Date', inplace=True)

    # 2. 抓取即時新聞 (最近 14 天)
    start_n = (now_tw - timedelta(days=14)).strftime('%Y-%m-%d')
    df_news = dl.taiwan_stock_news(stock_id=stock_id, start_date=start_n)
    
    # 3. 財報分析數據 (營收)
    df_rev = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2023-01-01')
    
    return df_price, df_news, df_rev

# --- 主程式呈現 ---
try:
    df_price, df_news, df_rev = get_pro_data(ticker_input)

    # 建立分頁
    tab1, tab2, tab3 = st.tabs(["📉 技術面分析", "📊 財報分析", "📰 即時情報"])

    with tab1:
        # 價格指標
        curr_p = df_price['Close'].iloc[-1]
        prev_p = df_price['Close'].iloc[-2]
        diff = curr_p - prev_p
        st.metric(f"{ticker_input} 最新價格", f"{curr_p:.2f}", f"{diff:.2f} ({(diff/prev_p)*100:.2f}%)")

        # 技術圖表 (MA20/MA60)
        df_price['MA20'] = df_price['Close'].rolling(20).mean()
        df_price['MA60'] = df_price['Close'].rolling(60).mean()
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_price.index, open=df_price['Open'], high=df_price['High'], low=df_price['Low'], close=df_price['Close'], name='K線'))
        fig.add_trace(go.Scatter(x=df_price.index, y=df_price['MA20'], line=dict(color='orange'), name='20MA'))
        fig.add_trace(go.Scatter(x=df_price.index, y=df_price['MA60'], line=dict(color='purple'), name='60MA'))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("📌 財報核心：每月營收走勢")
        if not df_rev.empty:
            # 轉換時間格式
            df_rev['date'] = pd.to_datetime(df_rev['revenue_month'], format='%Y-%m-%d')
            fig_rev = go.Figure()
            fig_rev.add_trace(go.Bar(x=df_rev['date'], y=df_rev['revenue'], name='單月營收'))
            fig_rev.update_layout(title=f"{ticker_input} 營收變化 (單位:元)", template="plotly_white")
            st.plotly_chart(fig_rev, use_container_width=True)
            
            # 數據表摘要
            st.write("**營收明細表 (最近 6 個月)**")
            st.dataframe(df_rev[['revenue_month', 'revenue', 'revenue_month_growth_percent']].tail(6), use_container_width=True)
        else:
            st.warning("查無該標的之財報數據。")

    with tab3:
        st.subheader(f"🔥 即時重大訊息 (台北時間: {now_tw.strftime('%m/%d')})")
        if not df_news.empty:
            # 依照日期排序（最晚到最早）
            df_news = df_news.sort_values('date', ascending=False)
            for _, n in df_news.iterrows():
                with st.container():
                    st.markdown(f"**[{n['title']}]({n['link']})**")
                    st.caption(f"來源: {n['source']} | 發佈日期: {n['date']}")
                    st.divider()
        else:
            st.info("過去 14 天內無重大新聞訊息。")

except Exception as e:
    st.error(f"分析異常: {e}")
