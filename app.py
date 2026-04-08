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
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; font-size: 18px; }
    .ai-insight { background: #f0f7ff; padding: 20px; border-radius: 12px; border-left: 6px solid #007bff; margin-bottom: 25px; }
    .news-card { background: white; padding: 15px; border-radius: 8px; border-left: 5px solid #1f77b4; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.title("📈 我的工具")

# --- 側邊欄 ---
st.sidebar.header("📊 研究對象")
ticker_input = st.sidebar.text_input("輸入證券代碼 (如 2330.TW)", value="2330.TW").upper()
st.sidebar.write(f"台北時間：{now_tw.strftime('%Y-%m-%d %H:%M')}")

# --- 數據抓取模組 ---
@st.cache_data(ttl=300)
def get_pro_data(ticker):
    dl = DataLoader()
    stock_id = ticker.split(".")[0]
    
    # 1. 股價 (1年)
    df_price = dl.taiwan_stock_daily(stock_id=stock_id, start_date=(now_tw - timedelta(days=365)).strftime('%Y-%m-%d'))
    if not df_price.empty:
        df_price = df_price.rename(columns={'date':'Date','open':'Open','max':'High','min':'Low','close':'Close'})
        df_price['Date'] = pd.to_datetime(df_price['Date'])
        df_price.set_index('Date', inplace=True)

    # 2. 即時新聞 (改用 yfinance 確保 4/8 的即時性)
    y_stock = yf.Ticker(ticker)
    y_news = y_stock.news
    
    # 3. 營收數據
    df_rev = dl.taiwan_stock_month_revenue(stock_id=stock_id, start_date='2024-01-01')
    
    return df_price, y_news, df_rev

# --- AI 觀察總結邏輯 (模擬分析師) ---
def generate_ai_insight(df_p, df_r, ticker):
    try:
        # 營收分析
        latest_rev = df_r['revenue'].iloc[-1]
        prev_rev = df_r['revenue'].iloc[-2]
        rev_mom = ((latest_rev - prev_rev) / prev_rev) * 100
        
        # 股價趨勢分析
        curr_p = df_p['Close'].iloc[-1]
        ma20 = df_p['Close'].rolling(20).mean().iloc[-1]
        ma60 = df_p['Close'].rolling(60).mean().iloc[-1]
        
        trend = "多頭排列" if curr_p > ma20 > ma60 else "弱勢整理"
        rev_status = "成長" if rev_mom > 0 else "衰退"
        
        insight = f"""
        <div class="ai-insight">
            <h3 style="margin-top:0;">🤖 AI 投資觀察總結 ({ticker})</h3>
            <ul style="line-height: 1.6;">
                <li><b>財務動能：</b>本月營收較上月{rev_status} <b>{rev_mom:.2f}%</b>，顯示基本面數據{'轉強' if rev_mom > 0 else '承壓'}。</li>
                <li><b>技術形態：</b>股價目前處於 <b>{trend}</b>。{'價格站穩均線上方，建議關注突破機會。' if trend == "多頭排列" else '目前動能轉弱，需留意下方支撐。'}</li>
                <li><b>綜合評價：</b>基於財報動能與技術指標，建議投資人針對該標的採取 <b>{'偏多觀察' if rev_mom > 0 and trend == "多頭排列" else '中性保守'}</b> 之策略。</li>
            </ul>
        </div>
        """
        return insight
    except:
        return "<div class='ai-insight'>⚠️ 無法產生 AI 總結，請確保數據加載完整。</div>"

# --- 主執行區 ---
try:
    df_p, news_list, df_r = get_pro_data(ticker_input)

    tab1, tab2, tab3 = st.tabs(["📉 技術面分析", "📊 財報分析", "📰 即時情報"])

    with tab1:
        if not df_p.empty:
            curr_p = df_p['Close'].iloc[-1]
            prev_p = df_p['Close'].iloc[-2]
            diff = curr_p - prev_p
            st.metric(f"{ticker_input} 最新報價", f"{curr_p:.2f}", f"{diff:.2f} ({(diff/prev_p)*100:.2f}%)")
            
            df_p['MA20'] = df_p['Close'].rolling(20).mean()
            df_p['MA60'] = df_p['Close'].rolling(60).mean()
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='K線'))
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['MA20'], line=dict(color='orange'), name='20MA'))
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['MA60'], line=dict(color='purple'), name='60MA'))
            fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # --- 財報 AI 觀察總結 ---
        if not df_r.empty and not df_p.empty:
            # 預處理營收日期
            df_r['date_fixed'] = pd.to_datetime(df_r['revenue_year'].astype(str) + '-' + df_r['revenue_month'].astype(str) + '-01')
            df_r = df_r.sort_values('date_fixed')
            
            # 顯示 AI 總結
            st.markdown(generate_ai_insight(df_p, df_r, ticker_input), unsafe_allow_html=True)
            
            # 顯示營收圖表
            fig_rev = go.Figure()
            fig_rev.add_trace(go.Bar(x=df_r['date_fixed'], y=df_r['revenue'], name='單月營收', marker_color='#1f77b4'))
            fig_rev.update_layout(title="每月營收變化走勢", template="plotly_white")
            st.plotly_chart(fig_rev, use_container_width=True)
            
            st.write("**營收明細數據表**")
            df_r['calc_growth'] = df_r['revenue'].pct_change() * 100
            display_df = df_r[['revenue_year', 'revenue_month', 'revenue', 'calc_growth']].tail(6)
            display_df.columns = ['年', '月', '營收', '月增率(%)']
            st.dataframe(display_df.style.format({'營收': '{:,.0f}', '月增率(%)': '{:.2f}%'}), use_container_width=True)

    with tab3:
        st.subheader(f"🔥 市場即時情報 (台北時間: {now_tw.strftime('%m/%d')})")
        if news_list:
            for n in news_list[:10]: # 顯示前 10 則
                pub_date = datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
                st.markdown(f"""
                <div class="news-card">
                    <div style="font-weight: bold;"><a href="{n['link']}" target="_blank" style="text-decoration: none; color: #1f77b4;">{n['title']}</a></div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">來源: {n['publisher']} | 發佈: {pub_date}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ 暫時無法獲取即時新聞。")

except Exception as e:
    st.error(f"分析異常: {e}")
