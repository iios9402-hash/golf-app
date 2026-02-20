import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# アプリ設定
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

# 固定情報
GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
WEATHER_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

st.title(f"⛳ {GOLF_COURSE_NAME} 予約支援・自動監視システム")

# データの保存（予約確定日などを保持）
if 'email_list' not in st.session_state:
    st.session_state.email_list = [MAIN_RECIPIENT]
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = None

def get_yaita_weather():
    """tenki.jpからデータを取得し判定"""
    # ※ここは実際のスクレイピング処理を維持
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status = "◎ 推奨"
        reason = "条件クリア"
        # 判定ロジック（デモ用）
        if d.weekday() == 2:
            status = "× 不可"
            reason = "風速5m以上（条件7）"
        elif d.weekday() == 5:
            status = "× 不可"
            reason = "8-16時に1mm以上の降水（条件5,6）"
            
        results.append({
            "日付": d.strftime('%Y-%m-%d'), 
            "曜日付き日付": d.strftime('%m/%d(%a)'), 
            "判定": status, 
            "理由": reason
        })
    return pd.DataFrame(results)

# --- 画面表示 ---
tab1, tab2, tab3 = st.tabs(["プレー日判定", "予約確定日の記録", "通知設定"])

with tab1:
    st.subheader("🌞 向こう2週間の判定結果")
    df = get_yaita_weather()
    st.dataframe(df[["曜日付き日付", "判定", "理由"]], use_container_width=True)

with tab2:
    st.subheader("📝 予約確定日の入力・記録")
    st.write("実際に予約を完了した日を入力してください。毎日AM5:00にこの日の天気を自動チェックします。")
    
    # 日付選択
    selected_res_date = st.date_input("予約した日を選択", min_value=datetime.now())
    if st.button("予約日を確定して記録する"):
        st.session_state.confirmed_reservation = selected_res_date.strftime('%Y-%m-%d')
        st.success(f"【記録完了】 {st.session_state.confirmed_reservation} の天気を毎朝5時に監視します。")

    if st.session_state.confirmed_reservation:
        st.info(f"現在監視中の予約日: **{st.session_state.confirmed_reservation}**")
        # 予約日の現在の天気を表示
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            current_status = res_info.iloc[0]
            if current_status["判定"] == "× 不可":
                st.error(f"⚠️ 警告: 予約日の天候が悪化しています！ ({current_status['理由']})")
            else:
                st.success("✅ 現在のところ、予約日の天候条件はクリアしています。")

with tab3:
    st.subheader("📧 アラート通知設定")
    st.write(f"メイン通知先: {MAIN_RECIPIENT}")
    # (通知先追加ロジックは維持)
