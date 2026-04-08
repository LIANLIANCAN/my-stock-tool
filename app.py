import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

try:
    from FinMind.data import DataLoader
except ImportError:
    st.error("組件安裝中... 請點擊右下角 'Manage app' -> 'Reboot App'。")

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

st.title("📈 My Tool")

# --- 側邊欄 ---
st.sidebar.header("🔍 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"台北時間：{now_tw.strftime('%Y-%m-%d %H:%M')}")

# --- 數據抓取模組 ---
@st.cache_data(ttl=300)
def get_full_analysis_data(ticker):
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    
    # 1. 股價與成交量 (使用防禦性更強的欄位對齊)
    df_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date=(now_tw - timedelta(days=365)).strftime('%Y-%m-%d'))
    if not df_price.empty:
        # 強制尋找成交量欄位
        vol_col = 'vol' if 'vol' in df_price.columns else 'Trading_Volume' if 'Trading_Volume' in df_price.columns else None
        rename_map = {'date':'Date','open':'Open','max':'High','min':'Low','close':'Close'}
        if vol_col: rename_map[vol_col] = 'Volume'
        
        df_price = df_price.rename(columns=rename_map)
        df_price['Date'] = pd.to_datetime(df_price['Date'])
        df_price.set_index('Date', inplace=True)

    # 2. 新聞與基本面
    y_stock = yf.Ticker(ticker)
    try:
        y_info = y_stock.info
        y_news = y_stock.news
    except:
        y_info = {}
        y_news = []
    
    # 3. 營收數據 (僅對個股有效)
    try:
        df_rev = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    except:
        df_rev = pd.DataFrame()
    
    return df_price, y_news, df_rev, y_info

# --- 計算 RSI ---
def calculate_rsi(data, window=14):
    if len(data) < window: return pd.Series([50]*len(data))
    diff = data.diff(1)
    gain = diff.where(diff > 0, 0)
    loss = -diff.where(diff < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# --- AI 投資觀察總結 (ETF 友善版) ---
def generate_ai_summary(df_p, df_r, info, ticker):
    try:
        curr_p = df_p['Close'].iloc[-1]
        rsi = calculate_rsi(df_p['Close']).iloc[-1]
        ma20 = df_p['Close'].rolling(20).mean().iloc[-1]
        
        # 判斷是 ETF 還是個股
        is_etf = df_r.empty
        rev_text = "N/A (ETF無月營收)" if is_etf else f"{((df_r['revenue'].iloc[-1]-df_r['revenue'].iloc[-2])/df_r['revenue'].iloc[-2]*100):.1f}%"
        
        insight = f"""
        <div class="ai-insight">
            <h3 style="margin-top:0;">🤖 AI 投資觀察總結 ({ticker})</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div><b>技術面：</b>{'過熱' if rsi > 70 else '超賣' if rsi < 30 else '中性'} (RSI: {rsi:.1f})<br>
                     <b>趨勢：</b>{'強勢' if curr_p > ma20 else '弱勢'} (站於月線上: {'是' if curr_p > ma20 else '否'})</div>
                <div><b>估值參考：</b>股價淨值比: {info.get('priceToBook', 'N/A')}<br>
                     <b>動能指標：</b>營收月增: {rev_text}</div>
            </div>
            <p style="margin-top:15px; border-top: 1px solid #eee; padding-top:10px;">
                <b>分析建議：</b>目前標的處於{'多頭排列' if curr_p > ma20 else '盤整階段'}。{'ETF 建議關注長線均線支撐。' if is_etf else '建議結合營收動能進行判斷。'}
            </p>
        </div>
        """
        return insight
    except:
        return "<div class='ai-insight'>⚠️ AI 分析計算中...</div>"

# --- 主程式呈現 ---
try:
    df_p, news_list, df_r, info = get_full_analysis_data(ticker_input)

    tab1, tab2, tab3 = st.tabs(["📉 技術面分析", "📊 財報深度分析", "📰 即時市場情報"])

    with tab1:
        if not df_p.empty:
            c1, c2, c3 = st.columns(3)
            curr_p = df_p['Close'].iloc[-1]
            c1.metric("最新報價", f"{curr_p:.2f}")
            c2.metric("股價淨值比 (P/B)", f"{info.get('priceToBook', 'N/A')}")
            c3.metric("RSI (相對強弱)", f"{calculate_rsi(df_p['Close']).iloc[-1]:.1f}")

            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.2, 0.3])
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='K線'), row=1, col=1)
            
            rsi_val = calculate_rsi(df_p['Close'])
            fig.add_trace(go.Scatter(x=df_p.index, y=rsi_val, line=dict(color='#FF5722'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

            if 'Volume' in df_p.columns:
                fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='成交量', marker_color='#1f77b4'), row=3, col=1)

            fig.update_layout(height=800, xaxis_rangeslider_visible=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown(generate_ai_summary(df_p, df_r, info, ticker_input), unsafe_allow_html=True)
        if not df_r.empty:
            df_r['date_fixed'] = pd.to_datetime(df_r['revenue_year'].astype(str) + '-' + df_r['revenue_month'].astype(str) + '-01')
            fig_rev = go.Figure()
            fig_rev.add_trace(go.Bar(x=df_r['date_fixed'], y=df_r['revenue'], name='月營收'))
            fig_rev.update_layout(title="每月營收走勢", template="plotly_white")
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.info("💡 提醒：ETF (如 0050) 無單月營收資料。請參考成分股配息與淨值變化。")

    with tab3:
        if news_list:
            for n in news_list[:12]:
                pub_date = datetime.fromtimestamp(n.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M') if n.get('providerPublishTime') else "即時"
                st.markdown(f'<div class="news-card"><b><a href="{n.get("link","#")}" target="_blank">{n.get("title")}</a></b><br><small>{n.get("publisher")} | {pub_date}</small></div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ 暫時無法獲取新聞數據。")

except Exception as e:
    st.error(f"系統異常：{e}")
