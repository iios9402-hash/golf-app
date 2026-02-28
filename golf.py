import streamlit as st
import pandas as pd
import requests
import json
import base64
from datetime import datetime

# --- 1. 基本コンセプト & 6. インターフェース仕様 ---
st.set_page_config(page_title="矢板CC 監視システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
TENKI_JP_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# 2. 情報ソース（APIへのリクエストにブラウザのふりをさせるヘッダーを追加）
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=36.8091&longitude=139.9073&daily=weather_code,precipitation_sum,wind_speed_10m_max&timezone=Asia%2FTokyo&wind_speed_unit=ms&forecast_days=14"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

# 4. 永続化設定
GITHUB_TOKEN = str(st.secrets.get("GH_TOKEN", "")).strip()
REPO_NAME = str(st.secrets.get("GH_REPO", "")).strip()
FILE_PATH = "settings.json"

@st.cache_data(ttl=300) # 5分間キャッシュして高速化
def fetch_weather():
    """要件 7-2. Weather Engine: 通信エラーを即座に切り捨てる"""
    rain_codes = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
    try:
        # タイムアウトを3秒に設定。これで「重い」状態を解消します。
        res = requests.get(API_URL, headers=HEADERS, timeout=3)
        res.raise_for_status()
        daily = res.json()['daily']
        results = []
        for i in range(len(daily['time'])):
            d_obj = datetime.strptime(daily['time'][i], '%Y-%m-%d')
            p_val = round(daily['precipitation_sum'][i], 1)
            w_val = round(daily['wind_speed_10m_max'][i], 1)
            is_rain = daily['weather_code'][i] in rain_codes
            w_desc = "雨" if is_rain else "晴/曇"
            
            status, reason = "◎ 推奨", "条件クリア"
            if p_val >= 1.0: status, reason = "× 不可", f"降水 {p_val}mm"
            elif w_val >= 5.0: status, reason = "× 不可", f"風速 {w_val}m"
            elif i in [10, 11, 12] and is_rain: status, reason = "× 不可", "雨予報 (警戒)"
            
            results.append({
                "曜日付き日付": d_obj.strftime('%m/%d(%a)'),
                "天気": w_desc, "判定": status, "理由": reason, "日付キー": daily['time'][i]
            })
        return pd.DataFrame(results)
    except:
        return None

def load_settings():
    default_vals = {"date": None, "emails": ""}
    if not GITHUB_TOKEN or not REPO_NAME: return default_vals, None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return json.loads(content), res.json()['sha']
    except: pass
    return default_vals, None

# データロード
settings_data, file_sha = load_settings()
if 'confirmed_reservation' not in st.session_state: st.session_state.confirmed_reservation = settings_data.get("date")
if 'additional_emails' not in st.session_state:
    emails_raw = settings_data.get("emails", "")
    st.session_state.additional_emails = [e.strip() for e in emails_raw.split(",") if e]

# --- UI表示 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")

df = fetch_weather()

st.subheader("🌞 向こう2週間の気象判定")
if df is not None:
    # 表示項目: 「曜日付き日付」「天気」「判定」「理由」
    st.table(df[["曜日付き日付", "天気", "判定", "理由"]])
    st.markdown(f"情報源: [tenki.jp 矢板カントリークラブ2週間予報]({TENKI_JP_URL})")
else:
    st.error("気象データの取得に失敗しました。APIとの通信が遮断されています。")
    st.markdown(f"直接確認: [tenki.jp 矢板カントリークラブ2週間予報]({TENKI_JP_URL})")
    if st.button("再試行"):
        st.cache_data.clear()
        st.rerun()

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約・通知設定")
    c_date = datetime.now()
    if st.session_state.confirmed_reservation:
        try: c_date = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d')
        except: pass
    new_date = st.date_input("予約確定日を選択", value=c_date)
    emails_text = ",".join(st.session_state.additional_emails)
    new_emails_str = st.text_area("追加通知先（カンマ区切り）", value=emails_text)
    if st.button("設定を完全に保存する"):
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        content_json = json.dumps({"date": new_date.strftime('%Y-%m-%d'), "emails": new_emails_str}, ensure_ascii=False)
        data = {"message": "Update", "content": base64.b64encode(content_json.encode('utf-8')).decode('utf-8'), "sha": file_sha}
        if requests.put(url, headers=headers, json=data, timeout=5).status_code in [200, 201]:
            st.success("保存完了")
            st.rerun()

with col2:
    st.subheader("🚨 判定アラート")
    if st.session_state.confirmed_reservation and df is not None:
        res_info = df[df["日付キー"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可": st.error(f"⚠️ 警告: {curr['曜日付き日付']} は不可")
            else: st.success(f"✅ 良好: {curr['曜日付き日付']} は推奨")

st.divider()
st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC 公式サイトを開く</button></a>', unsafe_allow_html=True)
