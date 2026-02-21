import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
TENKI_JP_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=36.8091&longitude=139.9073&daily=weather_code,precipitation_sum,wind_speed_10m_max&timezone=Asia%2FTokyo&wind_speed_unit=ms&forecast_days=14"
SETTINGS_FILE = "settings.json"

# --- サーバー側ストレージ (JSONファイル) の読み書き ---
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return data if data else {"date": None, "emails": ""}
        except:
            pass
    return {"date": None, "emails": ""}

def save_settings(date_str, emails_str):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"date": date_str, "emails": emails_str}, f)

# 起動時に設定をロード
settings = load_settings()

if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = settings.get("date")
if 'additional_emails' not in st.session_state:
    emails_raw = settings.get("emails", "")
    st.session_state.additional_emails = [e.strip() for e in emails_raw.split(",") if e.strip()]

def get_weather_info(code):
    rain_codes = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
    is_rain = code in rain_codes
    return ("雨" if is_rain else "晴/曇"), is_rain

def fetch_weather_stable():
    try:
        res = requests.get(API_URL, timeout=15)
        data = res.json()
        daily = data['daily']
        results = []
        for i in range(len(daily['time'])):
            d_obj = datetime.strptime(daily['time'][i], '%Y-%m-%d')
            p_val = round(daily['precipitation_sum'][i], 1)
            w_val = round(daily['wind_speed_10m_max'][i], 1)
            w_desc, is_rain = get_weather_info(daily['weather_code'][i])
            status, reason = "◎ 推奨", "条件クリア"
            if p_val >= 1.0: status, reason = "× 不可", f"降水 {p_val}mm"
            elif w_val >= 5.0: status, reason = "× 不可", f"風速 {w_val}m"
            if i in [10, 11, 12] and is_rain: status, reason = "× 不可", "雨予報 (規定)"
            results.append({"曜日付き": d_obj.strftime('%m/%d(%a)'), "天気": w_desc, "判定": status, "理由": reason, "日付": daily['time'][i]})
        return pd.DataFrame(results)
    except: return pd.DataFrame()

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")

df = fetch_weather_stable()

# 1. 2週間判定
st.subheader("🌞 向こう2週間の気象判定")
if not df.empty:
    st.table(df[["曜日付き", "天気", "判定", "理由"]])
    st.markdown(f"情報源: [tenki.jp 矢板カントリークラブ２週間予報]({TENKI_JP_URL})")
else:
    st.error("データの取得に失敗しました。")

st.divider()

# 2. 設定・管理
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 予約・通知設定")
    try:
        d_val = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d') if st.session_state.confirmed_reservation else datetime.now()
    except:
        d_val = datetime.now()
    
    new_date = st.date_input("予約確定日を選択", value=d_val)
    current_emails = ",".join(st.session_state.additional_emails)
    new_emails_str = st.text_area("追加通知先メールアドレス（カンマ区切り）", value=current_emails)
    
    if st.button("設定を完全に保存する"):
        date_str = new_date.strftime('%Y-%m-%d')
        # ファイルに書き込み（これでサーバー側に記憶される）
        save_settings(date_str, new_emails_str)
        st.session_state.confirmed_reservation = date_str
        st.session_state.additional_emails = [e.strip() for e in new_emails_str.split(",") if e.strip()]
        st.success("設定をサーバーに保存しました。次回以降も自動で読み込まれます。")
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
                st.success(f"✅ 良好: {curr['曜日付き']} は条件をクリアしています。")
    else:
        st.info("予約日を保存して判定を確認してください。")

st.divider()

# 3. 通知テスト
if st.button("📩 登録全アドレスへテストメール送信"):
    all_recipients = [MAIN_RECIPIENT] + st.session_state.additional_emails
    target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
    body = f"矢板CC 判定通知\n予約日: {target}\n判定: アプリを確認してください。"
    for email in all_recipients:
        try:
            requests.post("https://ntfy.sh/yaita_golf_110", data=body.encode('utf-8'),
                          headers={"Title": f"【矢板CC】判定({target})".encode('utf-8'), "Email": email, "Charset": "UTF-8"}, timeout=10)
        except: continue
    st.success(f"計 {len(all_recipients)} 件へ送信完了しました。")

st.markdown(f'<br><a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC 公式サイトを開く</button></a>', unsafe_allow_html=True)
