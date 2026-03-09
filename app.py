import streamlit as st
import requests

# --- 1. GÖRSEL VE MOBİL AYARLAR ---
st.set_page_config(page_title="Pro SMS Panel", layout="wide", page_icon="📲")

# Mobil Zoom Engelleyici
st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
    </head>
    <style>
        input, select, textarea { font-size: 16px !important; }
        .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SECRETS KONTROLÜ ---
try:
    S = st.secrets
    KEYS = {
        "t": S["TIGER_API_KEY"],
        "h": S["HERO_API_KEY"],
        "p": S["PANEL_SIFRESI"],
        "tg": S["TELEGRAM_TOKEN"],
        "cid": S["TELEGRAM_CHAT_ID"]
    }
except Exception as e:
    st.error("Secrets bulunamadı! Lütfen ayarları kontrol edin."); st.stop()

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'order' not in st.session_state: st.session_state.order = None

# --- 4. GİRİŞ KONTROLÜ ---
if not st.session_state.auth:
    st.title("🔐 Panel Giriş")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap") and pwd == KEYS["p"]:
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 5. YAN PANEL (BAKİYELER) ---
with st.sidebar:
    st.title("🤖 Bakiye Kontrol")
    try:
        t_res = requests.get(f"https://api.tiger-sms.com/stubs/handler_api.php?api_key={KEYS['t']}&action=getBalance", timeout=10).text
        t_bal = t_res.split(':')[1] if 'ACCESS' in t_res else "0"
        
        h_res = requests.get(f"https://hero-sms.com/stubs/handler_api.php?api_key={KEYS['h']}&action=getBalance", timeout=10).text
        h_bal = h_res.split(':')[1] if 'ACCESS' in h_res else "0"
    except:
        t_bal, h_bal = "ERR", "ERR"

    st.metric("🐯 Tiger SMS", f"{t_bal} ₽")
    st.metric("🦸 Hero SMS", f"{h_bal} $")
    
    st.divider()
    if st.button("🔄 Verileri Yenile"): st.rerun()

# --- 6. NUMARA ALIM FONKSİYONU ---
def buy_num(src, svc, country, name):
    with st.spinner(f"{name} numarası alınıyor..."):
        base = "https://api.tiger-sms.com/stubs/handler_api.php" if src == "t" else "https://hero-sms.com/stubs/handler_api.php"
        url = f"{base}?api_key={KEYS[src]}&action=getNumber&service={svc}&country={country}"
        
        try:
            res = requests.get(url, timeout=15).text
            if "ACCESS" in res:
                p = res.split(":")
                st.session_state.order = {"id": p[1], "num": p[2], "src": src, "name": name, "country": country}
                st.toast(f"✅ {name} (TR) alındı!")
            else:
                st.error(f"Hata: {res} (Stok olmayabilir)")
        except:
            st.error("Bağlantı hatası!")

# --- 7. ANA PANEL ---
st.title("🇹🇷 Multi-SMS Panel")
tab1, tab2 = st.tabs(["🐯 Tiger SMS (Genel)", "🦸 Hero SMS (Türkiye)"])

with tab1:
    st.subheader("Tiger SMS")
    st.info("Bu sekme varsayılan Endonezya (62) numarası alır.")
    c1, c2 = st.columns(2)
    if c1.button("🍔 Tiger Yemeksepeti"): buy_num("t", "yi", "62", "Yemeksepeti")
    if c2.button("🚗 Tiger Uber"): buy_num("t", "ub", "62", "Uber")

with tab2:
    st.subheader("Hero SMS Türkiye")
    st.warning("Bu sekme sadece Türkiye (90) numarası talep eder.")
    c1, c2 = st.columns(2)
    if c1.button("🍔 Hero Yemeksepeti (TR)"): buy_num("h", "yi", "90", "Yemeksepeti")
    if c2.button("🚗 Hero Uber (TR)"): buy_num("h", "ub", "90", "Uber")

# --- 8. SİPARİŞ TAKİP ---
if st.session_state.order:
    ord = st.session_state.order
    st.divider()
    st.success(f"✅ **Aktif {ord['name']} Numarası:** `+{ord['num']}`")
    st.write(f"📍 Ülke Kodu: {ord['country']} | Kaynak: {ord['src'].upper()}")
    
    if st.button("🗑️ Siparişi Kapat"):
        st.session_state.order = None; st.rerun()
