import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
TENKI_JP_URL = "https://tenki.jp/leisure/golf/3/12/644217/week.html"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = st.query_params.get("date", None)

def fetch_yaita_tenki_direct():
    """tenki.jpから2週間分の実データを直接取得・解析する"""
    results = []
    try:
        # ブラウザからのアクセスを装うヘッダー
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(TENKI_JP_URL, headers=headers, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        # 10日間・14日間予報テーブルを探す
        table = soup.find('table', class_='forecast-table-week')
        if not table: return pd.DataFrame()

        rows = table.find_all('tr')
        # 行の役割を特定
        dates, weathers, precips, winds = [], [], [], []
        for row in rows:
            th_text = row.find('th').text.strip() if row.find('th') else ""
            tds = [td.text.strip() for td in row.find_all('td')]
            if "日付" in th_text: dates = tds
            elif "天気" in th_text: weathers = [p.text.strip() for p in row.find_all('p', class_='weather-telop')]
            elif "降水量" in th_text: precips = tds
            elif "風速" in th_text: winds = tds

        # 14日間（あるいは取得できた全日数）ループ
        for i in range(len(dates)):
            w_text = weathers[i] if i < len(weathers) else ""
            p_str = precips[i] if i < len(precips) else "0"
            w_str = winds[i] if i < len(winds) else "0"
            
            # 数値抽出
            try: p_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', p_str)))
            except: p_val = 0.0
            try: w_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', w_str)))
            except: w_val = 0.0

            # 判定ロジック
            status = "◎ 推奨"
            reason = "条件クリア"
            
            # 基本基準
            if p_val >= 1.0:
                status = "× 不可"
                reason = f"降水 {p_val}mm"
            elif w_val >= 5.0:
                status = "× 不可"
                reason = f"風速 {w_val}m"
            
            # 11-13日目特別ルール (i=10, 11, 12)
            if i in [10, 11, 12] and "雨" in w_text:
                status = "× 不可"
                reason = "雨予報 (11-13日目規定)"

            results.append({
                "曜日付き": dates[i].replace('\n', ''),
                "天気": w_text,
                "判定": status,
                "理由": reason,
                "日付": (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            })
        return pd.DataFrame(results)
    except Exception as e:
        return pd.DataFrame()

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
st.write("プロオーディオ評論家「百十番」様専用（tenki.jp ダイレクト同期モデル）")

df = fetch_yaita_tenki_direct()

# 1. 2週間判定
st.subheader("🌞 向こう2週間の気象判定")
if not df.empty:
    st.table(df[["曜日付き", "天気", "判定", "理由"]])
    st.markdown(f"情報源: [tenki.jp 矢板カントリークラブ２週間予報]({TENKI_JP_URL})")
else:
    st.error("tenki.jpからのデータ取得に失敗しました。サイトの仕様変更か、一時的なアクセス制限の可能性があります。")

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
    if st.button("📩 テストメール送信"):
        target = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
        body = f"百十番様\n\n矢板CC 判定通知\n予約日: {target}\n判定: アプリを確認してください。"
        requests.post("https://ntfy.sh/yaita_golf_110", data=body.encode('utf-8'),
                      headers={"Title": f"【矢板CC】通知({target})".encode('utf-8'), "Email": MAIN_RECIPIENT, "Charset": "UTF-8"}, timeout=10)
        st.success("最新データで送信完了しました。")

with c2:
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC 公式サイトを開く</button></a>', unsafe_allow_html=True)
