import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import feedparser
import re
from dateutil import parser

# --- 專業介面設定 ---
st.set_page_config(page_title="My Tool", layout="wide", page_icon="📈")
TW_OFFSET = timedelta(hours=8)
now_tw = datetime.utcnow() + TW_OFFSET

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; font-size: 16px; padding: 10px 20px; }
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

# --- 核心數據引擎 (加入終極防禦) ---
@st.cache_data(ttl=300)
def get_institutional_v22_data(ticker):
    from FinMind.data import DataLoader
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    start_d = (now_tw - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 1. 股價與成交量 (終極容錯處理)
    df_p = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_d)
    if not df_p.empty:
        # 地毯式搜索所有可能的成交量名稱
        possible_vols = ['vol', 'Trading_Volume', 'Trading_Shares', 'Volume']
        vol_col = next((c for c in df_p.columns if c in possible_vols), None)
        
        rename_map = {'date':'Date', 'open':'Open', 'max':'High', 'min':'Low', 'close':'Close'}
        if vol_col: 
            rename_map[vol_col] = 'Volume'
            
        df_p = df_p.rename(columns=rename_map)
        
        # 終極防禦：如果改名後還是沒有 Volume，強制塞入 0 避免當機
        if 'Volume' not in df_p.columns:
            df_p['Volume'] = 0
            
        df_p['Date'] = pd.to_datetime(df_p['Date'])
        df_p.set_index('Date', inplace=True)

    # 2. 三大法人買賣超
    try:
        df_inst = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=(now_tw - timedelta(days=60)).strftime('%Y-%m-%d'))
    except:
        df_inst = pd.DataFrame()
    
    # 3. 獲利三率
    try:
        df_fin = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date='2023-01-01')
    except:
        df_fin = pd.DataFrame()
    
    # 4. 營收數據
    try:
        df_rev = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    except:
        df_rev = pd.DataFrame()

    # 5. Google 新聞
    query = f"{stock_id}+股票" if ".TW" in ticker else ticker
    rss = feedparser.parse(f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
    news_items = []
    for e in rss.entries:
        try:
            dt = parser.parse(e.published)
            news_items.append({
                "title": re.sub(r' - .*$', '', e.title), 
                "link": e.link, "source": e.source.get('title', '媒體'), 
                "ts": dt, "display": dt.strftime('%m-%d %H:%M')
            })
        except: continue
    news_items.sort(key=lambda x: x['ts'], reverse=True)
    
    # 6. 基本面
    try:
        info = yf.Ticker(ticker).info
    except:
        info = {}
        
    return df_p, df_inst, df_fin, df_rev, news_items, info

# --- 執行主程式 ---
try:
    df_p, df_inst, df_fin, df_rev, news_list, info = get_institutional_v22_data(ticker_input)

    tabs = st.tabs(["📉 技術 & RSI", "📊 獲利三率", "🦅 三大法人籌碼", "📰 即時市場情報"])

    with tabs[0]:
        if not df_p.empty:
            c1, c2, c3 = st.columns(3)
            curr_p = df_p['Close'].iloc[-1]
            c1.metric("最新報價", f"{curr_p:.2f}", f"{curr_p - df_p['Close'].iloc[-2]:.2f}")
            c2.metric("股價淨值比 (P/B)", f"{info.get('priceToBook', 'N/A')}")
            
            # RSI 安全計算
            if len(df_p) >= 14:
                delta = df_p['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi = 100 - (100 / (1 + gain/loss)).iloc[-1]
            else:
                rsi = 50.0
            c3.metric("RSI (14)", f"{rsi:.1f}")

            # 繪圖 (使用 .get 安全取得成交量)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='K線'), row=1, col=1)
            
            volume_data = df_p.get('Volume', pd.Series(0, index=df_p.index))
            fig.add_trace(go.Bar(x=df_p.index, y=volume_data, name='成交量', marker_color='#ced4da'), row=2, col=1)
            
            fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("無法取得股價資料，請確認代碼。")

    with tabs[1]:
        st.subheader("📌 獲利三率走勢 (季報)")
        if not df_fin.empty:
            types = ['Gross_Profit_Margin', 'Operating_Profit_Margin', 'Net_Profit_Margin_After_Tax']
            df_filtered = df_fin[df_fin['type'].isin(types)]
            fig_fin = go.Figure()
            for t in types:
                d = df_filtered[df_filtered['type'] == t]
                fig_fin.add_trace(go.Scatter(x=d['date'], y=d['value'], name=t, mode='lines+markers'))
            fig_fin.update_layout(template="plotly_white", yaxis_title="%")
            st.plotly_chart(fig_fin, use_container_width=True)
        else:
            st.info("查無獲利三率數據。")

    with tabs[2]:
        st.subheader("🦅 三大法人每日淨買賣超 (張)")
        if not df_inst.empty:
            df_inst['net'] = df_inst['buy'] - df_inst['sell']
            fig_inst = go.Figure()
            inst_names = {'Foreign_Investor': '外資', 'Investment_Trust': '投信', 'Dealer_Self': '自營商'}
            for k, v in inst_names.items():
                d = df_inst[df_inst['name'] == k]
                fig_inst.add_trace(go.Bar(x=d['date'], y=d['net'], name=v))
            fig_inst.update_layout(barmode='relative', template="plotly_white")
            st.plotly_chart(fig_inst, use_container_width=True)
        else:
            st.info("查無三大法人籌碼數據。")

    with tabs[3]:
        st.subheader(f"🔥 市場即時情報 (最新發布優先)")
        if news_list:
            for n in news_list[:15]:
                st.markdown(f"""
                <div class="news-card">
                    <a class="news-title" href="{n['link']}" target="_blank">{n['title']}</a>
                    <div style="font-size: 13px; color: #666; margin-top: 8px;">來源: {n['source']} | 發佈時間: {n['display']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("新聞抓取中...")

    # --- 底部 AI 總結 ---
    st.divider()
    try:
        if not df_p.empty:
            recent_inst = df_inst.tail(3) if not df_inst.empty else pd.DataFrame()
            f_net = recent_inst[recent_inst['name'] == 'Foreign_Investor']['net'].sum() if not recent_inst.empty else 0
            st.markdown(f"""
            <div class="ai-insight">
                <h3 style="margin-top:0;">🤖 專業分析師總結 ({ticker_input})</h3>
                <li><b>籌碼熱度：</b>近三日外資淨操作為 <b>{'買超' if f_net > 0 else '賣超' if f_net < 0 else '中性'}</b>。</li>
                <li><b>技術指標：</b>RSI 目前為 <b>{rsi:.1f}</b>，處於{'高檔' if rsi > 70 else '低檔' if rsi < 30 else '常態'}區間。</li>
                <li><b>綜合建議：</b>結合籌碼面與技術面，若法人買超且 RSI 未過熱，可視為偏多訊號。</li>
            </div>
            """, unsafe_allow_html=True)
    except: pass

except Exception as e:
    st.error(f"系統異常：請確保輸入正確的代碼並 Reboot App。詳細錯誤: {e}")
