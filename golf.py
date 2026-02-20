import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
WEATHER_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# Secretsから読み込み
stored_date = st.secrets.get("CONFIRMED_DATE", "")
stored_emails = st.secrets.get("ADDITIONAL_EMAILS", "").split(",") if st.secrets.get("ADDITIONAL_EMAILS") else []

if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = stored_date if stored_date else None
if 'additional_emails' not in st.session_state:
    st.session_state.additional_emails = [e for e in stored_emails if e]

def fetch_weather_data():
    """tenki.jpの表から項目名を検索して数値を抽出する堅牢なロジック"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(WEATHER_URL, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='forecast-table-week')
        if not table: return pd.DataFrame()

        rows = table.find_all('tr')
        data_map = {}
        
        # 各行の先頭にある見出し（th）を見て、どの行が何のデータか特定する
        for row in rows:
            header = row.find('th')
            if header:
                label = header.text.strip()
                data_map[label] = [td.text.strip() for td in row.find_all('td')]

        # データの抽出（項目名で探すので確実です）
        dates = data_map.get("日付", [])
        precips = data_map.get("降水量", [])
        winds = data_map.get("風速", [])

        results = []
        for i in range(len(dates)):
            # 数値変換の安全処理
            try:
                p_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', precips[i])))
            except: p_val = 0.0
            try:
                w_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', winds[i])))
            except: w_val = 0.0

            # 百十番様の判定基準
            status = "◎ 推奨"
            reason = "条件クリア"
            if p_val >= 1.0:
                status = "× 不可"
                reason = f"降水 {p_val}mm"
            elif w_val >= 5.0:
                status = "× 不可"
                reason = f"風速 {w_val}m"

            results.append({
                "曜日付き": dates[i].replace('\n', ''),
                "判定": status,
                "理由": reason,
                "日付": (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            })
        return pd.DataFrame(results)
    except:
        return pd.DataFrame()

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
st.write("プロオーディオ評論家「百十番」様専用（高精度解析モデル）")

df = fetch_weather_data()

# 1. 解析データ表示
st.subheader(f"🌞 {WEATHER_URL} の実測値に基づく判定")
if not df.empty:
    st.table(df[["曜日付き", "判定", "理由"]])
else:
    st.error("気象データの取得に失敗しました。サイトがメンテナンス中か、接続制限の可能性があります。")

st.divider()

# 2. 監視状況
col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約設定")
    curr_d = datetime.now()
    if st.session_state.confirmed_reservation:
        try: curr_d = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d')
        except: pass
    new_date = st.date_input("予約日を選択", value=curr_d, min_value=datetime.now())
    if st.button("予約日を更新"):
        st.session_state.confirmed_reservation = new_date.strftime('%Y-%m-%d')
        st.rerun()

with col2:
    st.subheader("🚨 判定アラート")
    if st.session_state.confirmed_reservation and not df.empty:
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 警告: {curr['曜日付き']} は【{curr['理由']}】のため推奨しません。")
            else:
                st.success(f"✅ 良好: {curr['曜日付き']} は現在条件をクリアしています。")
    else:
        st.info("予約日を更新して判定を確認してください。")

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
        st.success("最新データで送信しました。")

with c2:
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイトを開く</button></a>', unsafe_allow_html=True)
