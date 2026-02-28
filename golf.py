import streamlit as st
import pandas as pd
import requests
import json
import base64
from datetime import datetime, timedelta

# --- 1. 基本コンセプト & 6. インターフェース仕様 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
TENKI_JP_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
# 8. 追加要件（デフォルト送信先）
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# 2. 情報ソース（Open-Meteo API JMA準拠モデル）
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=36.8091&longitude=139.9073&daily=weather_code,precipitation_sum,wind_speed_10m_max&timezone=Asia%2FTokyo&wind_speed_unit=ms&forecast_days=14"

# 4. 永続化設定（GitHub同期）
GITHUB_TOKEN = str(st.secrets.get("GH_TOKEN", "")).strip()
REPO_NAME = str(st.secrets.get("GH_REPO", "")).strip()
FILE_PATH = "settings.json"

def load_settings():
    """7-1. GitHub Persistence Module: 設定のロード"""
    default_vals = {"date": None, "emails": ""}
    if not GITHUB_TOKEN or not REPO_NAME:
        return default_vals, None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return json.loads(content), res.json()['sha']
    except:
        pass
    return default_vals, None

def save_settings(date_str, emails_str, current_sha):
    """GitHubへの永続保存"""
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content_json = json.dumps({"date": date_str, "emails": emails_str}, ensure_ascii=False)
    data = {
        "message": "Sync settings",
        "content": base64.b64encode(content_json.encode('utf-8')).decode('utf-8'),
        "sha": current_sha
    }
    try:
        res = requests.put(url, headers=headers, json=data, timeout=10)
        return res.status_code in [200, 201]
    except:
        return False

# 起動時の設定読み込み
settings_data, file_sha = load_settings()

if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = settings_data.get("date")
if 'additional_emails' not in st.session_state:
    emails_raw = settings_data.get("emails", "")
    st.session_state.additional_emails = [e.strip() for e in emails_raw.split(",") if e]

def fetch_weather():
    """7-2. Weather Engine: 3. 判定アルゴリズムの実装"""
    try:
        res = requests.get(API_URL, timeout=15)
        res.raise_for_status()
        daily = res.json()['daily']
        results = []
        
        # 天気コードから「雨」を判定（WMO基準）
        rain_codes = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
        
        for i in range(len(daily['time'])):
            d_obj = datetime.strptime(daily['time'][i], '%Y-%m-%d')
            p_val = round(daily['precipitation_sum'][i], 1)
            w_val = round(daily['wind_speed_10m_max'][i], 1)
            is_rain_text = daily['weather_code'][i] in rain_codes
            
            w_desc = "雨" if is_rain_text else "晴/曇"
            status, reason = "◎ 推奨", "条件クリア"
            
            # 判定アルゴリズム
            # 通常（1-10日, 14日目）/ 警戒（11-13日目 ※インデックス10,11,12）
            if p_val >= 1.0:
                status, reason = "× 不可", f"降水 {p_val}mm"
            elif w_val >= 5.0:
                status, reason = "× 不可", f"風速 {w_val}m"
            elif i in [10, 11, 12] and is_rain_text:
                status, reason = "× 不可", "雨予報 (警戒期間)"
            
            results.append({
                "曜日付き日付": d_obj.strftime('%m/%d(%a)'),
                "天気": w_desc,
                "判定": status,
                "理由": reason,
                "日付キー": daily['time'][i]
            })
        return pd.DataFrame(results)
    except:
        return pd.DataFrame()

# --- 6. UIコンポーネント ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")

df = fetch_weather()

# 2. 表示仕様（2週間一括表示）
st.subheader("🌞 向こう2週間の気象判定")
if not df.empty:
    # 項目：「曜日付き日付」「天気」「判定」「理由」
    st.table(df[["曜日付き日付", "天気", "判定", "理由"]])
    st.markdown(f"情報源: [tenki.jp 矢板カントリークラブ2週間予報]({TENKI_JP_URL})")
else:
    st.error("現在、気象データを一時的に取得できません。API制限または通信エラーの可能性があります。")
    if st.button("🔄 予報データの再取得を試みる"):
        st.rerun()

st.divider()

# 4. 予約管理 UI
col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約・通知設定")
    current_date = datetime.now()
    if st.session_state.confirmed_reservation:
        try:
            current_date = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d')
        except: pass
    
    new_date = st.date_input("予約確定日を選択", value=current_date)
    emails_text = ",".join(st.session_state.additional_emails)
    new_emails_str = st.text_area("追加通知先メールアドレス（カンマ区切り）", value=emails_text)
    
    if st.button("設定を完全に保存する"):
        date_str = new_date.strftime('%Y-%m-%d')
        if save_settings(date_str, new_emails_str, file_sha):
            st.session_state.confirmed_reservation = date_str
            st.session_state.additional_emails = [e.strip() for e in new_emails_str.split(",") if e]
            st.success("GitHub同期完了。設定は永続的に保持されます。")
            st.rerun()
        else:
            st.error("保存失敗。SecretsまたはGitHubのファイル状態を確認してください。")

with col2:
    st.subheader("🚨 判定アラート")
    if st.session_state.confirmed_reservation and not df.empty:
        res_info = df[df["日付キー"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 警告: {curr['曜日付き日付']} は【{curr['理由']}】です。")
            else:
                st.success(f"✅ 良好: {curr['曜日付き日付']} は条件をクリアしています。")
    else:
        st.info("予約日を設定すると、ここに判定結果が表示されます。")

st.divider()

# 5. 通知機能（7-3. Communication Layer）
if st.button("📩 登録全アドレスへテストメール送信"):
    all_recipients = [MAIN_RECIPIENT] + st.session_state.additional_emails
    target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
    
    # 8. 追加要件に基づき、ntfy.sh経由で送信（パスワード不要）
    body = f"矢板CC 判定結果\n予約日: {target}\n詳細はアプリを確認してください。"
    title = f"【矢板CC】判定通知({target})"
    
    success_count = 0
    for email in all_recipients:
        try:
            res = requests.post(
                "https://ntfy.sh/yaita_golf_110",
                data=body.encode('utf-8'),
                headers={
                    "Title": title.encode('utf-8'),
                    "Email": email,
                    "Charset": "UTF-8"
                },
                timeout=10
            )
            if res.status_code == 200:
                success_count += 1
        except: pass
    
    if success_count > 0:
        st.success(f"テストメールを {success_count} 件送信しました。")
    else:
        st.error("送信に失敗しました。")

# 6. クイックアクセス
st.markdown(f'<br><a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC 公式サイトを開く</button></a>', unsafe_allow_html=True)
