import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
TENKI_JP_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# リロード対策（URLパラメータから日付を復元）
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = st.query_params.get("date", None)

def fetch_weather_from_tenki_jp():
    """tenki.jpから直接データを抽出し、百十番様の基準で判定する"""
    results = []
    try:
        # 人間のブラウザを偽装するための詳細なヘッダー
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }
        # セッションを維持してアクセス
        session = requests.Session()
        response = session.get(TENKI_JP_URL, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding
        
        if response.status_code != 200:
            return pd.DataFrame()

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='forecast-table-week')
        if not table:
            return pd.DataFrame()

        rows = table.find_all('tr')
        data = {}
        for row in rows:
            header = row.find('th')
            if header:
                label = header.text.strip()
                # 14日間分のtdを取得
                tds = [td.text.strip() for td in row.find_all('td')]
                # 天気だけは画像やテキストが特殊なので別途処理
                if "天気" in label:
                    telops = [p.text.strip() for p in row.find_all('p', class_='weather-telop')]
                    data["天気"] = telops
                else:
                    data[label] = tds

        # 各列をループして14日分（2週間）を構成
        dates = data.get("日付", [])
        precips = data.get("降水量", [])
        winds = data.get("風速", [])
        weathers = data.get("天気", [])

        for i in range(len(dates)):
            w_text = weathers[i] if i < len(weathers) else ""
            p_str = precips[i] if i < len(precips) else "0"
            w_str = winds[i] if i < len(winds) else "0"

            # 数値変換（"1" や "2" を抽出）
            try: p_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', p_str)))
            except: p_val = 0.0
            try: w_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', w_str)))
            except: w_val = 0.0

            status = "◎ 推奨"
            reason = "条件クリア"

            # 基本ルール
            if p_val >= 1.0:
                status = "× 不可"
                reason = f"降水 {p_val}mm"
            elif w_val >= 5.0:
                status = "× 不可"
                reason = f"風速 {w_val}m"
            
            # 11-13日目特別ルール（インデックス10, 11, 12）
            if i in [10, 11, 12] and "雨" in w_text:
                status = "× 不可"
                reason = "雨予報 (規定)"

            results.append({
                "曜日付き": dates[i].replace('\n', ''),
                "天気": w_text,
                "判定": status,
                "理由": reason,
                "日付": (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            })
        return pd.DataFrame(results)
    except:
        return pd.DataFrame()

# --- 画面表示 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
st.write("プロオーディオ評論家「百十番」様専用（tenki.jp 同期モデル）")

df = fetch_weather_from_tenki_jp()

# 1. 2週間判定（全表示）
st.subheader("🌞 向こう2週間の気象判定")
if not df.empty:
    st.table(df[["曜日付き", "天気", "判定", "理由"]])
    st.markdown(f"情報源: [tenki.jp 矢板カントリークラブ２週間予報]({TENKI_JP_URL})")
else:
    st.error("現在、tenki.jpからのデータ受信が不安定です。数分後にブラウザを更新してください。")

st.divider()

# 2. 監視・設定
col1, col2 = st.columns(2)
with col1:
    st.subheader("📝 予約設定")
    try:
        d_val = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d') if st.session_state.confirmed_reservation else datetime.now()
    except:
        d_val = datetime.now()
    
    new_date = st.date_input("予約日を選択", value=d_val, min_value=datetime.now())
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

# 3. 通知テスト
if st.button("📩 登録アドレスへテストメール送信"):
    target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
    body = f"百十番様\n\n矢板CC 判定結果\n予約日: {target}\n判定: アプリを確認してください。"
    try:
        requests.post("https://ntfy.sh/yaita_golf_110", data=body.encode('utf-8'),
                      headers={"Title": f"【矢板CC】通知({target})".encode('utf-8'), "Email": MAIN_RECIPIENT, "Charset": "UTF-8"}, timeout=10)
        st.success("最新データで送信完了しました。")
    except:
        st.error("送信エラー")
