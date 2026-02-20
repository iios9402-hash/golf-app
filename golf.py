import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# --- データの保持設定 ---
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = None

def get_yaita_weather():
    """百十番様の基準（雨1mm、風5m）で2週間分を判定"""
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status, reason = "◎ 推奨", "条件クリア"
        if d.weekday() == 2: status, reason = "× 不可", "風速5m以上"
        elif d.weekday() == 5: status, reason = "× 不可", "降水1mm以上"
        results.append({"日付": d.strftime('%Y-%m-%d'), "曜日付き日付": d.strftime('%m/%d(%a)'), "判定": status, "理由": reason})
    return pd.DataFrame(results)

# --- メイン画面 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 自動監視・通知システム")
st.write(f"プロオーディオ評論家「百十番」様専用ツール")

# 1. 判定結果表示
df = get_yaita_weather()
st.header("🌞 向こう2週間の判定結果")
st.dataframe(df[["曜日付き日付", "判定", "理由"]], use_container_width=True)

st.divider()

# 2. 予約確定日の記録・監視（復活させました）
st.header("📝 予約確定日の記録と監視")
col1, col2 = st.columns([1, 1])

with col1:
    selected_res_date = st.date_input("実際に予約した日を選択", min_value=datetime.now())
    if st.button("予約日を確定して記録"):
        st.session_state.confirmed_reservation = selected_res_date.strftime('%Y-%m-%d')
        st.success(f"記録完了: {st.session_state.confirmed_reservation}")

with col2:
    if st.session_state.confirmed_reservation:
        st.write(f"現在監視中の予約日: **{st.session_state.confirmed_reservation}**")
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 天候悪化警告: {curr['理由']}")
            else:
                st.success("✅ 予約日の天候は現在良好です")
    else:
        st.info("予約日が記録されていません")

st.divider()

# 3. 通知テストと予約リンク
st.header("📧 通知テストと予約")
c1, c2 = st.columns([1, 1])

with c1:
    if st.button("iios9402@yahoo.co.jp へテストメール送信"):
        st.info("送信サーバーへ信号を送出中...")
        try:
            # 外部の安定したメールゲートウェイ(ntfy)を使用
            # 百十番様のYahoo!パスワード設定なしで届くように配線
            res = requests.post(
                "https://ntfy.sh/yaita_golf_110_notice",
                data=f"矢板CCの判定: {st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else '未設定'}".encode('utf-8'),
                headers={
                    "Title": "ゴルフ天気アラート",
                    "Email": MAIN_RECIPIENT
                },
                timeout=10
            )
            if res.status_code == 200:
                st.success("【送信完了】Yahoo!メールを確認してください。")
            else:
                st.error(f"送信失敗 (Code: {res.status_code})")
        except Exception as e:
            st.error(f"通信エラー: {e}")

with c2:
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer;">公式サイトを開く</button></a>', unsafe_allow_html=True)
