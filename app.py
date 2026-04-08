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
    .ai-insight { background: #fdfdfd; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 25px; }
    .ai-tech { border-left: 6px solid #1f77b4; }
    .ai-fund { border-left: 6px solid #2ca02c; }
    .ai-inst { border-left: 6px solid #ff7f0e; }
    .news-card { background: white; padding: 18px; border-radius: 8px; border-left: 6px solid #9467bd; margin-bottom: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.08); }
    .news-title { font-size: 18px; font-weight: bold; color: #333; text-decoration: none; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 My Tool")

# --- 側邊欄 ---
st.sidebar.header("🔍 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"台北時間：{now_tw.strftime('%Y-%m-%d %H:%M')}")

# --- 核心數據引擎 ---
@st.cache_data(ttl=300)
def get_institutional_v24_data(ticker):
    from FinMind.data import DataLoader
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    start_d = (now_tw - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 1. 股價與成交量
    df_p = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_d)
    if not df_p.empty:
        vol_col = next((c for c in df_p.columns if c in ['vol', 'Trading_Shares', 'Volume']), None)
        rename_map = {'date':'Date', 'open':'Open', 'max':'High', 'min':'Low', 'close':'Close'}
        if vol_col: rename_map[vol_col] = 'Volume'
        df_p = df_p.rename(columns=rename_map)
        if 'Volume' not in df_p.columns: df_p['Volume'] = 0
        df_p['Date'] = pd.to_datetime(df_p['Date'])
        df_p.set_index('Date', inplace=True)

    # 2. 三大法人買賣超
    try:
        df_inst = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=(now_tw - timedelta(days=60)).strftime('%Y-%m-%d'))
    except: df_inst = pd.DataFrame()
    
    # 3. 原始財報數據
    try:
        df_fin = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date='2022-01-01')
    except: df_fin = pd.DataFrame()

    # 4. Google 新聞
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
    
    # 5. 基本面
    try: info = yf.Ticker(ticker).info
    except: info = {}
        
    return df_p, df_inst, df_fin, news_items, info

# --- 執行主程式 ---
try:
    df_p, df_inst, df_fin, news_list, info = get_institutional_v24_data(ticker_input)

    tabs = st.tabs(["📉 技術 & RSI", "📊 獲利三率", "🦅 三大法人籌碼", "📰 即時市場情報"])

    # ==========================================
    # 分頁 1: 技術面分析
    # ==========================================
    with tabs[0]:
        if not df_p.empty:
            curr_p = df_p['Close'].iloc[-1]
            ma20 = df_p['Close'].rolling(20).mean().iloc[-1]
            
            # RSI 安全計算
            if len(df_p) >= 14:
                delta = df_p['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rsi = 100 - (100 / (1 + gain/loss)).iloc[-1]
            else: rsi = 50.0

            # 🎯 專屬技術面 AI 總結
            st.markdown(f"""
            <div class="ai-insight ai-tech">
                <h4 style="margin-top:0;">🤖 價格行為與技術面研判</h4>
                <li><b>趨勢強度：</b>目前股價 {'大於' if curr_p > ma20 else '小於'} 月均線 (20MA)，短期趨勢偏向 <b>{'多頭' if curr_p > ma20 else '空頭'}</b>。</li>
                <li><b>動能指標：</b>RSI(14) 為 {rsi:.1f}，顯示市場情緒處於 <b>{'過熱' if rsi > 70 else '超賣' if rsi < 30 else '中性穩健'}</b> 狀態。</li>
                <li><b>估值參考：</b>目前 P/B 比為 {info.get('priceToBook', 'N/A')}。</li>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("最新報價", f"{curr_p:.2f}", f"{curr_p - df_p['Close'].iloc[-2]:.2f}")
            c2.metric("月均線 (20MA)", f"{ma20:.2f}")
            c3.metric("RSI (14)", f"{rsi:.1f}")

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='K線'), row=1, col=1)
            volume_data = df_p.get('Volume', pd.Series(0, index=df_p.index))
            fig.add_trace(go.Bar(x=df_p.index, y=volume_data, name='成交量', marker_color='#ced4da'), row=2, col=1)
            fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white", margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

            # 將數據藏進展開器
            with st.expander("📄 檢視歷史價格明細數據"):
                st.dataframe(df_p.tail(10).sort_index(ascending=False), use_container_width=True)

    # ==========================================
    # 分頁 2: 財報分析
    # ==========================================
    with tabs[1]:
        if not df_fin.empty:
            plot_data = []
            for date, group in df_fin.groupby('date'):
                group = group.copy()
                group['search_key'] = group['type'].astype(str).fillna('') + " " + (group['origin_name'].astype(str).fillna('') if 'origin_name' in group.columns else '')
                
                rev = group[group['search_key'].str.contains('Revenue|營業收入', case=False, na=False)]['value'].sum()
                gp = group[group['search_key'].str.contains('GrossProfit|毛利', case=False, na=False)]['value'].sum()
                op = group[group['search_key'].str.contains('OperatingIncome|OperatingProfit|營業利益', case=False, na=False)]['value'].sum()
                ni = group[group['search_key'].str.contains('IncomeAfterTaxes|NetIncome|本期淨利', case=False, na=False)]['value'].sum()
                
                if rev > 0:
                    plot_data.append({
                        'date': date,
                        '毛利率': (gp / rev) * 100 if gp else None,
                        '營益率': (op / rev) * 100 if op else None,
                        '淨利率': (ni / rev) * 100 if ni else None
                    })
            
            if plot_data:
                df_plot = pd.DataFrame(plot_data)
                
                # 🎯 專屬財報面 AI 總結
                latest_gross = df_plot['毛利率'].dropna().iloc[-1] if df_plot['毛利率'].notna().any() else 0
                prev_gross = df_plot['毛利率'].dropna().iloc[-2] if len(df_plot['毛利率'].dropna()) > 1 else 0
                
                st.markdown(f"""
                <div class="ai-insight ai-fund">
                    <h4 style="margin-top:0;">🤖 企業獲利護城河研判</h4>
                    <li><b>最新毛利率：</b>本季為 <b>{latest_gross:.2f}%</b>，較上一季 {'成長' if latest_gross > prev_gross else '衰退'}。</li>
                    <li><b>利潤結構：</b>毛利率代表產品競爭力，營益率代表管理效能。若兩者同步攀升，代表本業獲利極佳。</li>
                </div>
                """, unsafe_allow_html=True)

                fig_fin = go.Figure()
                for col, color in zip(['毛利率', '營益率', '淨利率'], ['#1f77b4', '#ff7f0e', '#2ca02c']):
                    if df_plot[col].notna().any():
                        fig_fin.add_trace(go.Scatter(x=df_plot['date'], y=df_plot[col], name=col, mode='lines+markers', line=dict(width=2)))
                fig_fin.update_layout(template="plotly_white", yaxis_title="百分比 (%)", hovermode="x unified", margin=dict(t=20, b=20))
                st.plotly_chart(fig_fin, use_container_width=True)

                # 將數據藏進展開器
                with st.expander("📄 檢視獲利三率具體數值 (季報)"):
                    st.dataframe(df_plot.set_index('date').sort_index(ascending=False).style.format("{:.2f}%"), use_container_width=True)
            else:
                st.warning("無法解析出百分比利潤數據。")
        else:
            st.info("查無財報數據 (ETF無此資料)。")

    # ==========================================
    # 分頁 3: 籌碼分析
    # ==========================================
    with tabs[2]:
        if not df_inst.empty:
            df_inst['net'] = df_inst['buy'] - df_inst['sell']
            recent_f = df_inst[df_inst['name'] == 'Foreign_Investor'].tail(5)['net'].sum()
            recent_t = df_inst[df_inst['name'] == 'Investment_Trust'].tail(5)['net'].sum()

            # 🎯 專屬籌碼面 AI 總結
            st.markdown(f"""
            <div class="ai-insight ai-inst">
                <h4 style="margin-top:0;">🤖 聰明錢 (Smart Money) 資金流向</h4>
                <li><b>外資態度：</b>近五日累計 <b>{'買超' if recent_f > 0 else '賣超'}</b>，顯示國際資金傾向。</li>
                <li><b>投信態度：</b>近五日累計 <b>{'買超' if recent_t > 0 else '賣超'}</b>，代表內資/法人佈局方向。</li>
                <li><b>籌碼共識：</b>{'土洋合作，推升力道強勁。' if recent_f > 0 and recent_t > 0 else '土洋對作，籌碼較為凌亂。' if (recent_f * recent_t) < 0 else '法人同步撤出，留意賣壓。'}</li>
            </div>
            """, unsafe_allow_html=True)

            fig_inst = go.Figure()
            inst_names = {'Foreign_Investor': '外資', 'Investment_Trust': '投信', 'Dealer_Self': '自營商'}
            for k, v in inst_names.items():
                d = df_inst[df_inst['name'] == k]
                fig_inst.add_trace(go.Bar(x=d['date'], y=d['net'], name=v))
            fig_inst.update_layout(barmode='relative', template="plotly_white", margin=dict(t=20, b=20))
            st.plotly_chart(fig_inst, use_container_width=True)
        else:
            st.info("查無三大法人籌碼數據。")

    # ==========================================
    # 分頁 4: 新聞
    # ==========================================
    with tabs[3]:
        st.subheader(f"🔥 市場即時情報")
        if news_list:
            for n in news_list[:15]:
                st.markdown(f"""
                <div class="news-card">
                    <a class="news-title" href="{n['link']}" target="_blank">{n['title']}</a>
                    <div style="font-size: 13px; color: #666; margin-top: 8px;">來源: {n['source']} | 發佈: {n['display']}</div>
                </div>
                """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"系統異常：{e}")
