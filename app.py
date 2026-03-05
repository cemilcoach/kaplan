import streamlit as st
import requests
import time

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pro SMS Panel V6.5", layout="wide", page_icon="📲")

try:
    S = st.secrets
    KEYS = {
        "t": S["TIGER_API_KEY"], "o": S["ONLINESIM_API_KEY"], "h": S["HERO_API_KEY"],
        "p": S["PANEL_SIFRESI"], "tg": S["TELEGRAM_TOKEN"], "cid": S["TELEGRAM_CHAT_ID"]
    }
except:
    st.error("Secrets (API Anahtarları) eksik!"); st.stop()

# --- 2. FONKSİYONLAR ---
def send_tg_test():
    url = f"https://api.telegram.org/bot{KEYS['tg']}/sendMessage"
    try:
        requests.post(url, data={"chat_id": KEYS["cid"], "text": "🔔 Bot Testi: Bağlantı Başarılı!"}, timeout=5)
        return True
    except: return False

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'order' not in st.session_state: st.session_state.order = None
if 'manual_proxy' not in st.session_state: st.session_state.manual_proxy = ""

# --- 4. GİRİŞ ---
if not st.session_state.auth:
    st.title("🔐 Giriş Yap")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş") and pwd == KEYS["p"]:
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 5. SIDEBAR (BAKİYE & KONTROL) ---
with st.sidebar:
    st.title("🤖 Kontrol")
    
    # Tiger & Hero Bakiye ve Stok (Hızlı Çekim)
    try:
        t_b = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["t"], "action": "getBalance"}, timeout=5).text
        h_b = requests.get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["h"], "action": "getBalance"}, timeout=5).text
        t_bal = t_b.split(':')[1] if 'ACCESS' in t_b else "0"
        h_bal = h_b.split(':')[1] if 'ACCESS' in h_b else "0"
        
        t_stock = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["t"], "action": "getPrices", "country": "62"}, timeout=5).json().get("62", {})
        h_stock = requests.get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["h"], "action": "getPrices", "country": "62"}, timeout=5).json().get("62", {})
    except:
        t_bal, h_bal, t_stock, h_stock = "Hata", "Hata", {}, {}

    st.metric("🐯 Tiger", f"{t_bal} RUB")
    st.metric("🦸 Hero", f"{h_bal} $")
    
    st.write("---")
    if st.button("🔔 Telegram Botunu Test Et"):
        if send_tg_test(): st.toast("✅ Test mesajı gönderildi!")
        else: st.error("❌ Bot hatası!")
    
    if st.button("🔄 Verileri Yenile"): st.rerun()

# --- 6. ALIM FONKSİYONU (MANUEL PROXY DESTEKLİ) ---
def process_buy(src, svc, country="62"):
    with st.spinner("İşlem yapılıyor..."):
        proxies = None
        # Eğer OnlineSim ise ve proxy girilmişse kullan
        if src == "o" and st.session_state.manual_proxy:
            p_str = st.session_state.manual_proxy.strip()
            proxies = {"http": p_str, "https": p_str}
        
        try:
            if src == "o":
                url = "https://onlinesim.io/api/getNum.php"
                params = {"apikey": KEYS["o"], "service": svc, "country": "90"}
                res = requests.get(url, params=params, proxies=proxies, timeout=15).json()
                if str(res.get("response")) == "1":
                    st.session_state.order = {"id": res["tzid"], "num": res["number"], "src": "o", "name": svc}
                else: st.error(f"Osim Hatası: {res}")
            else:
                base = "https://api.tiger-sms.com/stubs/handler_api.php" if src == "t" else "https://hero-sms.com/stubs/handler_api.php"
                r = requests.get(base, {"api_key": KEYS[src], "action": "getNumber", "service": svc, "country": country}, timeout=10).text
                if "ACCESS" in r:
                    p = r.split(":"); st.session_state.order = {"id": p[1], "num": p[2], "src": src, "name": svc}
                else: st.error(f"Hata: {r}")
        except Exception as e:
            st.error(f"Bağlantı Hatası: {e}")

# --- 7. ANA PANEL ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🦸 Hero", "🔵 OnlineSim"])

with t1:
    st.subheader("Tiger SMS (Endonezya)")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"🍔 Yemeksepeti: **{t_stock.get('yi', {}).get('cost', '-')} RUB**")
        if st.button("T-YEMEK AL", key="t1"): process_buy("t", "yi")
    with c2:
        st.write(f"🚗 Uber: **{t_stock.get('ub', {}).get('cost', '-')} RUB**")
        if st.button("T-UBER AL", key="t2"): process_buy("t", "ub")

with t2:
    st.subheader("Hero SMS (Endonezya)")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"🍔 Yemeksepeti: **{h_stock.get('yi', {}).get('cost', '-')} $**")
        if st.button("H-YEMEK AL", key="h1"): process_buy("h", "yi")
    with c2:
        st.write(f"🚗 Uber: **{h_stock.get('ub', {}).get('cost', '-')} $**")
        if st.button("H-UBER AL", key="h2"): process_buy("h", "ub")

with t3:
    st.subheader("OnlineSim (Türkiye)")
    
    # MANUEL PROXY GİRİŞİ
    st.session_state.manual_proxy = st.text_input(
        "Proxy Girin (Opsiyonel)", 
        placeholder="http://user:pass@ip:port", 
        help="Eğer boş bırakırsanız normal bağlantı denenir. IP ban varsa proxy girin."
    )
    
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🍔 Yemeksepeti (O)", key="o1"): process_buy("o", "yemeksepeti")
    with c2:
        if st.button("🚗 Uber (O)", key="o2"): process_buy("o", "uber")
    with c3:
        if st.button("☕ Espressolab (O)", key="o3"): process_buy("o", "espressolab")

# --- 8. TAKİP ALANI ---
if st.session_state.order:
    ord = st.session_state.order
    st.divider()
    st.success(f"✅ Aktif Numara: +{ord['num']} | Kaynak: {ord['src'].upper()}")
    if st.button("🗑️ Siparişi Temizle"):
        st.session_state.order = None; st.rerun()
