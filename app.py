import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 修改網頁分頁名稱為 My Tool
st.set_page_config(page_title="My Tool", layout="wide")

# 2. 修改主標題為 My Tool
st.title("🚀 My Tool")
st.write("輸入股票代號，快速查看現價、走勢圖與最新新聞。")

# --- 側邊欄：輸入區 ---
st.sidebar.header("查詢條件")
ticker_input = st.sidebar.text_input("請輸入股票代號", value="AAPL").upper() # 自動轉大寫
st.sidebar.info("提示：美股直接輸入 (如 AAPL)，台股請加 .TW (如 2330.TW)")

# --- 核心功能：使用快取減少請求次數 ---
@st.cache_data(ttl=600)  # 資料會記住 10 分鐘，這段時間內重複輸入同代號不會重複抓資料
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    df = stock.history(start=start_date, end=end_date)
    # 抓取新聞
    news = stock.news[:10]
    # 抓取貨幣資訊
    currency = stock.info.get('currency', 'USD')
    return df, news, currency

# --- 執行與顯示 ---
try:
    if ticker_input:
        df, news, currency = get_stock_data(ticker_input)

        if not df.empty:
            # 1. 顯示目前價格
            current_price = df['Close'].iloc[-1]
            st.metric(label=f"{ticker_input} 目前價格", value=f"{current_price:.2f} {currency}")

            # 2. Plotly 走勢圖
            st.subheader("🗓️ 最近一個月走勢圖")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='收盤價', line=dict(color='#1f77b4')))
            fig.update_layout(xaxis_title="日期", yaxis_title=f"價格 ({currency})", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            # 3. 顯示最新新聞
            st.subheader("📰 最新相關新聞")
            if news:
                for item in news:
                    col1, col2 = st.columns([1, 4])
                    with col2:
                        st.markdown(f"**[{item['title']}]({item['link']})**")
                        pub_time = datetime.fromtimestamp(item['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
                        st.caption(f"來源: {item['publisher']} | 發布時間: {pub_time}")
                    st.divider()
            else:
                st.write("暫無相關新聞。")
        else:
            st.error("找不到該股票數據，請確認代號是否正確（例如台股要加 .TW）。")

except Exception as e:
    # 針對 Rate Limit 顯示更友善的提示
    if "Too Many Requests" in str(e):
        st.warning("⚠️ 系統忙碌中 (Yahoo Finance 暫時限制連線)，請稍等 5-10 分鐘後重新整理頁面再試。")
    else:
        st.error(f"發生錯誤: {e}")
