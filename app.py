import streamlit as st
import requests
import time
from fp.fp import FreeProxy

# --- 1. AYARLAR ---
st.set_page_config(page_title="Pro SMS Panel V6.2", layout="wide")

try:
    S = st.secrets
    KEYS = {
        "t": S["TIGER_API_KEY"], "o": S["ONLINESIM_API_KEY"], "h": S["HERO_API_KEY"],
        "p": S["PANEL_SIFRESI"], "tg": S["TELEGRAM_TOKEN"], "cid": S["TELEGRAM_CHAT_ID"]
    }
except:
    st.error("Secrets bulunamadı!"); st.stop()

# --- 2. GELİŞMİŞ PROXY MOTORU ---
def get_working_proxy():
    """Çalışma ihtimali yüksek, hızlı bir proxy bulmaya çalışır."""
    try:
        # timeout=1 ve rand=True ile en hızlı ve rastgele olanı seçer
        return FreeProxy(https=True, rand=True, timeout=0.5).get()
    except:
        return None

def osim_safe_request(url, params):
    """Bağlantı koparsa veya timeout olursa otomatik yeni proxy ile tekrar dener."""
    proxy_url = get_working_proxy()
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    
    try:
        # Timeout süresini 7 saniyeye çıkardık (Proxy yavaşlığı için)
        r = requests.get(url, params=params, proxies=proxies, timeout=7)
        if r.status_code == 200:
            return r.json()
        return {"error": "http_error"}
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ProxyError):
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'order' not in st.session_state: st.session_state.order = None
if 'osim_status' not in st.session_state: st.session_state.osim_status = "Hazır"

# --- 4. GİRİŞ ---
if not st.session_state.auth:
    st.title("🔐 Pro SMS Giriş")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş") and pwd == KEYS["p"]:
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 5. SIDEBAR (AUTO-RETRY MANTIĞI) ---
with st.sidebar:
    st.title("🤖 Kontrol")
    
    # Tiger & Hero (Direkt ve Hızlı)
    try:
        t_b_raw = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["t"], "action": "getBalance"}, timeout=5).text
        h_b_raw = requests.get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["h"], "action": "getBalance"}, timeout=5).text
        t_bal = t_b_raw.split(':')[1] if 'ACCESS' in t_b_raw else '0'
        h_bal = h_b_raw.split(':')[1] if 'ACCESS' in h_b_raw else '0'
    except:
        t_bal, h_bal = "ERR", "ERR"

    # OnlineSim (Proxy ile Sorgulama)
    o_res = osim_safe_request("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["o"]})
    
    if "error" in o_res:
        st.warning("⚠️ Osim Bağlantı Hatası. Yeni Proxy deneniyor...")
        time.sleep(2)
        st.rerun() # Hata varsa otomatik olarak yeni bir Proxy ile sayfayı tazeler
    else:
        osim_bal = str(o_res.get("balance", "0"))
        st.session_state.osim_status = "Aktif"

    st.metric("🐯 Tiger", f"{t_bal} RUB")
    st.metric("🦸 Hero", f"{h_bal} $")
    st.metric("🔵 OnlineSim", f"{osim_bal} $")
    
    if st.button("🔄 Manuel Yenile"): st.rerun()

# --- 6. ANA PANEL ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🦸 Hero", "🔵 OnlineSim"])

def process_order(src, svc):
    with st.spinner(f"{src.upper()} üzerinden işlem yapılıyor..."):
        if src == "o":
            res = osim_safe_request("https://onlinesim.io/api/getNum.php", {"apikey": KEYS["o"], "service": svc, "country": "90"})
            if res.get("response") == "1":
                st.session_state.order = {"id": res["tzid"], "num": res["number"], "src": "o"}
                st.toast("✅ Numara Alındı!")
            else: 
                st.error("Osim Hatası: " + str(res.get("error", "Bilinmeyen Hata")))
        else:
            url = "https://api.tiger-sms.com/stubs/handler_api.php" if src == "t" else "https://hero-sms.com/stubs/handler_api.php"
            try:
                res = requests.get(url, {"api_key": KEYS[src], "action": "getNumber", "service": svc, "country": "62"}, timeout=10).text
                if "ACCESS" in res:
                    p = res.split(":")
                    st.session_state.order = {"id": p[1], "num": p[2], "src": src}
                    st.toast("✅ Numara Alındı!")
                else: st.error("Hata: " + res)
            except: st.error("Bağlantı Hatası!")

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
    st.success(f"✅ Aktif Numara: +{ord['num']} ({ord['src'].upper()})")
    if st.button("🗑️ Siparişi Kapat"):
        st.session_state.order = None
        st.rerun()
