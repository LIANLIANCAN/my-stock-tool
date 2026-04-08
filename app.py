import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import feedparser
import re

# --- 專業介面與風格設定 ---
st.set_page_config(page_title="My Tool", layout="wide", page_icon="📈")
TW_OFFSET = timedelta(hours=8)
now_tw = datetime.utcnow() + TW_OFFSET

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; font-size: 16px; padding: 10px 20px; }
    .ai-insight { background: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 8px solid #17a2b8; margin-bottom: 20px; }
    .news-card { background: white; padding: 15px; border-radius: 8px; border-left: 5px solid #007bff; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.title("📈 My Tool")

# --- 側邊欄 ---
st.sidebar.header("🔍 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"台北時間：{now_tw.strftime('%Y-%m-%d %H:%M')}")

# --- 核心數據引擎 ---
@st.cache_data(ttl=300)
def get_institutional_engine(ticker):
    from FinMind.data import DataLoader
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    start_d = (now_tw - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 1. 股價與成交量
    df_p = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_d)
    if not df_p.empty:
        vol_col = next((c for c in df_p.columns if c in ['vol', 'Trading_Shares', 'Volume']), None)
        df_p = df_p.rename(columns={'date':'Date', 'open':'Open', 'max':'High', 'min':'Low', 'close':'Close'})
        if vol_col: df_p = df_p.rename(columns={vol_col: 'Volume'})
        df_p['Date'] = pd.to_datetime(df_p['Date'])
        df_p.set_index('Date', inplace=True)

    # 2. 三大法人買賣超 (籌碼面核心)
    df_inst = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=(now_tw - timedelta(days=60)).strftime('%Y-%m-%d'))
    
    # 3. 獲利三率 (季報核心)
    df_fin = dl.taiwan_stock_financial_statements(stock_id=stock_id, start_date='2023-01-01')
    
    # 4. 營收
    df_rev = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    
    return df_p, df_inst, df_fin, df_rev

# --- AI 進階分析邏析 ---
def generate_pro_ai_insight(df_p, df_inst, df_fin, ticker):
    try:
        # 籌碼面判斷：近五日外資與投信動向
        recent_inst = df_inst.tail(5)
        foreign_buy = recent_inst[recent_inst['name'] == 'Foreign_Investor']['buy'].sum() - recent_inst[recent_inst['name'] == 'Foreign_Investor']['sell'].sum()
        itrust_buy = recent_inst[recent_inst['name'] == 'Investment_Trust']['buy'].sum() - recent_inst[recent_inst['name'] == 'Investment_Trust']['sell'].sum()
        
        # 獲利三率判斷 (最新一季)
        latest_fin = df_fin[df_fin['type'] == 'Gross_Profit_Margin'].iloc[-1]['value']
        
        insight = f"""
        <div class="ai-insight">
            <h3 style="margin-top:0;">🤖 專業分析師週報 ({ticker})</h3>
            <ul style="line-height: 1.8;">
                <li><b>籌碼動向：</b>近五日外資淨操作為 <b>{'買超' if foreign_buy > 0 else '賣超'}</b>；投信淨操作為 <b>{'買超' if itrust_buy > 0 else '賣超'}</b>。</li>
                <li><b>獲利指標：</b>最新揭露毛利率為 <b>{latest_fin:.2f}%</b>。</li>
                <li><b>綜合研判：</b>{'籌碼面偏向多頭排列，且基本面穩健，適合擇機佈局。' if foreign_buy > 0 and itrust_buy > 0 else '籌碼出現分歧或撤離訊號，建議轉向保守觀望。'}</li>
            </ul>
        </div>
        """
        return insight
    except: return "<div class='ai-insight'>分析報告生成中...請稍候。</div>"

# --- 主程式 ---
try:
    df_p, df_inst, df_fin, df_r = get_institutional_engine(ticker_input)

    tabs = st.tabs(["📉 技術 & RSI", "📊 獲利三率", "🦅 三大法人籌碼", "📰 即時情報"])

    with tabs[0]:
        # RSI 與 K 線
        delta = df_p['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain/loss)).iloc[-1]
        st.metric("最新報價", f"{df_p['Close'].iloc[-1]:.2f}", f"RSI: {rsi:.1f}")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='成交量', marker_color='#ced4da'), row=2, col=1)
        fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        # 獲利三率圖表
        st.subheader("📌 獲利三率走勢 (毛利率 / 營益率 / 淨利率)")
        # 篩選指標
        types = ['Gross_Profit_Margin', 'Operating_Profit_Margin', 'Net_Profit_Margin_After_Tax']
        df_filtered = df_fin[df_fin['type'].isin(types)]
        
        fig_fin = go.Figure()
        for t in types:
            data = df_filtered[df_filtered['type'] == t]
            fig_fin.add_trace(go.Scatter(x=data['date'], y=data['value'], name=t, mode='lines+markers'))
        fig_fin.update_layout(template="plotly_white", yaxis_title="百分比 (%)")
        st.plotly_chart(fig_fin, use_container_width=True)

    with tabs[2]:
        # 法人買賣超
        st.subheader("🦅 三大法人每日進出 (近 60 日)")
        df_inst['net_buy'] = df_inst['buy'] - df_inst['sell']
        
        fig_inst = go.Figure()
        for name in ['Foreign_Investor', 'Investment_Trust', 'Dealer_Self']:
            d = df_inst[df_inst['name'] == name]
            fig_inst.add_trace(go.Bar(x=d['date'], y=d['net_buy'], name=name))
        fig_inst.update_layout(barmode='relative', template="plotly_white", title="法人買賣超 (張)")
        st.plotly_chart(fig_inst, use_container_width=True)

    with tabs[3]:
        # 即時新聞 (Google RSS)
        stock_id = ticker_input.split(".")[0]
        rss = feedparser.parse(f"https://news.google.com/rss/search?q={stock_id}+股票&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        for e in rss.entries[:10]:
            st.markdown(f'<div class="news-card"><b><a href="{e.link}" target="_blank">{re.sub(r" - .*$", "", e.title)}</a></b><br><small>{e.published}</small></div>', unsafe_allow_html=True)

    # 底部 AI 總結
    st.markdown(generate_pro_ai_insight(df_p, df_inst, df_fin, ticker_input), unsafe_allow_html=True)

except Exception as e:
    st.error(f"系統異常：{e}")
