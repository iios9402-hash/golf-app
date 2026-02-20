import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# 矢板CCの座標。forecast_days=14 で2週間分を取得
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=36.8039&longitude=139.9042&daily=precipitation_sum,wind_speed_10m_max&timezone=Asia%2FTokyo&wind_speed_unit=ms&forecast_days=14"

# --- 永続的な保存ロジック（リロード対策） ---
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = st.query_params.get("date", None)

def fetch_weather_data():
    """2週間(14日間)の正確な気象データを取得"""
    try:
        res = requests.get(API_URL, timeout=10)
        data = res.json()
        daily = data['daily']
        results = []
        for i in range(len(daily['time'])):
            d_obj = datetime.strptime(daily['time'][i], '%Y-%m-%d')
            p_val = round(daily['precipitation_sum'][i], 1)
            w_val = round(daily['wind_speed_10m_max'][i], 1)

            # 百十番様の判定基準（雨1mm、風5m）
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
                "日付": daily['time'][i]
            })
        return pd.DataFrame(results)
    except:
        return pd.DataFrame()

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
st.write("プロオーディオ評論家「百十番」様専用（2週間フルレンジ監視モデル）")

df = fetch_weather_data()

# 1. 2週間判定（全表示・スクロールなし）
st.subheader("🌞 向こう2週間の気象判定")
if not df.empty:
    # 14行すべてを一度に表示
    st.table(df[["曜日付き", "判定", "理由"]])
else:
    st.error("データ取得エラー。通信環境を確認してリロードしてください。")

st.divider()

# 2. 監視状況
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
        # URLに日付を刻むことでリロード後も保持
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
    else:
        st.info("予約日を保存して判定を確認してください。")

st.divider()

# 3. 通知・リンク
c1, c2 = st.columns(2)
with c1:
    if st.button("📩 全宛先へテストメール送信"):
        target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
        body = f"百十番様\n\n矢板CC 判定結果\n予約日: {target}\n判定: アプリを確認してください。"
        # 送信エンドポイント
        requests.post("https://ntfy.sh/yaita_golf_110", data=body.encode('utf-8'),
                      headers={"Title": f"【矢板CC】判定({target})".encode('utf-8'), "Email": MAIN_RECIPIENT, "Charset": "UTF-8"}, timeout=10)
        st.success("最新データで送信完了しました。")

with c2:
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイトを開く</button></a>', unsafe_allow_html=True)
