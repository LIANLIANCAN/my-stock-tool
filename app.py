import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
try:
    from FinMind.data import DataLoader
except ImportError:
    st.error("系統正在安裝組件中，請稍候並重新整理頁面。")

# --- 專業介面設定 ---
st.set_page_config(page_title="My Tool", layout="wide", page_icon="📈")

# 專業風格 CSS
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; color: #1f77b4; }
    .stTable { border: 1px solid #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 My Tool")

# --- 側邊欄 ---
st.sidebar.header("📊 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW 或 NVDA)", value="2330.TW").upper()
period_map = {"3個月": 90, "6個月": 180, "1年": 365, "2年": 730}
selected_label = st.sidebar.selectbox("分析週期", list(period_map.keys()), index=1)
days = period_map[selected_label]

@st.cache_data(ttl=3600)
def fetch_pro_data(ticker, days):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    if ".TW" in ticker:
        # 台股優先使用 FinMind 避開 Yahoo 封鎖
        try:
            dl = DataLoader()
            stock_id = ticker.split(".")[0]
            df = dl.taiwan_stock_daily(stock_id=stock_id, 
                                       start_date=start_date.strftime('%Y-%m-%d'), 
                                       end_date=end_date.strftime('%Y-%m-%d'))
            df = df.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'vol': 'Volume'})
            df.set_index('Date', inplace=True)
            df.index = pd.to_datetime(df.index)
            # 嘗試補抓基本面數據
            stock_info = yf.Ticker(ticker).info # 僅抓基本面
            return df, stock_info, "FinMind (穩定通道)"
        except:
            return None, None, "數據源連線失敗"
    else:
        # 美股直接用 yfinance
        s = yf.Ticker(ticker)
        return s.history(period=f"{days}d"), s.info, "yfinance (國際數據)"

# --- 執行與呈現 ---
try:
    df, info, source = fetch_pro_data(ticker_input, days)
    
    if df is not None and not df.empty:
        # 計算專業指標
        curr_p = df['Close'].iloc[-1]
        prev_p = df['Close'].iloc[-2]
        diff = curr_p - prev_p
        pct = (diff / prev_p) * 100
        
        # 顯示核心報價
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{ticker_input} 現價", f"{curr_p:.2f}", f"{diff:.2f} ({pct:.2f}%)")
        c2.metric("數據源", source)
        c3.metric("資料期間", selected_label)

        # --- 技術面：專業 K 線與均線 ---
        st.divider()
        st.subheader("📈 技術分析形態 (MA20/MA60)")
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#FFA500', width=1), name='20MA'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#800080', width=1), name='60MA'))
        fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        # --- 基本面：專業投資人關注指標 ---
        st.divider()
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("🔍 價值與成長指標")
            # 專業投資人看重的四大核心
            try:
                metrics = {
                    "指標項目": ["本益比 (PE)", "每股盈餘 (EPS)", "ROE (股東權益報酬)", "營收成長率 (YoY)"],
                    "數據內容": [
                        f"{info.get('trailingPE', 'N/A')}",
                        f"{info.get('trailingEps', 'N/A')}",
                        f"{info.get('returnOnEquity', 0)*100:.2f}%" if info.get('returnOnEquity') else "N/A",
                        f"{info.get('revenueGrowth', 0)*100:.2f}%" if info.get('revenueGrowth') else "N/A"
                    ]
                }
                st.table(pd.DataFrame(metrics))
            except:
                st.warning("基本面數據暫時無法由 Yahoo 取得。")

        with col_right:
            st.subheader("📰 市場焦點與重大訊息")
            news = yf.Ticker(ticker_input).news[:5]
            if news:
                for n in news:
                    st.markdown(f"**[{n['title']}]({n['link']})**")
                    st.caption(f"{n['publisher']} | {datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d')}")
            else:
                st.write("目前無相關重大訊息。")

    else:
        st.error("數據抓取失敗，請確認代碼是否正確。")

except Exception as e:
    st.error(f"系統運行錯誤: {e}")
