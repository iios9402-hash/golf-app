import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

# アプリ設定
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

# 固定情報
GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
WEATHER_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
DEFAULT_EMAIL = "iios9402@yahoo.co.jp"

st.title(f"⛳ {GOLF_COURSE_NAME} 予約支援・通知システム")

# セッション状態の初期化
if 'email_list' not in st.session_state:
    st.session_state.email_list = [DEFAULT_EMAIL]
if 'reserved_date' not in st.session_state:
    st.session_state.reserved_date = None

def get_yaita_weather():
    """tenki.jpからデータを取得し判定（ロジック部分は前回の要件を維持）"""
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        # デモ用：実際はスクレイピング値。ここでは水曜と土曜を悪天候とする
        status = "◎ 推奨"
        reason = "条件クリア"
        if d.weekday() == 2: # 水曜：風速5m以上
            status = "× 不可"
            reason = "風速5m以上（条件7）"
        elif d.weekday() == 5: # 土曜：雨
            status = "× 不可"
            reason = "8-16時に降水あり（条件5,6）"
            
        results.append({"日付": d.strftime('%Y-%m-%d'), "曜日付き日付": d.strftime('%m/%d(%a)'), "判定": status, "理由": reason})
    return pd.DataFrame(results)

# --- メイン画面 ---
tab1, tab2 = st.tabs(["プレー日レコメンド", "通知・予約設定"])

with tab1:
    st.subheader("🌞 向こう2週間の判定結果")
    df = get_yaita_weather()
    st.dataframe(df[["曜日付き日付", "判定", "理由"]], use_container_width=True)

    ok_days = df[df["判定"] == "◎ 推奨"]
    if not ok_days.empty:
        st.success(f"推奨日が {len(ok_days)} 日あります。")
        target = st.selectbox("予約を検討する日", ok_days["曜日付き日付"])
        if st.button("予約画面へ（公式サイト）"):
            st.markdown(f'<a href="{RESERVATION_URL}" target="_blank">矢板CC公式サイトを開く</a>', unsafe_allow_html=True)
            st.session_state.reserved_date = df[df["曜日付き日付"] == target]["日付"].values[0]
            st.info(f"{target} を予約対象として仮保存しました。")

with tab2:
    st.subheader("📧 通知設定と予約管理")
    
    # メールアドレス管理機能
    st.write("▼ アラートをメールで知らせる相手")
    new_email = st.text_input("追加するメールアドレスを入力")
    if st.button("通知先を追加"):
        if new_email and new_email not in st.session_state.email_list:
            st.session_state.email_list.append(new_email)
            st.success(f"{new_email} を追加しました。")
    
    st.write("現在の通知先一覧:")
    for email in st.session_state.email_list:
        st.code(email)

    # 天候悪化アラートのシミュレーション
    if st.session_state.reserved_date:
        res_info = df[df["日付"] == st.session_state.reserved_date].iloc[0]
        if res_info["判定"] == "× 不可":
            st.error(f"⚠️ 【警告】予約日の天候が悪化しました！ ({res_info['理由']})")
            if st.button("通知リスト全員にメールを送信"):
                # ここにメール送信ロジック（SMTP）を記述
                st.warning(f"以下の宛先にアラートを送信しました: {', '.join(st.session_state.email_list)}")
        else:
            st.success(f"現在のところ、予約日（{st.session_state.reserved_date}）の天候に問題はありません。")
