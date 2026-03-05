import streamlit as st
import requests
import time

# --- 1. GÖRSEL VE MOBİL AYARLAR ---
st.set_page_config(page_title="Pro SMS Panel V6.8", layout="wide", page_icon="📲")

# Mobil Zoom Engelleyici
st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
    </head>
    <style>
        input, select, textarea { font-size: 16px !important; }
        .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SECRETS KONTROLÜ ---
try:
    S = st.secrets
    KEYS = {
        "t": S["TIGER_API_KEY"], "o": S["ONLINESIM_API_KEY"], "h": S["HERO_API_KEY"],
        "p": S["PANEL_SIFRESI"], "tg": S["TELEGRAM_TOKEN"], "cid": S["TELEGRAM_CHAT_ID"]
    }
    GAS_URL = S["GAS_URL"]
except Exception as e:
    st.error(f"Secrets Ayarlarında Hata Var: {e}"); st.stop()

# --- 3. ÖZEL İSTEK MOTORU (HİBRİT) ---
def smart_request(target_url, use_proxy=False):
    """Sadece istenirse Google Proxy kullanır, yoksa direkt bağlanır."""
    if use_proxy:
        proxied_url = f"{GAS_URL}?url={target_url}"
        try:
            r = requests.get(proxied_url, timeout=25)
            return r.json() if "onlinesim" in target_url else r.text
        except:
            return {"error": "proxy_error"}
    else:
        # Direkt ve hızlı bağlantı (Tiger & Hero için)
        try:
            r = requests.get(target_url, timeout=10)
            return r.json() if "json" in target_url else r.text
        except:
            return "ERROR"

# --- 4. GİRİŞ KONTROLÜ ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'order' not in st.session_state: st.session_state.order = None

if not st.session_state.auth:
    st.title("🔐 Panel Giriş")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap") and pwd == KEYS["p"]:
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 5. SIDEBAR (BAKİYELER) ---
with st.sidebar:
    st.title("🤖 Bakiye Durumu")
    
    # TIGER & HERO (Direkt - Hızlı)
    t_b_url = f"https://api.tiger-sms.com/stubs/handler_api.php?api_key={KEYS['t']}&action=getBalance"
    h_b_url = f"https://hero-sms.com/stubs/handler_api.php?api_key={KEYS['h']}&action=getBalance"
    
    t_b_raw = smart_request(t_b_url, use_proxy=False)
    h_b_raw = smart_request(h_b_url, use_proxy=False)
    
    # ONLINESIM (Sadece bu Proxy ile)
    osim_url = f"https://onlinesim.io/api/getBalance.php?apikey={KEYS['o']}"
    o_res = smart_request(osim_url, use_proxy=True)
    
    st.metric("🐯 Tiger", f"{t_b_raw.split(':')[1] if 'ACCESS' in str(t_b_raw) else '0'} ₽")
    st.metric("🦸 Hero", f"{h_b_raw.split(':')[1] if 'ACCESS' in str(h_b_raw) else '0'} $")
    st.metric("🔵 OnlineSim", f"{o_res.get('balance', 'IP BAN')} $")
    
    st.divider()
    if st.button("🔄 Verileri Yenile"): st.rerun()

# --- 6. ANA PANEL (SEKMELER) ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🦸 Hero", "🔵 OnlineSim"])

def buy_process(src, svc):
    with st.spinner(f"{src.upper()} işlemi başlatılıyor..."):
        if src == "o":
            # Osim için Google Proxy kullanılıyor
            url = f"https://onlinesim.io/api/getNum.php?apikey={KEYS['o']}&service={svc}&country=90"
            res = smart_request(url, use_proxy=True)
            if str(res.get("response")) == "1":
                st.session_state.order = {"id": res["tzid"], "num": res["number"], "src": "o"}
            else: st.error("Osim Hatası: Stok yok veya Proxy limiti.")
        else:
            # Tiger & Hero için Direkt bağlantı
            base = "https://api.tiger-sms.com/stubs/handler_api.php" if src == "t" else "https://hero-sms.com/stubs/handler_api.php"
            res = smart_request(f"{base}?api_key={KEYS[src]}&action=getNumber&service={svc}&country=62", use_proxy=False)
            if "ACCESS" in str(res):
                p = res.split(":"); st.session_state.order = {"id": p[1], "num": p[2], "src": src}
            else: st.error(f"Hata: {res}")

with t1:
    st.subheader("Tiger SMS (Endonezya)")
    c1, c2 = st.columns(2)
    if c1.button("🍔 Yemeksepeti (T)"): buy_process("t", "yi")
    if c2.button("🚗 Uber (T)"): buy_process("t", "ub")

with t2:
    st.subheader("Hero SMS (Endonezya)")
    c1, c2 = st.columns(2)
    if c1.button("🍔 Yemeksepeti (H)"): buy_process("h", "yi")
    if c2.button("🚗 Uber (H)"): buy_process("h", "ub")

with t3:
    st.subheader("OnlineSim (Türkiye - Google Proxy)")
    st.info("Bu sekmedeki işlemler Google sunucuları üzerinden güvenli şekilde yapılır.")
    c1, c2, c3 = st.columns(3)
    if c1.button("🍔 Yemek (O)"): buy_process("o", "yemeksepeti")
    if c2.button("🚗 Uber (O)"): buy_process("o", "uber")
    if c3.button("☕ Espresso (O)"): buy_process("o", "espressolab")

# --- 7. SİPARİŞ TAKİP ---
if st.session_state.order:
    ord = st.session_state.order
    st.divider()
    st.success(f"✅ Aktif Numara: +{ord['num']} ({ord['src'].upper()})")
    if st.button("🗑️ Siparişi Kapat"):
        st.session_state.order = None; st.rerun()
