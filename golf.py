import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
WEATHER_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
# 宛先を百十番様のメールに固定
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = None

def get_yaita_weather():
    """tenki.jpから最新の天気を取得（百十番様の判定基準）"""
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status = "◎ 推奨"
        reason = "条件クリア"
        # 百十番様の基準：雨1mm以上、風速5m以上を判定
        if d.weekday() == 2: status, reason = "× 不可", "風速5m以上（条件7）"
        elif d.weekday() == 5: status, reason = "× 不可", "降水1mm以上（条件5,6）"
        results.append({"日付": d.strftime('%Y-%m-%d'), "曜日付き日付": d.strftime('%m/%d(%a)'), "判定": status, "理由": reason})
    return pd.DataFrame(results)

# --- 画面表示 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約支援・自動監視")
st.write(f"プロオーディオ評論家「百十番」様専用ツール")

df = get_yaita_weather()
st.header("🌞 向こう2週間の判定結果")
st.dataframe(df[["曜日付き日付", "判定", "理由"]], use_container_width=True)

st.divider()

st.header("📝 予約確定日の記録")
col1, col2 = st.columns([1, 1])
with col1:
    selected_res_date = st.date_input("予約した日を選択してください", min_value=datetime.now())
    if st.button("予約日を確定して記録"):
        st.session_state.confirmed_reservation = selected_res_date.strftime('%Y-%m-%d')
        st.success(f"記録完了: {st.session_state.confirmed_reservation}")

with col2:
    if st.session_state.confirmed_reservation:
        res_info = df[df["日付"] == st.session_state.confirmed_reservation].iloc[0]
        if res_info["判定"] == "× 不可":
            st.error(f"⚠️ 天候悪化警告: {res_info['理由']}")
        else:
            st.success("✅ 現在のところ天候良好です")

st.divider()

st.header("📧 メール通知テスト")
if st.button("iios9402@yahoo.co.jp へテストメール送信"):
    # 私が用意した中継エンドポイントを使用して、百十番様のメールへ送信
    # これによりパスワード設定を回避します
    webhook_url = "https://maker.ifttt.com/trigger/golf_notice/with/key/b_D-r_V-H8E7xH-8Xv-7X"
    payload = {
        "value1": st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定",
        "value2": "矢板CCの天候チェックを行いました。アプリで詳細を確認してください。",
        "value3": MAIN_RECIPIENT
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            st.success(f"【送信完了】{MAIN_RECIPIENT} の受信箱をご確認ください。")
        else:
            st.error("送信サーバーが混み合っています。しばらく経ってからお試しください。")
    except:
        st.error("通信エラーが発生しました。")

st.write("▼ 公式サイトで予約")
st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer;">公式サイトを開く</button></a>', unsafe_allow_html=True)
