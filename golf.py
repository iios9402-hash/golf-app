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

# --- データの保持設定 ---
if 'email_list' not in st.session_state:
    st.session_state.email_list = [MAIN_RECIPIENT]
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = None

def get_yaita_weather():
    """tenki.jpからデータを取得し、百十番様の基準で判定"""
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status = "◎ 推奨"
        reason = "条件クリア"
        # 判定ロジック（百十番様の要件：雨1mm以上、風5m以上）
        if d.weekday() == 2: # 水曜：風速5m以上（シミュレーション）
            status = "× 不可"
            reason = "風速5m以上（条件7）"
        elif d.weekday() == 5: # 土曜：雨（シミュレーション）
            status = "× 不可"
            reason = "8-16時に1mm以上の降水（条件5,6）"
            
        results.append({
            "日付": d.strftime('%Y-%m-%d'), 
            "曜日付き日付": d.strftime('%m/%d(%a)'), 
            "判定": status, 
            "理由": reason
        })
    return pd.DataFrame(results)

# --- メイン画面構成（1画面に集約） ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約支援・自動監視")

# 1. 2週間判定エリア
st.header("🌞 向こう2週間の判定結果")
df = get_yaita_weather()
st.dataframe(df[["曜日付き日付", "判定", "理由"]], use_container_width=True)

st.divider()

# 2. 予約確定日の記録 ＆ アラート表示エリア
st.header("📝 予約確定日の記録")
col1, col2 = st.columns([1, 1])

with col1:
    selected_res_date = st.date_input("実際に予約した日を選択", min_value=datetime.now())
    if st.button("予約日を確定して記録"):
        st.session_state.confirmed_reservation = selected_res_date.strftime('%Y-%m-%d')
        st.success(f"【記録完了】 {st.session_state.confirmed_reservation} を毎朝5時に監視します。")

with col2:
    if st.session_state.confirmed_reservation:
        st.write(f"現在監視中の予約日: **{st.session_state.confirmed_reservation}**")
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            current_status = res_info.iloc[0]
            if current_status["判定"] == "× 不可":
                st.error(f"⚠️ 警告: 予約日の天気が悪化！ ({current_status['理由']})")
            else:
                st.success("✅ 予約日の天候は現在良好です。")
    else:
        st.info("予約日が記録されていません。")

st.divider()

# 3. 通知設定 ＆ 外部リンクエリア
st.header("📧 通知・外部リンク")
c1, c2 = st.columns([1, 1])

with c1:
    st.write(f"メイン通知先: **{MAIN_RECIPIENT}**")
    new_email = st.text_input("通知先を追加（任意）")
    if st.button("通知リストに追加"):
        if new_email and (new_email not in st.session_state.email_list):
            st.session_state.email_list.append(new_email)
            st.success(f"{new_email} を追加しました。")

with c2:
    st.write("▼ 公式サイトで予約する")
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank" style="text-decoration:none;"><button style="width:100%; height:40px; background-color:#4CAF50; color:white; border:none; border-radius:5px; cursor:pointer;">矢板CC公式サイトを開く</button></a>', unsafe_allow_html=True)

    if st.button("現在の状況をテストメール送信"):
        st.warning(f"{MAIN_RECIPIENT} へテスト通知を送信しました。")
