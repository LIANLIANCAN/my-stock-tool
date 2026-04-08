import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import feedparser
import re

# --- 專業介面設定 ---
st.set_page_config(page_title="My Tool", layout="wide", page_icon="📈")
TW_OFFSET = timedelta(hours=8)
now_tw = datetime.utcnow() + TW_OFFSET

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; font-size: 18px; }
    .ai-insight { background: #fdfdfd; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; border-top: 6px solid #28a745; margin-bottom: 25px; }
    .news-card { background: white; padding: 18px; border-radius: 8px; border-left: 6px solid #1f77b4; margin-bottom: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.08); }
    .news-title { font-size: 18px; font-weight: bold; color: #1f77b4; text-decoration: none; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 My Tool")

# --- 側邊欄 ---
st.sidebar.header("🔍 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"台北時間：{now_tw.strftime('%Y-%m-%d %H:%M')}")

# --- 數據抓取引擎 ---
@st.cache_data(ttl=300)
def get_data_engine(ticker):
    from FinMind.data import DataLoader
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    
    # 1. 抓取股價並自動對齊欄位
    df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=(now_tw - timedelta(days=365)).strftime('%Y-%m-%d'))
    if not df.empty:
        # 自動偵測成交量欄位 (防禦性邏輯)
        vol_col = next((c for c in df.columns if c in ['vol', 'Trading_Shares', 'Volume']), None)
        df = df.rename(columns={'date':'Date', 'open':'Open', 'max':'High', 'min':'Low', 'close':'Close'})
        if vol_col:
            df = df.rename(columns={vol_col: 'Volume'})
        else:
            df['Volume'] = 0 # 若真的沒抓到，補 0 避免當機
            
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
    
    # 2. 抓取營收
    try:
        df_r = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    except:
        df_r = pd.DataFrame()

    # 3. 抓取 Google 即時新聞
    query = f"{stock_id}+股票" if ".TW" in ticker else ticker
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    news = []
    for e in feed.entries[:10]:
        news.append({"title": re.sub(r' - .*$', '', e.title), "link": e.link, "source": e.source.get('title', '媒體'), "time": e.published})
    
    # 4. 抓取 yf 基本面
    try:
        info = yf.Ticker(ticker).info
    except:
        info = {}
        
    return df, df_r, news, info

# --- 執行主程式 ---
try:
    df_p, df_r, news_list, info = get_data_engine(ticker_input)

    tab1, tab2, tab3 = st.tabs(["📉 技術面分析", "📊 財報深度分析", "📰 即時市場情報"])

    with tab1:
        if not df_p.empty:
            c1, c2, c3 = st.columns(3)
            curr_p = df_p['Close'].iloc[-1]
            diff = curr_p - df_p['Close'].iloc[-2]
            c1.metric("最新報價", f"{curr_p:.2f}", f"{diff:.2f}")
            c2.metric("股價淨值比 (P/B)", f"{info.get('priceToBook', 'N/A')}")
            
            # RSI 計算
            delta = df_p['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi = 100 - (100 / (1 + gain/loss)).iloc[-1]
            c3.metric("RSI (14)", f"{rsi:.1f}")

            # 專業圖表
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='成交量', marker_color='#1f77b4'), row=2, col=1)
            fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if not df_r.empty:
            # AI 總結
            rev_mom = ((df_r['revenue'].iloc[-1] - df_r['revenue'].iloc[-2]) / df_r['revenue'].iloc[-2]) * 100
            st.markdown(f"""
            <div class="ai-insight">
                <h3 style="margin-top:0;">🤖 AI 投資觀察總結 ({ticker_input})</h3>
                <li><b>財務動能：</b>本月營收月增率 <b>{rev_mom:.2f}%</b>，營運動能{'持穩' if rev_mom > 0 else '轉弱'}。</li>
                <li><b>估值水位：</b>P/B 比為 {info.get('priceToBook', 'N/A')}，位於歷史{'中高' if info.get('priceToBook', 0) > 2 else '合理'}區間。</li>
            </div>
            """, unsafe_allow_html=True)
            
            # 營收圖
            df_r['date_fixed'] = pd.to_datetime(df_r['revenue_year'].astype(str) + '-' + df_r['revenue_month'].astype(str) + '-01')
            fig_rev = go.Figure(go.Bar(x=df_r['date_fixed'], y=df_r['revenue'], name='月營收'))
            fig_rev.update_layout(title="每月營收走勢", template="plotly_white")
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.info("暫無財報數據，ETF 請參考技術面。")

    with tab3:
        if news_list:
            for n in news_list:
                st.markdown(f"""
                <div class="news-card">
                    <a class="news-title" href="{n['link']}" target="_blank">{n['title']}</a>
                    <div style="font-size: 13px; color: #666; margin-top: 8px;">來源: {n['source']} | 發佈時間: {n['time']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("即時新聞抓取中，請稍候。")

except Exception as e:
    st.error(f"系統異常：{e}")
