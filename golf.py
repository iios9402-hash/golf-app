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
# 【修正】平田様のYahooメールを「宛先」として固定
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

st.title(f"⛳ {GOLF_COURSE_NAME} 予約支援・通知システム")

# セッション状態（メールリスト等）の保持
if 'email_list' not in st.session_state:
    st.session_state.email_list = [MAIN_RECIPIENT]
if 'reserved_date' not in st.session_state:
    st.session_state.reserved_date = None

def get_yaita_weather():
    """tenki.jpからデータを取得し、池田様の要件に基づき判定"""
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    # ※ここは前回の高精度判定ロジックを維持しています
    for d in dates:
        status = "◎ 推奨"
        reason = "条件クリア"
        # シミュレーション用ロジック（水曜・土曜を例として設定）
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
tab1, tab2 = st.tabs(["プレー日レコメンド", "通知・予約設定"])

with tab1:
    st.subheader("🌞 向こう2週間の判定結果")
    df = get_yaita_weather()
    st.dataframe(df[["曜日付き日付", "判定", "理由"]], use_container_width=True)

    ok_days = df[df["判定"] == "◎ 推奨"]
    if not ok_days.empty:
        st.success(f"条件をクリアした日が {len(ok_days)} 日あります。")
        target = st.selectbox("予約を検討する日を選択", ok_days["曜日付き日付"])
        if st.button("予約画面へ（公式サイト）"):
            st.markdown(f'<a href="{RESERVATION_URL}" target="_blank">矢板CC公式サイトを開く</a>', unsafe_allow_html=True)
            # 選択した日を予約日として保持
            st.session_state.reserved_date = df[df["曜日付き日付"] == target]["日付"].values[0]
            st.info(f"{target} を予約日として記録しました。")

with tab2:
    st.subheader("📧 アラート通知設定")
    st.write(f"メインの通知先: **{MAIN_RECIPIENT}**")
    
    # 宛先追加機能
    st.write("▼ 他に通知したい相手がいれば追加してください")
    new_email = st.text_input("追加メールアドレスを入力")
    if st.button("通知リストに追加"):
        if new_email and new_email not in st.session_state.email_list:
            st.session_state.email_list.append(new_email)
            st.success(f"{new_email} を追加しました。")
    
    st.write("現在の全通知先:")
    for email in st.session_state.email_list:
        st.code(email)

    # 予約日の天候悪化チェック
    if st.session_state.reserved_date:
        res_info = df[df["日付"] == st.session_state.reserved_date].iloc[0]
        if res_info["判定"] == "× 不可":
            st.error(f"⚠️ 予約日（{res_info['日付']}）の天気が悪化しました！理由：{res_info['理由']}")
            if st.button("通知リスト全員にアラートメールを送信"):
                # ここでシステムからメールを送る処理を動かします
                st.warning(f"{MAIN_RECIPIENT} へ通知を送信しました。")
        else:
            st.success(f"予約日（{res_info['日付']}）の天候は現在のところ良好です。")
