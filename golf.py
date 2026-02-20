import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# アプリの基本設定
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

# 固定情報
GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaitacc.com/"

st.title(f"⛳ {GOLF_COURSE_NAME} 予約支援システム")

# 判定ロジック（要件5,6,7を反映したシミュレーション）
def check_golf_weather():
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    res = []
    for d in dates:
        recommend = "◎ 推奨"
        reason = "風・雨ともに条件をクリアしています"
        
        # ダミーデータ：実際にはここを天気サイトと連動させます
        if d.weekday() == 2: # 例：風が強い日
            recommend = "× 不可"
            reason = "風速5m以上の予報（条件7違反）"
        elif d.weekday() == 5: # 例：雨の日
            recommend = "× 不可"
            reason = "8-16時に1mm以上の降水（条件5,6違反）"
            
        res.append({"日付": d.strftime('%m/%d(%a)'), "判定": recommend, "理由": reason})
    return pd.DataFrame(res)

# 画面表示
st.subheader("🌞 向こう2週間のプレー推奨日")
df = check_golf_weather()
ok_days = df[df["判定"] == "◎ 推奨"]

if not ok_days.empty:
    st.success(f"条件をクリアした日が {len(ok_days)} 日あります。")
    selected_day = st.selectbox("予約を検討する日を選択", ok_days["日付"])
    
    if st.button("予約画面へ（公式サイトを開く）"):
        st.write(f"こちらのリンクから予約してください： {RESERVATION_URL}")
        st.info("予約完了後、下の入力欄で保存してください。")
else:
    st.warning("現在、条件を満たす日はありません。")

st.divider()
st.subheader("📝 予約状況の記録")
res_date = st.date_input("予約した日を選択", value=datetime.now())
if st.button("予約確定として保存"):
    st.success(f"{res_date} の予約をシステムに保存しました。")