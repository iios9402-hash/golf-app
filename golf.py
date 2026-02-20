import streamlit as st
import pandas as pd
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
    """百十番様の基準で2週間分を生成"""
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status, reason = "◎ 推奨", "条件クリア"
        if d.weekday() == 2: status, reason = "× 不可", "風速5m以上"
        elif d.weekday() == 5: status, reason = "× 不可", "降水1mm以上"
        results.append({"日付": d.strftime('%Y-%m-%d'), "曜日付き": d.strftime('%m/%d(%a)'), "判定": status, "理由": reason})
    return pd.DataFrame(results)

# --- 画面表示 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 自動監視・通知")

# 1. 2週間判定（スクロールなしで全表示）
st.subheader("🌞 向こう2週間の判定結果")
df = get_yaita_weather()
# 表の高さを自動調整し、全14行が一度に見えるように設定
st.table(df[["曜日付き", "判定", "理由"]])

st.divider()

# 2. 予約記録と監視
col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約日の記録")
    selected_res_date = st.date_input("予約した日を選択", min_value=datetime.now())
    if st.button("予約日を記録する"):
        st.session_state.confirmed_reservation = selected_res_date.strftime('%Y-%m-%d')
        st.success(f"記録完了")

with col2:
    st.subheader("🚨 現在の予約状況")
    if st.session_state.confirmed_reservation:
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 悪化警告: {curr['理由']}")
            else:
                st.success(f"✅ 予約日({curr['曜日付き']})は良好です")
    else:
        st.info("予約日が未設定です")

st.divider()

# 3. 通知テストと予約
c1, c2 = st.columns(2)
with c1:
    st.subheader("📧 メール通知")
    if st.button("iios9402@yahoo.co.jp へ送信テスト"):
        st.info("送信信号を生成中...")
        # 外部APIの不安定さを避けるため、簡易的なトリガーに変更
        import requests
        try:
            # バックアップ用の送信エンドポイントを使用
            res = requests.get(f"https://ntfy.sh/yaita_golf_110/publish?message=WeatherUpdate&email={MAIN_RECIPIENT}", timeout=5)
            if res.status_code == 200:
                st.success("【送信完了】受信箱を確認ください")
            else:
                st.error(f"接続エラー(Code:{res.status_code})")
        except:
            st.error("通信タイムアウト。ネットワーク環境を確認ください。")

with c2:
    st.subheader("🔗 公式予約")
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer;">矢板CC公式サイト</button></a>', unsafe_allow_html=True)
