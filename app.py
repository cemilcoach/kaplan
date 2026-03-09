import streamlit as st
import requests

# --- 1. GÖRSEL VE MOBİL AYARLAR ---
st.set_page_config(page_title="Pro SMS Panel", layout="wide", page_icon="📲")

# Mobil Zoom Engelleyici ve Şık Butonlar
st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
    </head>
    <style>
        input, select, textarea { font-size: 16px !important; }
        .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { 
            height: 50px; white-space: pre-wrap; background-color: #161b22; 
            border-radius: 10px 10px 0 0; color: white;
        }
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
    st.error("Secrets eksik! Lütfen API anahtarlarını kontrol edin."); st.stop()

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

# --- 5. SIDEBAR (BAKİYELER) ---
with st.sidebar:
    st.title("🤖 Bakiye Kontrol")
    
    try:
        # Tiger Bakiye
        t_res = requests.get(f"https://api.tiger-sms.com/stubs/handler_api.php?api_key={KEYS['t']}&action=getBalance", timeout=10).text
        t_bal = t_res.split(':')[1] if 'ACCESS' in t_res else "0"
        
        # Hero Bakiye
        h_res = requests.get(f"https://hero-sms.com/stubs/handler_api.php?api_key={KEYS['h']}&action=getBalance", timeout=10).text
        h_bal = h_res.split(':')[1] if 'ACCESS' in h_res else "0"
    except:
        t_bal, h_bal = "ERR", "ERR"

    st.metric("🐯 Tiger SMS", f"{t_bal} ₽")
    st.metric("🦸 Hero SMS", f"{h_bal} $")
    
    st.divider()
    if st.button("🔄 Verileri Yenile"): st.rerun()
    
    if st.button("🔔 Telegram Test"):
        test_url = f"https://api.telegram.org/bot{KEYS['tg']}/sendMessage"
        requests.post(test_url, data={"chat_id": KEYS["cid"], "text": "✅ Panel Telegram bağlantısı aktif!"})
        st.toast("Test mesajı gönderildi!")

# --- 6. ALIM FONKSİYONU ---
def process_buy(src, svc, name):
    with st.spinner(f"{name} numarası alınıyor..."):
        # Tiger Endonezya (62), Hero Türkiye (90) veya Endonezya (62) tercih edilebilir.
        # İsteğine göre burayı 90 (TR) veya 62 (ID) yapabiliriz. Şimdilik 62 (En ucuz) olarak ayarlandı.
        country = "62" 
        base = "https://api.tiger-sms.com/stubs/handler_api.php" if src == "t" else "https://hero-sms.com/stubs/handler_api.php"
        
        url = f"{base}?api_key={KEYS[src]}&action=getNumber&service={svc}&country={country}"
        try:
            res = requests.get(url, timeout=15).text
            if "ACCESS" in res:
                p = res.split(":")
                st.session_state.order = {"id": p[1], "num": p[2], "src": src, "name": name}
                st.toast(f"✅ {name} numarası alındı!")
            else:
                st.error(f"Hata: {res}")
        except:
            st.error("Bağlantı hatası!")

# --- 7. ANA PANEL ---
st.title("📲 SMS Tedarik Paneli")
tab1, tab2 = st.tabs(["🐯 Tiger SMS", "🦸 Hero SMS"])

with tab1:
    st.subheader("Tiger SMS Servisleri")
    c1, c2 = st.columns(2)
    if c1.button("🍔 Yemeksepeti (T)"): process_buy("t", "yi", "Yemeksepeti")
    if c2.button("🚗 Uber (T)"): process_buy("t", "ub", "Uber")

with tab2:
    st.subheader("Hero SMS Servisleri")
    c1, c2 = st.columns(2)
    if c1.button("🍔 Yemeksepeti (H)"): process_buy("h", "yi", "Yemeksepeti")
    if c2.button("🚗 Uber (H)"): process_buy("h", "ub", "Uber")

# --- 8. SİPARİŞ TAKİP ---
if st.session_state.order:
    ord = st.session_state.order
    st.divider()
    st.success(f"✅ **Aktif {ord['name']} Numarası:** `+{ord['num']}` ({ord['src'].upper()})")
    st.info("📩 Kod geldiğinde otomatik olarak Telegram botunuza gönderilecektir.")
    
    if st.button("🗑️ Siparişi Kapat"):
        st.session_state.order = None; st.rerun()
