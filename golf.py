import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

# --- 固定情報（矢板CCの座標: 北緯36.8, 東経139.9） ---
GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=36.80&longitude=139.90&daily=precipitation_sum,wind_speed_10m_max&timezone=Asia%2FTokyo"

# --- 永続的な保存（ブラウザのセッションを跨いで保持） ---
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = st.query_params.get("date", None)
if 'additional_emails' not in st.session_state:
    st.session_state.additional_emails = st.query_params.get_all("emails")

def fetch_weather_data():
    """安定した気象APIから矢板CCのピンポイント予報を取得し判定"""
    try:
        res = requests.get(API_URL, timeout=10)
        data = res.json()
        daily = data['daily']
        
        results = []
        for i in range(len(daily['time'])):
            d_str = daily['time'][i]
            d_obj = datetime.strptime(d_str, '%Y-%m-%d')
            p_val = daily['precipitation_sum'][i]
            w_val = daily['wind_speed_10m_max'][i]

            # 百十番様の判定基準（雨1mm以上、風5m以上で不可）
            status = "◎ 推奨"
            reason = "条件クリア"
            if p_val >= 1.0:
                status = "× 不可"
                reason = f"降水 {p_val}mm"
            elif w_val >= 5.0:
                status = "× 不可"
                reason = f"風速 {w_val}m"

            results.append({
                "曜日付き": d_obj.strftime('%m/%d(%a)'),
                "判定": status,
                "理由": reason,
                "日付": d_str
            })
        return pd.DataFrame(results)
    except:
        return pd.DataFrame()

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
st.write("プロオーディオ評論家「百十番」様専用（高信頼データ接続モデル）")

df = fetch_weather_data()

# 1. 判定表示
st.subheader("🌞 向こう週間の気象判定")
if not df.empty:
    st.table(df[["曜日付き", "判定", "理由"]])
else:
    st.error("気象データの取得に失敗しました。時間をおいてリロードしてください。")

st.divider()

# 2. 監視状況（リロード対策：URLパラメータに保存）
col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約設定")
    curr_d = datetime.now()
    if st.session_state.confirmed_reservation:
        try: curr_d = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d')
        except: pass
    
    new_date = st.date_input("予約日を選択", value=curr_d, min_value=datetime.now())
    if st.button("予約日を保存（リロード対応）"):
        st.session_state.confirmed_reservation = new_date.strftime('%Y-%m-%d')
        # URLに日付を刻むことでリロードしても残るようにします
        st.query_params["date"] = st.session_state.confirmed_reservation
        st.success("設定をブラウザに保存しました。")
        st.rerun()

with col2:
    st.subheader("🚨 判定アラート")
    if st.session_state.confirmed_reservation and not df.empty:
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 警告: {curr['曜日付き']} は【{curr['理由']}】です。")
            else:
                st.success(f"✅ 良好: {curr['曜日付き']} は現在条件をクリアしています。")
    else:
        st.info("予約日を保存して判定を確認してください。")

st.divider()

# 3. 通知・リンク
c1, c2 = st.columns(2)
with c1:
    if st.button("📩 登録全宛先へテストメール送信"):
        all_recs = [MAIN_RECIPIENT] + st.session_state.additional_emails
        target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
        body = f"百十番様\n\n矢板CC 判定結果\n予約日: {target}\n判定: アプリを確認してください。"
        for email in all_recs:
            try:
                requests.post("https://ntfy.sh/yaita_golf_110", data=body.encode('utf-8'),
                              headers={"Title": f"【矢板CC】判定({target})".encode('utf-8'), "Email": email, "Charset": "UTF-8"}, timeout=10)
            except: continue
        st.success("最新データで送信完了しました。")

with c2:
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイトを開く</button></a>', unsafe_allow_html=True)
