import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

# --- 固定情報 ---
GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
WEATHER_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# Secretsから永続設定を読み込む
stored_date = st.secrets.get("CONFIRMED_DATE", "")
stored_emails = st.secrets.get("ADDITIONAL_EMAILS", "").split(",") if st.secrets.get("ADDITIONAL_EMAILS") else []

if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = stored_date if stored_date else None
if 'additional_emails' not in st.session_state:
    st.session_state.additional_emails = [e for e in stored_emails if e]

def fetch_weather_data():
    """tenki.jpから10日間分の気象データを取得し解析する"""
    results = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(WEATHER_URL, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        # 10日間予報テーブルを取得
        table = soup.find('table', class_='forecast-table-week')
        if not table:
            raise Exception("Table not found")

        # 行の抽出
        rows = table.find_all('tr')
        # 0:日付/曜日, 1:天気, 2:最高気温, 3:最低気温, 4:降水確率, 5:降水量, 6:風速
        date_tds = rows[0].find_all('td')
        weather_tds = rows[1].find_all('td')
        precip_tds = rows[5].find_all('td')  # 降水量
        wind_tds = rows[6].find_all('td')    # 風速

        for i in range(len(date_tds)):
            date_str = date_tds[i].text.strip().replace('\n', '')
            weather_text = weather_tds[i].find('p', class_='weather-telop').text.strip() if weather_tds[i].find('p', class_='weather-telop') else ""
            
            # 数値の抽出（「1」や「5」などの数値だけを抜き出す）
            try:
                precip_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', precip_tds[i].text)))
            except: precip_val = 0.0
            
            try:
                wind_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', wind_tds[i].text)))
            except: wind_val = 0.0

            # --- 百十番様の判定基準 ---
            status = "◎ 推奨"
            reason = "条件クリア"
            if precip_val >= 1.0:
                status = "× 不可"
                reason = f"降水量{precip_val}mm (条件5,6)"
            elif wind_val >= 5.0:
                status = "× 不可"
                reason = f"風速{wind_val}m (条件7)"

            results.append({
                "曜日付き": date_str,
                "判定": status,
                "理由": reason,
                "日付": (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            })
    except Exception as e:
        # 取得失敗時のバックアップ
        for i in range(14):
            d = datetime.now() + timedelta(days=i)
            results.append({
                "曜日付き": d.strftime('%m/%d(%a)'),
                "判定": "取得中",
                "理由": "サイト解析待機",
                "日付": d.strftime('%Y-%m-%d')
            })
    return pd.DataFrame(results)

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
st.write("プロオーディオ評論家「百十番」様専用（実況データ解析版）")

# 1. 解析データ表示
df = fetch_weather_data()
st.subheader("🌞 向こう10日間の気象判定（tenki.jp リアルタイム解析）")
# エラー回避のため、列の存在を確認してから表示
if not df.empty and "曜日付き" in df.columns:
    st.table(df[["曜日付き", "判定", "理由"]])
else:
    st.error("気象データの解析に失敗しました。サイト側の仕様変更の可能性があります。")

st.divider()

# 2. 予約記録・監視
col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約記録・通知先")
    try:
        curr_val = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d') if st.session_state.confirmed_reservation else datetime.now()
    except:
        curr_val = datetime.now()
    new_date = st.date_input("予約日を選択", value=curr_val, min_value=datetime.now())
    if st.button("予約日を反映"):
        st.session_state.confirmed_reservation = new_date.strftime('%Y-%m-%d')
        st.rerun()

    new_email = st.text_input("追加アドレスを入力")
    if st.button("アドレスを追加"):
        if new_email and new_email not in st.session_state.additional_emails:
            st.session_state.additional_emails.append(new_email)
            st.rerun()

with col2:
    st.subheader("🚨 予約日の監視状況")
    if st.session_state.confirmed_reservation:
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 警告: {curr['曜日付き']} は【{curr['理由']}】です")
            else:
                st.success(f"✅ 良好: {curr['曜日付き']} は現在条件をクリアしています")
    else:
        st.info("予約日が未設定です")

st.divider()

# 3. 通知 ＆ リンク
c1, c2 = st.columns(2)
with c1:
    if st.button("📩 登録全宛先へテストメール送信"):
        all_recs = [MAIN_RECIPIENT] + st.session_state.additional_emails
        target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
        body = f"百十番様\n\n矢板CC 判定通知\n予約日: {target}\n判定: アプリを確認してください。"
        for email in all_recs:
            try:
                requests.post("https://ntfy.sh/yaita_golf_110", data=body.encode('utf-8'),
                              headers={"Title": f"【矢板CC】通知({target})".encode('utf-8'), "Email": email, "Charset": "UTF-8"}, timeout=10)
            except: continue
        st.success("最新データに基づき送信完了しました。")

with c2:
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC公式サイトを開く</button></a>', unsafe_allow_html=True)
