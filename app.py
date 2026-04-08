import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; font-size: 18px; }
    .ai-insight { background: #fdfdfd; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; border-top: 6px solid #28a745; margin-bottom: 25px; }
    .news-card { background: white; padding: 15px; border-radius: 8px; border-left: 5px solid #1f77b4; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.title("📈 我的決策終端 - My Tool")

# --- 側邊欄 ---
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"台北時間：{now_tw.strftime('%Y-%m-%d %H:%M')}")

# --- 數據抓取模組 ---
@st.cache_data(ttl=300)
def get_full_analysis_data(ticker):
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    
    # 1. 股價與成交量
    df_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date=(now_tw - timedelta(days=365)).strftime('%Y-%m-%d'))
    if not df_price.empty:
        df_price = df_price.rename(columns={'date':'Date','open':'Open','max':'High','min':'Low','close':'Close','vol':'Volume'})
        df_price['Date'] = pd.to_datetime(df_price['Date'])
        df_price.set_index('Date', inplace=True)

    # 2. 新聞與基本面 (yfinance)
    y_stock = yf.Ticker(ticker)
    y_info = y_stock.info
    y_news = y_stock.news
    
    # 3. 營收數據
    df_rev = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    
    return df_price, y_news, df_rev, y_info

# --- 計算 RSI 指標 ---
def calculate_rsi(data, window=14):
    diff = data.diff(1)
    gain = diff.where(diff > 0, 0)
    loss = -diff.where(diff < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- AI 進階觀察總結 ---
def generate_advanced_ai_insight(df_p, df_r, info, ticker):
    try:
        curr_p = df_p['Close'].iloc[-1]
        # 技術面指標
        rsi = calculate_rsi(df_p['Close']).iloc[-1]
        ma20 = df_p['Close'].rolling(20).mean().iloc[-1]
        
        # 基本面指標
        pb_ratio = info.get('priceToBook', 'N/A')
        div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        
        # 營收動能
        rev_mom = ((df_r['revenue'].iloc[-1] - df_r['revenue'].iloc[-2]) / df_r['revenue'].iloc[-2]) * 100
        
        insight = f"""
        <div class="ai-insight">
            <h3 style="margin-top:0;">🤖 AI 深度分析報告 ({ticker})</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div><b>📈 技術評價：</b>{'超買(熱)' if rsi > 70 else '超賣(冷)' if rsi < 30 else '中性'} (RSI: {rsi:.1f})<br>
                     <b>💡 趨勢力道：</b>{'強勁' if curr_p > ma20 else '疲弱'} (價格於月線{'上' if curr_p > ma20 else '下'})</div>
                <div><b>💰 估值參考：</b>P/B 比: {pb_ratio if isinstance(pb_ratio, float) else 'N/A'}<br>
                     <b>📊 收益能力：</b>營收月增 {rev_mom:.1f}% | 殖利率: {div_yield:.2f}%</div>
            </div>
            <p style="margin-top:15px; border-top: 1px solid #eee; padding-top:10px;">
                <b>分析師建議：</b>目前標的{'估值偏低且動能轉強' if isinstance(pb_ratio, float) and pb_ratio < 2 and rev_mom > 0 else '進入高檔震盪區'}，建議關注{'支撐位' if rsi < 50 else '獲利了結機會'}。
            </p>
        </div>
        """
        return insight
    except:
        return "<div class='ai-insight'>⚠️ 數據不足，無法產生 AI 總結。</div>"

# --- 主執行區 ---
try:
    df_p, news_list, df_r, info = get_full_analysis_data(ticker_input)

    tab1, tab2, tab3 = st.tabs(["📉 專業技術終端", "📊 深度財報分析", "📰 即時市場情報"])

    with tab1:
        if not df_p.empty:
            # 頂部指標
            c1, c2, c3 = st.columns(3)
            curr_p = df_p['Close'].iloc[-1]
            c1.metric("當前報價", f"{curr_p:.2f}")
            c2.metric("P/B 比 (估值)", f"{info.get('priceToBook', 'N/A')}")
            c3.metric("RSI 指標", f"{calculate_rsi(df_p['Close']).iloc[-1]:.1f}")

            # 繪製進階副圖 (K線 + RSI + 成交量)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.05, row_heights=[0.5, 0.2, 0.3])
            
            # 1. K線圖
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], 
                                         low=df_p['Low'], close=df_p['Close'], name='K線'), row=1, col=1)
            
            # 2. RSI 圖
            rsi_series = calculate_rsi(df_p['Close'])
            fig.add_trace(go.Scatter(x=df_p.index, y=rsi_series, line=dict(color='#FF5722'), name='RSI(14)'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

            # 3. 成交量
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='成交量', marker_color='#1f77b4'), row=3, col=1)

            fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        if not df_r.empty:
            df_r['date_fixed'] = pd.to_datetime(df_r['revenue_year'].astype(str) + '-' + df_r['revenue_month'].astype(str) + '-01')
            st.markdown(generate_advanced_ai_insight(df_p, df_r, info, ticker_input), unsafe_allow_html=True)
            
            fig_rev = go.Figure()
            fig_rev.add_trace(go.Bar(x=df_r['date_fixed'], y=df_r['revenue'], name='單月營收'))
            fig_rev.update_layout(title="營收長期走勢圖", template="plotly_white")
            st.plotly_chart(fig_rev, use_container_width=True)

    with tab3:
        if news_list:
            for n in news_list[:12]:
                pub_date = datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M')
                st.markdown(f'<div class="news-card"><b><a href="{n.get("link","#")}" target="_blank">{n.get("title")}</a></b><br><small>{n.get("publisher")} | {pub_date}</small></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"分析異常: {e}")
