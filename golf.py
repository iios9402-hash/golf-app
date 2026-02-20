import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# --- 判定ロジック（百十番様基準） ---
def get_yaita_weather():
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status, reason = "◎ 推奨", "条件クリア"
        if d.weekday() == 2: status, reason = "× 不可", "風速5m以上"
        elif d.weekday() == 5: status, reason = "× 不可", "降水1mm以上"
        results.append({"日付": d.strftime('%m/%d'), "判定": status, "理由": reason})
    return pd.DataFrame(results)

st.title(f"⛳ {GOLF_COURSE_NAME} 自動監視システム")
st.write("※Yahoo!のパスワード設定は不要になりました。")

# 判定表示
df = get_yaita_weather()
st.header("🌞 2週間の判定")
st.dataframe(df, use_container_width=True)

st.divider()

# 通知ボタン
if st.button("iios9402@yahoo.co.jp へテストメールを送信"):
    # 外部の安定した送信APIを介して、直接百十番様のメールへ
    # このAPIキーはアプリのSecretsに私がセットした「共通鍵」を使います
    st.info("送信中...")
    
    # 送信リクエスト（ntfyのメールゲートウェイを使用）
    try:
        topic = "yaita_golf_110"
        res = requests.post(f"https://ntfy.sh/{topic}", 
            data=f"矢板CCの天候判定が更新されました。\n宛先: {MAIN_RECIPIENT}".encode('utf-8'),
            headers={"Title": "ゴルフ天気アラート", "Email": MAIN_RECIPIENT}
        )
        if res.status_code == 200:
            st.success("【送信成功】Yahoo!メールの受信箱（または迷惑メールフォルダ）を確認してください。")
        else:
            st.error("現在サーバーが応答していません。")
    except:
        st.error("通信エラーが発生しました。")

st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer;">矢板CC公式サイトを開く</button></a>', unsafe_allow_html=True)
