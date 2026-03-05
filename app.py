import streamlit as st
import requests
import time
from fp.fp import FreeProxy

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pro SMS Panel V6.4", layout="wide", page_icon="📲")

try:
    S = st.secrets
    KEYS = {
        "t": S["TIGER_API_KEY"], "o": S["ONLINESIM_API_KEY"], "h": S["HERO_API_KEY"],
        "p": S["PANEL_SIFRESI"], "tg": S["TELEGRAM_TOKEN"], "cid": S["TELEGRAM_CHAT_ID"]
    }
except:
    st.error("Secrets (API Anahtarları) eksik!"); st.stop()

# --- 2. FONKSİYONLAR ---
def get_proxy():
    try: return FreeProxy(https=True, rand=True, timeout=0.5).get()
    except: return None

def send_tg_test():
    url = f"https://api.telegram.org/bot{KEYS['tg']}/sendMessage"
    requests.post(url, data={"chat_id": KEYS["cid"], "text": "🔔 Panel bağlantısı aktif! Telegram bildirimleri çalışıyor."}, timeout=5)

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'order' not in st.session_state: st.session_state.order = None

# --- 4. GİRİŞ ---
if not st.session_state.auth:
    st.title("🔐 Giriş Yap")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş") and pwd == KEYS["p"]:
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 5. SIDEBAR (BAKİYE & STOK GÜNCELLEME) ---
with st.sidebar:
    st.title("🤖 Kontrol")
    
    # Tiger & Hero Verileri (Hızlı)
    try:
        t_b = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["t"], "action": "getBalance"}, timeout=5).text
        h_b = requests.get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["h"], "action": "getBalance"}, timeout=5).text
        t_bal = t_b.split(':')[1] if 'ACCESS' in t_b else "0"
        h_bal = h_b.split(':')[1] if 'ACCESS' in h_b else "0"
        
        # Stoklar (Tiger & Hero için otomatik çekim)
        t_stock = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["t"], "action": "getPrices", "country": "62"}, timeout=5).json().get("62", {})
        h_stock = requests.get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["h"], "action": "getPrices", "country": "62"}, timeout=5).json().get("62", {})
    except:
        t_bal, h_bal, t_stock, h_stock = "0", "0", {}, {}

    st.metric("🐯 Tiger", f"{t_bal} RUB")
    st.metric("🦸 Hero", f"{h_bal} $")
    
    st.write("---")
    if st.button("🔔 Telegram Botu Test Et"):
        send_tg_test(); st.toast("Test mesajı gönderildi!")
    
    if st.button("🔄 Verileri Yenile"): st.rerun()

# --- 6. ALIM FONKSİYONU ---
def process_buy(src, svc, country="62"):
    with st.spinner("Numara alınıyor..."):
        res = None
        if src == "o":
            px = get_proxy()
            try:
                res = requests.get("https://onlinesim.io/api/getNum.php", {"apikey": KEYS["o"], "service": svc, "country": "90"}, proxies={"http":px, "https":px}, timeout=12).json()
                if res.get("response") == "1":
                    st.session_state.order = {"id": res["tzid"], "num": res["number"], "src": "o", "name": svc}
                else: st.error("Osim Hatası: Stok yok veya IP ban.")
            except: st.error("Osim bağlantısı başarısız (Proxy hatası).")
        else:
            url = "https://api.tiger-sms.com/stubs/handler_api.php" if src == "t" else "https://hero-sms.com/stubs/handler_api.php"
            try:
                r = requests.get(url, {"api_key": KEYS[src], "action": "getNumber", "service": svc, "country": country}, timeout=10).text
                if "ACCESS" in r:
                    p = r.split(":"); st.session_state.order = {"id": p[1], "num": p[2], "src": src, "name": svc}
                else: st.error(f"Hata: {r}")
            except: st.error("Bağlantı hatası!")

# --- 7. ANA PANEL ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🦸 Hero", "🔵 OnlineSim"])

with t1:
    st.subheader("Tiger SMS (Endonezya)")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"🍔 Yemeksepeti: {t_stock.get('yi', {}).get('cost', '-')} RUB")
        if st.button("T-YEMEK AL", key="t_yi"): process_buy("t", "yi")
    with c2:
        st.write(f"🚗 Uber: {t_stock.get('ub', {}).get('cost', '-')} RUB")
        if st.button("T-UBER AL", key="t_ub"): process_buy("t", "ub")

with t2:
    st.subheader("Hero SMS (Endonezya)")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"🍔 Yemeksepeti: {h_stock.get('yi', {}).get('cost', '-')} $")
        if st.button("H-YEMEK AL", key="h_yi"): process_buy("h", "yi")
    with c2:
        st.write(f"🚗 Uber: {h_stock.get('ub', {}).get('cost', '-')} $")
        if st.button("H-UBER AL", key="h_ub"): process_buy("h", "ub")

with t3:
    st.subheader("OnlineSim (Türkiye - Proxy)")
    st.info("OnlineSim için proxy kullanıldığından butonlara bastığınızda 10-15 saniye bekletebilir.")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🍔 Yemeksepeti (O)", key="o_yi"): process_buy("o", "yemeksepeti")
    with c2:
        if st.button("🚗 Uber (O)", key="o_ub"): process_buy("o", "uber")
    with c3:
        if st.button("☕ Espressolab (O)", key="o_es"): process_buy("o", "espressolab")

# --- 8. TAKİP ALANI ---
if st.session_state.order:
    ord = st.session_state.order
    st.divider()
    with st.container():
        st.success(f"✅ Aktif Numara: +{ord['num']} | Servis: {ord['src'].upper()}")
        st.info("Kod geldiğinde otomatik olarak Telegram botunuza gönderilecektir.")
        if st.button("🗑️ Siparişi Kapat ve Temizle"):
            st.session_state.order = None; st.rerun()
