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
# 取得台北目前時間
now_tw = datetime.utcnow() + TW_OFFSET

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; font-size: 18px; }
    .news-card { background: white; padding: 15px; border-radius: 8px; border-left: 5px solid #1f77b4; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.title("📈 我的工具")

# --- 側邊欄 ---
st.sidebar.header("📊 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"台北時間：{now_tw.strftime('%Y-%m-%d %H:%M')}")

# --- 數據抓取模組 ---
@st.cache_data(ttl=300) # 縮短快取至 5 分鐘，確保極致即時性
def get_pro_data(ticker):
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    
    # 1. 股價
    df_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date=(now_tw - timedelta(days=365)).strftime('%Y-%m-%d'))
    if not df_price.empty:
        df_price = df_price.rename(columns={'date':'Date','open':'Open','max':'High','min':'Low','close':'Close'})
        df_price['Date'] = pd.to_datetime(df_price['Date'])
        df_price.set_index('Date', inplace=True)

    # 2. 即時新聞 (強制抓最近 30 天，確保不漏掉當日訊息)
    df_news = dl.taiwan_stock_news(stock_id=stock_id, start_date=(now_tw - timedelta(days=30)).strftime('%Y-%m-%d'))
    
    # 3. 營收數據 (財報狗核心)
    df_rev = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    
    return df_price, df_news, df_rev

# --- 主執行區 ---
try:
    df_p, df_n, df_r = get_pro_data(ticker_input)

    tab1, tab2, tab3 = st.tabs(["📉 技術面分析", "📊 財報分析", "📰 即時情報"])

    with tab1:
        # 價格摘要
        curr_p = df_p['Close'].iloc[-1]
        prev_p = df_p['Close'].iloc[-2]
        diff = curr_p - prev_p
        st.metric(f"{ticker_input} 最新價格", f"{curr_p:.2f}", f"{diff:.2f} ({(diff/prev_p)*100:.2f}%)")
        
        # 專業 K 線圖
        df_p['MA20'] = df_p['Close'].rolling(20).mean()
        df_p['MA60'] = df_p['Close'].rolling(60).mean()
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='K線'))
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['MA20'], line=dict(color='orange', width=1), name='20MA'))
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['MA60'], line=dict(color='purple', width=1), name='60MA'))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("📌 財報核心：每月營收走勢")
        if not df_r.empty:
            # --- 關鍵修正：修復日期解析錯誤 ---
            # 合併年與月，並強制設定為該月 1 號
            df_r['date_fixed'] = pd.to_datetime(
                df_r['revenue_year'].astype(str) + '-' + df_r['revenue_month'].astype(str) + '-01'
            )
            df_r = df_r.sort_values('date_fixed')

            fig_rev = go.Figure()
            fig_rev.add_trace(go.Bar(x=df_r['date_fixed'], y=df_r['revenue'], name='單月營收', marker_color='#1f77b4'))
            fig_rev.update_layout(title="每月營收變化 (單位: 元)", template="plotly_white")
            st.plotly_chart(fig_rev, use_container_width=True)
            
            st.write("**營收明細數據 (最近 6 個月)**")
            st.dataframe(df_r[['revenue_month', 'revenue', 'revenue_month_growth_percent']].tail(6), use_container_width=True)
        else:
            st.info("暫無財報數據。")

    with tab3:
        st.subheader(f"🔥 即時情報 (最後更新: {now_tw.strftime('%H:%M')})")
        if not df_n.empty:
            # 確保新聞日期由新到舊
            df_n['date'] = pd.to_datetime(df_n['date'])
            df_n = df_n.sort_values('date', ascending=False)
            
            for _, n in df_n.iterrows():
                st.markdown(f"""
                <div class="news-card">
                    <div style="font-weight: bold;"><a href="{n['link']}" target="_blank" style="text-decoration: none; color: #1f77b4;">{n['title']}</a></div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">來源: {n['source']} | 發佈: {n['date'].strftime('%Y-%m-%d %H:%M')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("當前時段查無重大訊息。")

except Exception as e:
    st.error(f"系統分析異常: {e}")
