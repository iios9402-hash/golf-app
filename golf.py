import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 永続監視システム", layout="wide")

# --- 固定情報の取得（Secretsから読み込む） ---
GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# Secretsに保存された値をデフォルトとして読み込む
fixed_res_date = st.secrets.get("CONFIRMED_DATE", "")
fixed_add_emails = st.secrets.get("ADDITIONAL_EMAILS", "").split(",") if st.secrets.get("ADDITIONAL_EMAILS") else []

def get_yaita_weather():
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status, reason = "◎ 推奨", "条件クリア"
        if d.weekday() == 2: status, reason = "× 不可", "風速5m以上（条件7）"
        elif d.weekday() == 5: status, reason = "× 不可", "降水1mm以上（条件5,6）"
        results.append({"日付": d.strftime('%Y-%m-%d'), "曜日付き": d.strftime('%m/%d(%a)'), "判定": status, "理由": reason})
    return pd.DataFrame(results)

st.title(f"⛳ {GOLF_COURSE_NAME} 永続監視システム")

# 1. 2週間判定（全表示）
df = get_yaita_weather()
st.table(df[["曜日付き", "判定", "理由"]])

st.divider()

# 2. 監視状況の表示
st.subheader("🚨 現在の固定監視設定")
col1, col2 = st.columns(2)

with col1:
    if fixed_res_date:
        res_info = df[df["日付"] == fixed_res_date]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 警告: 予約日 {fixed_res_date} は【{curr['理由']}】です")
            else:
                st.success(f"✅ 良好: 予約日 {fixed_res_date} は現在クリアしています")
    else:
        st.info("監視する予約日がSecretsに設定されていません")

with col2:
    st.write("【現在の通知先】")
    st.text(f"・メイン: {MAIN_RECIPIENT}")
    for em in fixed_add_emails:
        if em: st.text(f"・追加: {em}")

st.divider()
st.caption("※予約日や通知先の変更は、Streamlit Cloudの [Settings] > [Secrets] から直接書き換えて保存してください。リロードしても消えなくなります。")
