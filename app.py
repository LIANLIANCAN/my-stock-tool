import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 設定網頁標題
st.set_page_config(page_title="簡易股市分析工具", layout="wide")

st.title("📈 簡易股市分析小工具")
st.write("輸入股票代號，快速查看現價、走勢圖與最新新聞。")

# --- 側邊欄：輸入區 ---
st.sidebar.header("查詢條件")
ticker_input = st.sidebar.text_input("請輸入股票代號", value="AAPL")
st.sidebar.info("提示：美股直接輸入 (如 AAPL)，台股請加 .TW (如 2330.TW)")

# --- 抓取數據 ---
try:
    stock = yf.Ticker(ticker_input)
    
    # 獲取股價歷史 (最近一個月)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    df = stock.history(start=start_date, end=end_date)

    if not df.empty:
        # 1. 顯示目前價格
        current_price = df['Close'].iloc[-1]
        currency = stock.info.get('currency', 'USD')
        st.metric(label=f"{ticker_input} 目前價格", value=f"{current_price:.2f} {currency}")

        # 2. Plotly 走勢圖
        st.subheader("🗓️ 最近一個月走勢圖")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines+markers', name='收盤價'))
        fig.update_layout(xaxis_title="日期", yaxis_title="價格", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # 3. 顯示最新新聞 (前10則)
        st.subheader("📰 最新相關新聞")
        news = stock.news[:10]  # 取前 10 則
        if news:
            for item in news:
                col1, col2 = st.columns([1, 4])
                with col2:
                    st.markdown(f"**[{item['title']}]({item['link']})**")
                    # 轉換時間戳記
                    pub_time = datetime.fromtimestamp(item['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
                    st.caption(f"來源: {item['publisher']} | 發布時間: {pub_time}")
                st.divider()
        else:
            st.write("暫無相關新聞。")
    else:
        st.error("找不到該股票數據，請檢查代號是否正確。")

except Exception as e:
    st.error(f"發生錯誤: {e}")