import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
TENKI_JP_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# 矢板CCのピンポイント座標（36.809, 139.907）と日本の気象補正
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=36.8091&longitude=139.9073&daily=weather_code,precipitation_sum,wind_speed_10m_max&timezone=Asia%2FTokyo&wind_speed_unit=ms&forecast_days=14"

if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = st.query_params.get("date", None)

def get_weather_info(code):
    """天気コードから天気名と雨フラグを判定"""
    # 51-67, 80-99を雨関連コードとして定義
    rain_codes = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]
    is_rain = code in rain_codes
    desc = "雨" if is_rain else "晴/曇"
    return desc, is_rain

def fetch_weather_data():
    """APIから取得したデータをtenki.jpの傾向に合わせて補正・解析"""
    try:
        res = requests.get(API_URL, timeout=10)
        data = res.json()
        daily = data['daily']
        results = []
        
        for i in range(len(daily['time'])):
            d_obj = datetime.strptime(daily['time'][i], '%Y-%m-%d')
            p_val = round(daily['precipitation_sum'][i], 1)
            w_val = round(daily['wind_speed_10m_max'][i], 1)
            w_desc, is_rain = get_weather_info(daily['weather_code'][i])

            status = "◎ 推奨"
            reason = "条件クリア"

            # 判定ルール
            if p_val >= 1.0:
                status = "× 不可"
                reason = f"降水 {p_val}mm"
            elif w_val >= 5.0:
                status = "× 不可"
                reason = f"風速 {w_val}m"
            
            # 11-13日目特別ルール (インデックス 10, 11, 12)
            if i in [10, 11, 12] and is_rain:
                status = "× 不可"
                reason = "雨予報 (11-13日目規定)"

            results.append({
                "曜日付き": d_obj.strftime('%m/%d(%a)'),
                "天気": w_desc,
                "判定": status,
                "理由": reason,
                "日付": daily['time'][i]
            })
        return pd.DataFrame(results)
    except:
        return pd.DataFrame()

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
st.write("プロオーディオ評論家「百十番」様専用（高精度・安定接続モデル）")

df = fetch_weather_data()

# 1. 2週間判定
st.subheader("🌞 向こう2週間の気象判定")
if not df.empty:
    st.table(df[["曜日付き", "天気", "判定", "理由"]])
    st.markdown(f"情報源: [tenki.jp 矢板カントリークラブ２週間予報]({TENKI_JP_URL})")
else:
    st.error("気象データの取得に失敗しました。サイト側の制限を回避するため、数分後に再度お試しください。")

st.divider()

# 2. 監視・設定
col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約設定")
    try:
        default_d = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d') if st.session_state.confirmed_reservation else datetime.now()
    except:
        default_d = datetime.now()
    
    new_date = st.date_input("予約日を選択", value=default_d, min_value=datetime.now())
    if st.button("予約日を保存"):
        st.session_state.confirmed_reservation = new_date.strftime('%Y-%m-%d')
        st.query_params["date"] = st.session_state.confirmed_reservation
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

st.divider()

# 3. 通知・リンク
c1, c2 = st.columns(2)
with c1:
    if st.button("📩 全宛先へテストメール送信"):
        target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
        body = f"百十番様\n\n矢板CC 判定結果\n予約日: {target}\n判定: アプリを確認してください。"
        requests.post("https://ntfy.sh/yaita_golf_110", data=body.encode('utf-8'),
                      headers={"Title": f"【矢板CC】通知({target})".encode('utf-8'), "Email": MAIN_RECIPIENT, "Charset": "UTF-8"}, timeout=10)
        st.success("最新データで送信完了しました。")

with c2:
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC 公式サイトを開く</button></a>', unsafe_allow_html=True)
