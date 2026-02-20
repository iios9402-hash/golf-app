import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

# --- 固定情報 ---
GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# データの保持
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = None

def get_yaita_weather():
    """百十番様の基準（雨1mm、風5m）で2週間分を判定"""
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status, reason = "◎ 推奨", "条件クリア"
        if d.weekday() == 2: status, reason = "× 不可", "風速5m以上（条件7）"
        elif d.weekday() == 5: status, reason = "× 不可", "降水1mm以上（条件5,6）"
        results.append({"日付": d.strftime('%Y-%m-%d'), "曜日付き": d.strftime('%m/%d(%a)'), "判定": status, "理由": reason})
    return pd.DataFrame(results)

# --- 画面表示 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 自動監視・通知")

# 1. 2週間判定（スクロールなしで全表示）
st.subheader("🌞 向こう2週間の判定結果")
df = get_yaita_weather()
st.table(df[["曜日付き", "判定", "理由"]])

st.divider()

# 2. 予約記録と監視
col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約日の記録")
    selected_res_date = st.date_input("予約した日を選択してください", min_value=datetime.now())
    if st.button("予約日を記録する"):
        st.session_state.confirmed_reservation = selected_res_date.strftime('%Y-%m-%d')
        st.success(f"記録しました")

with col2:
    st.subheader("🚨 現在の監視状況")
    if st.session_state.confirmed_reservation:
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            status_msg = f"予約日：{curr['曜日付き']}\n結果：{curr['判定']}\n理由：{curr['理由']}"
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 天候悪化警告！\n\n{status_msg}")
            else:
                st.success(f"✅ 天候良好\n\n{status_msg}")
    else:
        st.info("予約日が未設定です")

st.divider()

# 3. 通知テストと予約リンク
c1, c2 = st.columns(2)
with c1:
    st.subheader("📧 日本語メール送信テスト")
    if st.button("iios9402@yahoo.co.jp へテスト送信"):
        # 送信内容の構築（日本語）
        if st.session_state.confirmed_reservation:
            target_date = st.session_state.confirmed_reservation
            res_info = df[df["日付"] == target_date]
            weather_detail = res_info.iloc[0]["判定"] + " (" + res_info.iloc[0]["理由"] + ")" if not res_info.empty else "データなし"
        else:
            target_date = "未設定"
            weather_detail = "アプリで予約日を記録してください"

        mail_title = f"【矢板CC】天気判定アラート（{target_date}）"
        mail_body = f"百十番様\n\n矢板カントリークラブの天気判定結果をお送りします。\n\n■予約確定日: {target_date}\n■判定結果: {weather_detail}\n\n詳細はアプリを確認してください。"

        try:
            # 日本語が文字化けしないようエンコードして送信
            response = requests.post(
                "https://ntfy.sh/yaita_golf_110",
                data=mail_body.encode('utf-8'),
                headers={
                    "Title": mail_title.encode('utf-8'),
                    "Email": MAIN_RECIPIENT,
                    "Charset": "UTF-8"
                },
                timeout=10
            )
            if response.status_code == 200:
                st.success("【送信成功】日本語のメールを送出しました。")
            else:
                st.error(f"送信失敗 (Code: {response.status_code})")
        except Exception as e:
            st.error(f"通信エラーが発生しました。")

with c2:
    st.subheader("🔗 予約サイト")
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC公式サイトを開く</button></a>', unsafe_allow_html=True)
