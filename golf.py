import streamlit as st
import pandas as pd
import requests
import json
import base64
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
TENKI_JP_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=36.8091&longitude=139.9073&daily=weather_code,precipitation_sum,wind_speed_10m_max&timezone=Asia%2FTokyo&wind_speed_unit=ms&forecast_days=14"

# --- GitHub永続化設定（Secretsから取得） ---
# これにより再起動してもGitHub上のsettings.jsonを正しく読み書きします
GITHUB_TOKEN = st.secrets.get("GH_TOKEN") # GitHubのPersonal Access Token
REPO_NAME = st.secrets.get("GH_REPO")   # 例: "user/reponame"
FILE_PATH = "settings.json"

def load_settings_from_github():
    """GitHub上のsettings.jsonを直接読み込む"""
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            data = json.loads(content)
            return data, res.json()['sha']
    except:
        pass
    return {"date": None, "emails": ""}, None

def save_settings_to_github(date_str, emails_str, current_sha):
    """GitHub上のsettings.jsonを直接上書き保存する"""
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {
        "message": "Update settings from App",
        "content": base64.b64encode(json.dumps({"date": date_str, "emails": emails_str}).encode('utf-8')).decode('utf-8'),
        "sha": current_sha
    }
    res = requests.put(url, headers=headers, json=data)
    return res.status_code == 200

# データのロード
settings_data, file_sha = load_settings_from_github()

if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = settings_data.get("date")
if 'additional_emails' not in st.session_state:
    emails_raw = settings_data.get("emails", "")
    st.session_state.additional_emails = [e.strip() for e in emails_raw.split(",") if e]

def get_weather_info(code):
    rain_codes = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
    is_rain = code in rain_codes
    return ("雨" if is_rain else "晴/曇"), is_rain

def fetch_weather():
    try:
        res = requests.get(API_URL, timeout=15)
        daily = res.json()['daily']
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
df = fetch_weather()

# 1. 2週間判定
st.subheader("🌞 向こう2週間の気象判定")
if not df.empty:
    st.table(df[["曜日付き", "天気", "判定", "理由"]])
    st.markdown(f"情報源: [tenki.jp 矢板カントリークラブ２週間予報]({TENKI_JP_URL})")

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
    new_emails_str = st.text_area("追加通知先メールアドレス（カンマ区切り）", value=",".join(st.session_state.additional_emails))
    
    if st.button("設定を完全に保存する"):
        date_str = new_date.strftime('%Y-%m-%d')
        success = save_settings_to_github(date_str, new_emails_str, file_sha)
        if success:
            st.session_state.confirmed_reservation = date_str
            st.session_state.additional_emails = [e.strip() for e in new_emails_str.split(",") if e]
            st.success("GitHub上のマスターデータを更新しました。再起動後も保持されます。")
            st.rerun()
        else:
            st.error("GitHub連携エラー。Secretsの設定を確認してください。")

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

st.divider()

# 3. 通知テスト
if st.button("📩 登録全アドレスへテストメール送信"):
    all_recipients = [MAIN_RECIPIENT] + st.session_state.additional_emails
    target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
    body = f"矢板CC 判定通知\n予約日: {target}\n判定: アプリを確認してください。"
    for email in all_recipients:
        requests.post("https://ntfy.sh/yaita_golf_110", data=body.encode('utf-8'),
                      headers={"Title": f"【矢板CC】判定({target})".encode('utf-8'), "Email": email, "Charset": "UTF-8"}, timeout=10)
    st.success("テスト送信完了。")

st.markdown(f'<br><a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC 公式サイトを開く</button></a>', unsafe_allow_html=True)
