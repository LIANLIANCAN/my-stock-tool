import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import feedparser
import re

try:
    from FinMind.data import DataLoader
except ImportError:
    st.error("系統環境建置中，請點擊 Reboot App。")

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
    .news-meta { font-size: 13px; color: #666; margin-top: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 My Tool")

# --- 側邊欄 ---
st.sidebar.header("🔍 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"台北時間：{now_tw.strftime('%Y-%m-%d %H:%M:%S')}")

# --- 即時新聞抓取引擎 (Google News RSS) ---
@st.cache_data(ttl=300) # 每 5 分鐘強制更新一次
def fetch_realtime_news(ticker):
    stock_id = ticker.split(".")[0]
    # 針對台股與美股優化搜尋關鍵字
    query = f"{stock_id}+股票" if ".TW" in ticker else ticker
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    feed = feedparser.parse(rss_url)
    news_items = []
    
    for entry in feed.entries[:15]: # 抓取前 15 則
        # 簡單清理標題中的來源後綴
        clean_title = re.sub(r' - .*$', '', entry.title)
        news_items.append({
            "title": clean_title,
            "link": entry.link,
            "source": entry.source.get('title', '財經媒體'),
            "time": entry.published
        })
    return news_items

@st.cache_data(ttl=600)
def get_stock_and_rev(ticker):
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    # 股價
    df_p = dl.taiwan_stock_daily(stock_id=stock_id, start_date=(now_tw - timedelta(days=365)).strftime('%Y-%m-%d'))
    if not df_p.empty:
        df_p = df_p.rename(columns={'date':'Date','open':'Open','max':'High','min':'Low','close':'Close','vol':'Volume'})
        df_p['Date'] = pd.to_datetime(df_p['Date'])
        df_p.set_index('Date', inplace=True)
    # 營收
    try:
        df_r = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    except:
        df_r = pd.DataFrame()
    # 估值 (yf)
    try:
        info = yf.Ticker(ticker).info
    except:
        info = {}
    return df_p, df_r, info

# --- 主執行區 ---
try:
    df_p, df_r, info = get_stock_and_rev(ticker_input)
    
    tab1, tab2, tab3 = st.tabs(["📉 技術面分析", "📊 財報深度分析", "📰 即時市場情報"])

    with tab1:
        if not df_p.empty:
            c1, c2, c3 = st.columns(3)
            curr_p = df_p['Close'].iloc[-1]
            c1.metric("最新報價", f"{curr_p:.2f}")
            c2.metric("股價淨值比 (P/B)", f"{info.get('priceToBook', 'N/A')}")
            
            # 計算 RSI
            diff = df_p['Close'].diff(1)
            gain = diff.where(diff > 0, 0).rolling(14).mean()
            loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain/loss))).iloc[-1]
            c3.metric("RSI (14)", f"{rsi:.1f}")

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='成交量', marker_color='#1f77b4'), row=2, col=1)
            fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if not df_r.empty:
            df_r['date_fixed'] = pd.to_datetime(df_r['revenue_year'].astype(str) + '-' + df_r['revenue_month'].astype(str) + '-01')
            
            # AI 總結簡化版
            rev_mom = ((df_r['revenue'].iloc[-1]-df_r['revenue'].iloc[-2])/df_r['revenue'].iloc[-2]*100)
            st.markdown(f"""
            <div class="ai-insight">
                <h3 style="margin-top:0;">🤖 AI 投資觀察總結</h3>
                <li><b>營收動能：</b>月增率 {rev_mom:.2f}%，基本面{'穩健' if rev_mom > 0 else '震盪'}。</li>
                <li><b>估值評估：</b>P/B 比為 {info.get('priceToBook', 'N/A')}，建議參考同業平均。</li>
            </div>
            """, unsafe_allow_html=True)
            
            fig_rev = go.Figure(go.Bar(x=df_r['date_fixed'], y=df_r['revenue'], name='月營收'))
            fig_rev.update_layout(title="每月營收走勢", template="plotly_white")
            st.plotly_chart(fig_rev, use_container_width=True)

    with tab3:
        st.subheader(f"🔥 市場即時情報 (台北時間: {now_tw.strftime('%m/%d')})")
        # 點擊按鈕手動清除快取重新抓取
        if st.button("🔄 重新整理新聞"):
            st.cache_data.clear()
            
        real_news = fetch_realtime_news(ticker_input)
        
        if real_news:
            for n in real_news:
                st.markdown(f"""
                <div class="news-card">
                    <a class="news-title" href="{n['link']}" target="_blank">{n['title']}</a>
                    <div class="news-meta">來源: {n['source']} | 發佈時間: {n['time']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ 暫時無法獲取 Google 即時新聞，請確認代碼是否輸入正確。")

except Exception as e:
    st.error(f"系統異常：{e}")
