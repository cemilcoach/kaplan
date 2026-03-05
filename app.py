import streamlit as st
import requests
import time
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="SMS Panel V4.2 - Error Handling", layout="wide", page_icon="🇹🇷")

try:
    S = st.secrets
    KEYS = {
        "tiger": S["TIGER_API_KEY"],
        "osim": S["ONLINESIM_API_KEY"],
        "hero": S["HERO_API_KEY"],
        "pass": S["PANEL_SIFRESI"],
        "tg_token": S["TELEGRAM_TOKEN"],
        "tg_chat": S["TELEGRAM_CHAT_ID"]
    }
except Exception as e:
    st.error(f"Secrets Hatası: {e}")
    st.stop()

# --- 2. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'orders' not in st.session_state: st.session_state.orders = []
if 'balances' not in st.session_state: st.session_state.balances = {"tiger": "0", "osim": "0", "hero": "0"}
if 'stocks' not in st.session_state: st.session_state.stocks = {"tiger": {}, "osim": {}, "hero": {}}

# --- 3. GÜVENLİ API ÇEKİRDEĞİ ---
def safe_get(url, params=None, is_json=False, timeout=5):
    """Bağlantı hatalarında uygulamayı çökertmez, boş veri döner."""
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json() if is_json else r.text
        return {} if is_json else "ERROR"
    except Exception:
        return {} if is_json else "TIMEOUT"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{KEYS['tg_token']}/sendMessage"
    # Telegram hatası paneli yavaşlatmasın diye timeout çok kısa
    try: requests.post(url, data={"chat_id": str(KEYS['tg_chat']), "text": msg, "parse_mode": "HTML"}, timeout=2)
    except: pass

# --- 4. VERİ GÜNCELLEME (Korumalı) ---
def refresh_panel():
    with st.spinner("Servislerle bağlantı kuruluyor..."):
        # Tiger
        t_b = safe_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getBalance"})
        st.session_state.balances["tiger"] = t_b.split(":")[1] if "ACCESS" in t_b else "OFFLINE"
        
        # Hero
        h_b = safe_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getBalance"})
        st.session_state.balances["hero"] = h_b.split(":")[1] if "ACCESS" in h_b else "OFFLINE"

        # OnlineSim (Hatanın Kaynağı Burasıydı)
        o_b_raw = safe_get("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["osim"]}, is_json=True, timeout=8)
        if isinstance(o_b_raw, dict) and "balance" in o_b_raw:
            st.session_state.balances["osim"] = str(o_b_raw["balance"])
        else:
            st.session_state.balances["osim"] = "OFFLINE"

        # Stoklar
        try:
            t_s = safe_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getPrices", "country": "62"}, is_json=True)
            st.session_state.stocks["tiger"] = t_s.get("62", {}) if isinstance(t_s, dict) else {}
            
            h_s = safe_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getPrices", "country": "62"}, is_json=True)
            st.session_state.stocks["hero"] = h_s.get("62", {}) if isinstance(h_s, dict) else {}
            
            o_s = safe_get("https://onlinesim.io/api/getTariffs.php", {"apikey": KEYS["osim"], "country": "90"}, is_json=True, timeout=8)
            st.session_state.stocks["osim"] = o_s.get("90", {}).get("services", {}) if "90" in o_s else o_s.get("services", {})
        except:
            pass

# --- 5. GİRİŞ ---
if not st.session_state.auth:
    st.title("🔒 Pro SMS Panel")
    with st.form("login"):
        pwd = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş", use_container_width=True):
            if pwd == KEYS["pass"]:
                st.session_state.auth = True
                refresh_panel()
                st.rerun()
            else: st.error("Hatalı Şifre!")
    st.stop()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🤖 Kontrol")
    st.metric("🐯 Tiger", f"{st.session_state.balances['tiger']} RUB")
    st.metric("🔵 OnlineSim", f"{st.session_state.balances['osim']} $")
    st.metric("🦸 Hero", f"{st.session_state.balances['hero']} $")
    if st.button("🔄 Verileri Yenile", use_container_width=True):
        refresh_panel()
        st.rerun()
    canli = st.toggle("🟢 Takip Aktif", value=True)

# --- 7. ARAYÜZ VE TAKİP ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

# (Alım ve Takip fonksiyonları V4.1 ile aynı kalacak şekilde buraya eklenmeli)
# Not: Yavaşlamayı önlemek için buy() fonksiyonunda da safe_get kullanılmalı.

def buy(source, s_name, s_code, country):
    res_id, res_num = None, None
    if source == "tiger":
        r = safe_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getNumber", "service": s_code, "country": country})
        if "ACCESS" in r: parts = r.split(":"); res_id, res_num = parts[1], parts[2]
    elif source == "hero":
        r = safe_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getNumber", "service": s_code, "country": country})
        if "ACCESS" in r: parts = r.split(":"); res_id, res_num = parts[1], parts[2]
    elif source == "osim":
        r = safe_get("https://onlinesim.io/api/getNum.php", {"apikey": KEYS["osim"], "service": s_code, "country": country}, is_json=True)
        if str(r.get("response")) == "1": res_id, res_num = r.get("tzid"), r.get("number")

    if res_id and res_num:
        st.session_state.orders.append({"id":res_id, "phone":res_num, "name":s_name, "src":source, "time":time.time(), "code":None})
        st.toast("✅ Başarılı!")
    else: st.error(f"Hata: {source} şu an yanıt vermiyor.")

# ... (Tab içerikleri ve Takip Döngüsü V4.1'deki gibi devam eder)
