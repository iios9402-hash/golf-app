import streamlit as st
import pandas as pd
import requests
import json
import base64
from datetime import datetime, date

# --- 永続化仕様: キャッシュの強制クリア ---
st.cache_data.clear()

# --- 1. 基本コンセプト & 6. インターフェース仕様 ---
st.set_page_config(page_title="矢板CC 監視システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
TENKI_JP_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# 2. 情報ソース
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=36.8091&longitude=139.9073&daily=weather_code,precipitation_sum,wind_speed_10m_max&timezone=Asia%2FTokyo&wind_speed_unit=ms&forecast_days=14"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

# 4. 永続化設定
GITHUB_TOKEN = str(st.secrets.get("GH_TOKEN", "")).strip()
REPO_NAME = str(st.secrets.get("GH_REPO", "")).strip()
FILE_PATH = "settings.json"

def load_settings():
    default_vals = {"date": None, "emails": ""}
    if not GITHUB_TOKEN or not REPO_NAME: return default_vals, None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            data = json.loads(content)
            # 過去日の自動クリア
            if data.get("date"):
                try:
                    saved_date = datetime.strptime(data["date"], '%Y-%m-%d').date()
                    if saved_date < date.today(): data["date"] = None
                except: data["date"] = None
            return data, res.json()['sha']
    except: pass
    return default_vals, None

def save_settings(date_val, emails_str, current_sha):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    # 保存データ。Noneの場合はnullとして保存
    content_json = json.dumps({"date": date_val, "emails": emails_str}, ensure_ascii=False)
    payload = {"message": "Update settings", "content": base64.b64encode(content_json.encode('utf-8')).decode('utf-8'), "sha": current_sha}
    try:
        res = requests.put(url, headers=headers, json=payload, timeout=5)
        return res.status_code in [200, 201]
    except: return False

# 設定ロード
settings_data, file_sha = load_settings()
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = settings_data.get("date")

def fetch_weather():
    rain_codes = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
    try:
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
            results.append({"曜日付き日付": d_obj.strftime('%m/%d(%a)'), "天気": w_desc, "判定": status, "理由": reason, "日付キー": daily['time'][i]})
        return pd.DataFrame(results)
    except: return None

# --- UI ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
df = fetch_weather()

st.subheader("🌞 向こう2週間の気象判定")
if df is not None:
    st.table(df[["曜日付き日付", "天気", "判定", "理由"]])
    st.markdown(f"情報源: [tenki.jp 矢板カントリークラブ2週間予報]({TENKI_JP_URL})")
else:
    st.error("気象データの取得に失敗しました。")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約・通知設定")
    
    # --- 修正: デフォルトを空白(None)にする ---
    initial_date = None
    if st.session_state.confirmed_reservation:
        try: initial_date = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d').date()
        except: pass
    
    # date_inputのvalueをNoneにすることで「空欄」を実現
    new_date = st.date_input("予約確定日を選択", value=initial_date, help="予約がない場合は空欄のままにしてください")
    
    emails_text = ",".join([e.strip() for e in settings_data.get("emails", "").split(",") if e])
    new_emails_str = st.text_area("追加通知先（カンマ区切り）", value=emails_text)
    
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("設定を完全に保存する", use_container_width=True):
            save_val = new_date.strftime('%Y-%m-%d') if new_date else None
            if save_settings(save_val, new_emails_str, file_sha):
                st.session_state.confirmed_reservation = save_val
                st.success("保存完了")
                st.rerun()
    with btn_col2:
        if st.button("予約日をリセット", use_container_width=True):
            if save_settings(None, new_emails_str, file_sha):
                st.session_state.confirmed_reservation = None
                st.warning("予約日を空欄にリセットしました")
                st.rerun()

with col2:
    st.subheader("🚨 判定アラート")
    # 予約日がNone（空）でない場合のみ、判定を表示
    if st.session_state.confirmed_reservation and df is not None:
        res_info = df[df["日付キー"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可": st.error(f"⚠️ 警告: {curr['曜日付き日付']} は不可")
            else: st.success(f"✅ 良好: {curr['曜日付き日付']} は推奨")
    else:
        st.info("現在、予約日は設定されていません。")

st.divider()
st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC 公式サイトを開く</button></a>', unsafe_allow_html=True)
