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

# --- データの保持設定（セッション状態） ---
if 'additional_emails' not in st.session_state:
    st.session_state.additional_emails = []
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = None

def get_yaita_weather():
    """百十番様の基準（雨1mm、風5m）で2週間分を生成"""
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status, reason = "◎ 推奨", "条件クリア"
        # 判定シミュレーション（水曜・土曜）
        if d.weekday() == 2: status, reason = "× 不可", "風速5m以上（条件7）"
        elif d.weekday() == 5: status, reason = "× 不可", "降水1mm以上（条件5,6）"
        results.append({
            "日付": d.strftime('%Y-%m-%d'), 
            "曜日付き": d.strftime('%m/%d(%a)'), 
            "判定": status, 
            "理由": reason
        })
    return pd.DataFrame(results)

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 自動監視・一括通知")
st.write(f"プロオーディオ評論家「百十番」様専用システム")

# 1. 2週間判定（スクロールなし全表示）
st.subheader("🌞 向こう2週間の判定結果")
df = get_yaita_weather()
st.table(df[["曜日付き", "判定", "理由"]])

st.divider()

# 2. 予約記録 ＆ 通知先設定
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 予約日の記録")
    selected_res_date = st.date_input("予約した日を選択", min_value=datetime.now())
    if st.button("予約日を確定保存"):
        st.session_state.confirmed_reservation = selected_res_date.strftime('%Y-%m-%d')
        st.success(f"記録完了: {st.session_state.confirmed_reservation}")

    st.subheader("📧 通知先の追加")
    new_email = st.text_input("追加するメールアドレスを入力")
    if st.button("アドレスを追加"):
        if new_email and new_email not in st.session_state.additional_emails:
            st.session_state.additional_emails.append(new_email)
            st.success(f"追加しました: {new_email}")
    
    if st.session_state.additional_emails:
        st.write("【追加済みリスト】")
        for em in st.session_state.additional_emails:
            st.text(f"・ {em}")
        if st.button("リストをリセット"):
            st.session_state.additional_emails = []
            st.rerun()

with col2:
    st.subheader("🚨 現在の予約監視状況")
    if st.session_state.confirmed_reservation:
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 警告: {curr['曜日付き']} は【{curr['理由']}】のため推奨しません。")
            else:
                st.success(f"✅ 良好: {curr['曜日付き']} の天候条件はクリアしています。")
    else:
        st.info("予約日が記録されていません")

st.divider()

# 3. 通知テスト ＆ 予約リンク
c1, c2 = st.columns(2)

with c1:
    st.subheader("📩 テストメールの一括送信")
    if st.button("全宛
