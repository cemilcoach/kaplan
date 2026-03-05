import streamlit as st
import requests
import time
from fp.fp import FreeProxy

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pro SMS Panel V6.1", layout="wide")

try:
    S = st.secrets
    KEYS = {
        "t": S["TIGER_API_KEY"], "o": S["ONLINESIM_API_KEY"], "h": S["HERO_API_KEY"],
        "p": S["PANEL_SIFRESI"], "tg": S["TELEGRAM_TOKEN"], "cid": S["TELEGRAM_CHAT_ID"]
    }
except:
    st.error("Secrets bulunamadı!"); st.stop()

# --- 2. AKILLI PROXY VE API MOTORU ---
def get_fresh_proxy():
    """Çalışan bir HTTPS proxy bulana kadar dener."""
    try:
        return FreeProxy(https=True, rand=True, timeout=1).get()
    except:
        return None

def osim_request(url, params):
    """Sadece OnlineSim için proxy kullanır ve hata alursa sistemi tetikler."""
    p_url = get_fresh_proxy()
    proxies = {"http": p_url, "https": p_url} if p_url else None
    
    try:
        r = requests.get(url, params=params, proxies=proxies, timeout=8)
        return r.json()
    except Exception:
        return {"error": "proxy_failed"}

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'order' not in st.session_state: st.session_state.order = None
if 'osim_bal' not in st.session_state: st.session_state.osim_bal = "Yükleniyor..."

# --- 4. GİRİŞ ---
if not st.session_state.auth:
    st.title("🔐 Pro SMS Giriş")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş") and pwd == KEYS["p"]:
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🤖 Kontrol")
    
    # Tiger & Hero (Direkt bağlantı - Hızlı)
    t_b_raw = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["t"], "action": "getBalance"}).text
    h_b_raw = requests.get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["h"], "action": "getBalance"}).text
    
    # OnlineSim (Proxy ile - Eğer banlıysa otomatik yenile)
    o_res = osim_request("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["o"]})
    
    if "error" in o_res or o_res.get("response") == "error":
        st.warning("🔄 OnlineSim Banlı/Yavaş. Yeni IP deneniyor...")
        time.sleep(1)
        st.rerun() # IP ban varsa veya proxy çalışmadıysa otomatik yenile
    else:
        st.session_state.osim_bal = str(o_res.get("balance", "0"))

    st.metric("🐯 Tiger", f"{t_b_raw.split(':')[1] if 'ACCESS' in t_b_raw else '0'} RUB")
    st.metric("🦸 Hero", f"{h_b_raw.split(':')[1] if 'ACCESS' in h_b_raw else '0'} $")
    st.metric("🔵 OnlineSim", f"{st.session_state.osim_bal} $")
    
    if st.button("🔄 Manuel Yenile"): st.rerun()

# --- 6. ANA PANEL ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🦸 Hero", "🔵 OnlineSim"])

def process_order(src, svc):
    with st.spinner("İşlem yapılıyor..."):
        if src == "o":
            res = osim_request("https://onlinesim.io/api/getNum.php", {"apikey": KEYS["o"], "service": svc, "country": "90"})
            if res.get("response") == "1":
                st.session_state.order = {"id": res["tzid"], "num": res["number"], "src": "o"}
            else: st.error("Osim şu an meşgul, tekrar deneyin.")
        else:
            url = "https://api.tiger-sms.com/stubs/handler_api.php" if src == "t" else "https://hero-sms.com/stubs/handler_api.php"
            res = requests.get(url, {"api_key": KEYS[src], "action": "getNumber", "service": svc, "country": "62"}).text
            if "ACCESS" in res:
                p = res.split(":")
                st.session_state.order = {"id": p[1], "num": p[2], "src": src}

with t1:
    c1, c2 = st.columns(2)
    if c1.button("🍔 Yemeksepeti (T)"): process_order("t", "yi")
    if c2.button("🚗 Uber (T)"): process_order("t", "ub")

with t2:
    c1, c2 = st.columns(2)
    if c1.button("🍔 Yemeksepeti (H)"): process_order("h", "yi")
    if c2.button("🚗 Uber (H)"): process_order("h", "ub")

with t3:
    c1, c2, c3 = st.columns(3)
    if c1.button("🍔 Yemeksepeti (O)"): process_order("o", "yemeksepeti")
    if c2.button("🚗 Uber (O)"): process_order("o", "uber")
    if c3.button("☕ Espressolab (O)"): process_order("o", "espressolab")

# --- 7. TAKİP ---
if st.session_state.order:
    ord = st.session_state.order
    st.divider()
    st.success(f"✅ Aktif: +{ord['num']} ({ord['src'].upper()})")
    if st.button("🗑️ Kapat"): st.session_state.order = None; st.rerun()
