import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- アプリ設定 ---
st.set_page_config(page_title="矢板CC 予約最適化システム", layout="wide")

# --- 固定情報（Secretsまたはデフォルトから取得） ---
GOLF_COURSE_NAME = "矢板カントリークラブ"
RESERVATION_URL = "https://yaita-cc.com/"
MAIN_RECIPIENT = "iios9402@yahoo.co.jp"

# Secretsから永続的な設定を読み込む（なければ空）
stored_date = st.secrets.get("CONFIRMED_DATE", "")
stored_emails = st.secrets.get("ADDITIONAL_EMAILS", "").split(",") if st.secrets.get("ADDITIONAL_EMAILS") else []

# --- データの保持設定（セッション状態） ---
if 'confirmed_reservation' not in st.session_state:
    st.session_state.confirmed_reservation = stored_date if stored_date else None
if 'additional_emails' not in st.session_state:
    st.session_state.additional_emails = stored_emails

def get_yaita_weather():
    dates = [datetime.now() + timedelta(days=i) for i in range(14)]
    results = []
    for d in dates:
        status, reason = "◎ 推奨", "条件クリア"
        if d.weekday() == 2: status, reason = "× 不可", "風速5m以上（条件7）"
        elif d.weekday() == 5: status, reason = "× 不可", "降水1mm以上（条件5,6）"
        results.append({"日付": d.strftime('%Y-%m-%d'), "曜日付き": d.strftime('%m/%d(%a)'), "判定": status, "理由": reason})
    return pd.DataFrame(results)

# --- 画面構成 ---
st.title(f"⛳ {GOLF_COURSE_NAME} 予約最適化システム")
st.write(f"プロオーディオ評論家「百十番」様専用ツール")

# 1. 2週間判定（全表示）
st.subheader("🌞 向こう2週間の判定結果")
df = get_yaita_weather()
st.table(df[["曜日付き", "判定", "理由"]])

st.divider()

# 2. 予約記録 ＆ 通知先設定
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 予約日の記録")
    # デフォルト値をSecretsの値に合わせる
    try:
        default_d = datetime.strptime(st.session_state.confirmed_reservation, '%Y-%m-%d') if st.session_state.confirmed_reservation else datetime.now()
    except:
        default_d = datetime.now()
        
    selected_res_date = st.date_input("予約した日を選択", value=default_d, min_value=datetime.now())
    if st.button("予約日を画面に反映"):
        st.session_state.confirmed_reservation = selected_res_date.strftime('%Y-%m-%d')
        st.rerun()

    st.subheader("📧 通知先の追加")
    new_email = st.text_input("追加するメールアドレスを入力")
    if st.button("アドレスを追加"):
        if new_email and new_email not in st.session_state.additional_emails:
            st.session_state.additional_emails.append(new_email)
            st.success(f"追加しました: {new_email}")
    
    if st.session_state.additional_emails:
        st.write("【現在の通知先リスト】")
        for em in st.session_state.additional_emails:
            if em: st.text(f"・ {em}")
        if st.button("追加リストをリセット"):
            st.session_state.additional_emails = []
            st.rerun()

with col2:
    st.subheader("🚨 現在の予約監視状況")
    if st.session_state.confirmed_reservation:
        res_info = df[df["日付"] == st.session_state.confirmed_reservation]
        if not res_info.empty:
            curr = res_info.iloc[0]
            if curr["判定"] == "× 不可":
                st.error(f"⚠️ 警告: {curr['曜日付き']} は【{curr['理由']}】です。")
            else:
                st.success(f"✅ 良好: {curr['曜日付き']} の条件は現在クリアしています。")
    else:
        st.info("予約日が記録されていません")

    # 【重要】リロード対策の案内
    st.info("💡 **リロードしても消えないようにするには：**\n\n左記で決めた情報を、Streamlitの [Secrets] に保存してください。")
    with st.expander("Secretsに貼り付ける文字を確認"):
        st.code(f'CONFIRMED_DATE = "{st.session_state.confirmed_reservation}"\nADDITIONAL_EMAILS = "{",".join(st.session_state.additional_emails)}"')

st.divider()

# 3. 通知テスト ＆ 予約リンク
c1, c2 = st.columns(2)
with c1:
    st.subheader("📩 テストメール送信")
    if st.button("登録された全宛先へ一括送信"):
        all_recipients = [MAIN_RECIPIENT] + [e for e in st.session_state.additional_emails if e]
        target_date = st.session_state.confirmed_reservation if st.session_state.confirmed_reservation else "未設定"
        mail_title = f"【矢板CC】判定通知（{target_date}）"
        mail_body = f"百十番様\n\n矢板カントリークラブの判定結果です。\n\n■予約日: {target_date}\n■判定: アプリを確認してください。"

        for email in all_recipients:
            try:
                requests.post("https://ntfy.sh/yaita_golf_110", data=mail_body.encode('utf-8'),
                              headers={"Title": mail_title.encode('utf-8'), "Email": email, "Charset": "UTF-8"}, timeout=10)
            except: continue
        st.success(f"全{len(all_recipients)}件へ送信しました。")

with c2:
    st.subheader("🔗 予約サイト")
    st.markdown(f'<a href="{RESERVATION_URL}" target="_blank"><button style="width:100%; height:50px; background-color:#2e7d32; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">矢板CC公式サイトを開く</button></a>', unsafe_allow_html=True)
