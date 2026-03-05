import streamlit as st
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

# --- 1. AYARLAR ---
st.set_page_config(page_title="SMS Panel V4.5 - Debug", layout="wide", page_icon="🔍")

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

# --- 2. DURUM YÖNETİMİ ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'orders' not in st.session_state: st.session_state.orders = []
if 'balances' not in st.session_state: st.session_state.balances = {}
if 'stocks' not in st.session_state: st.session_state.stocks = {}
if 'osim_debug' not in st.session_state: st.session_state.osim_debug = "Henüz veri çekilmedi."

# --- 3. API ÇEKİRDEĞİ ---
def safe_get(url, params=None, is_json=False, timeout=10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json() if is_json else r.text
        return {"error": f"HTTP {r.status_code}", "raw": r.text} if is_json else f"ERR_{r.status_code}"
    except Exception as e:
        return {"error": str(e)} if is_json else f"TIMEOUT_{str(e)[:20]}"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{KEYS['tg_token']}/sendMessage"
    try: requests.post(url, data={"chat_id": str(KEYS['tg_chat']), "text": msg, "parse_mode": "HTML"}, timeout=3)
    except: pass

# --- 4. VERİ ÇEKME (DEBUG LOGLU) ---
def fetch_all_data():
    with st.spinner("Tüm servisler sorgulanıyor..."):
        urls = {
            "t_bal": ("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getBalance"}, False),
            "h_bal": ("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getBalance"}, False),
            "o_bal": ("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["osim"]}, True),
            "t_stock": ("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getPrices", "country": "62"}, True),
            "h_stock": ("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getPrices", "country": "62"}, True),
            "o_stock": ("https://onlinesim.io/api/getTariffs.php", {"apikey": KEYS["osim"], "country": "90"}, True)
        }

        with ThreadPoolExecutor(max_workers=6) as executor:
            results = {k: executor.submit(safe_get, u, p, j).result() for k, (u, p, j) in urls.items()}

        # DEBUG KAYDI (Hata buradaysa yakalayacağız)
        st.session_state.osim_debug = {
            "Bakiye Yanıtı": results["o_bal"],
            "Tarife Yanıtı (İlk 500 karakter)": str(results["o_stock"])[:500]
        }

        # BAKİYE İŞLEME
        st.session_state.balances = {
            "tiger": results["t_bal"].split(":")[1] if "ACCESS" in results["t_bal"] else "OFFLINE",
            "hero": results["h_bal"].split(":")[1] if "ACCESS" in results["h_bal"] else "OFFLINE",
            "osim": str(results["o_bal"].get("balance", "OFFLINE")) if isinstance(results["o_bal"], dict) else "OFFLINE"
        }
        
        # STOK İŞLEME
        st.session_state.stocks["tiger"] = results["t_stock"].get("62", {}) if isinstance(results["t_stock"], dict) else {}
        st.session_state.stocks["hero"] = results["h_stock"].get("62", {}) if isinstance(results["h_stock"], dict) else {}
        
        o_data = results["o_stock"]
        if isinstance(o_data, dict):
            # Hiyerarşik kontrol (Default Country Turkey ayarı için)
            if "90" in o_data:
                st.session_state.stocks["osim"] = o_data["90"].get("services", {})
            else:
                st.session_state.stocks["osim"] = o_data.get("services", {})
        else:
            st.session_state.stocks["osim"] = {}

# --- 5. GİRİŞ ---
if not st.session_state.auth:
    st.title("🔒 Pro SMS Panel")
    with st.form("login"):
        if st.form_submit_button("Giriş Yap", use_container_width=True) and st.text_input("Şifre", type="password") == KEYS["pass"]:
            st.session_state.auth = True
            st.rerun()
    st.stop()

if not st.session_state.balances:
    fetch_all_data()
    st.rerun()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🤖 Kontrol")
    st.metric("🐯 Tiger", f"{st.session_state.balances.get('tiger')} RUB")
    st.metric("🔵 OnlineSim", f"{st.session_state.balances.get('osim')} $")
    st.metric("🦸 Hero", f"{st.session_state.balances.get('hero')} $")
    if st.button("🔄 Verileri Yenile", use_container_width=True):
        fetch_all_data(); st.rerun()
    canli = st.toggle("🟢 Canlı Takip", value=True)

# --- 7. ARAYÜZ ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

# Veri Atamaları
s_t, s_o, s_h = st.session_state.stocks["tiger"], st.session_state.stocks["osim"], st.session_state.stocks["hero"]

def buy(source, s_name, s_code, country):
    with st.spinner("İşlem yapılıyor..."):
        if source == "osim":
            r = safe_get("https://onlinesim.io/api/getNum.php", {"apikey": KEYS["osim"], "service": s_code, "country": "90"}, is_json=True)
            if str(r.get("response")) == "1":
                st.session_state.orders.append({"id":r['tzid'], "phone":r['number'], "name":s_name, "src":"osim", "time":time.time(), "code":None})
                st.toast("✅ Alındı!")
                st.rerun()
            else: st.error(f"Osim Hatası: {r}")
        # (Tiger ve Hero alım kodları buraya eklenebilir)

with t1:
    st.subheader("Tiger Servisleri")
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {s_t.get('yi',{}).get('cost','-')} RUB")
    c2.write(f"🚗 Uber: {s_t.get('ub',{}).get('cost','-')} RUB")

with t2:
    st.subheader("OnlineSim Servisleri")
    c1, c2, c3 = st.columns(3)
    def find_o(slug): return s_o.get(slug, {}) or next((v for k,v in s_o.items() if v.get('slug')==slug), {})
    
    oy, ou, oe = find_o("yemeksepeti"), find_o("uber"), find_o("espressolab")
    c1.write(f"🍔 Yemek: {oy.get('price','-')} $")
    if c1.button("AL", key="o1"): buy("osim", "Yemeksepeti", "yemeksepeti", "90")
    c2.write(f"🚗 Uber: {ou.get('price','-')} $")
    if c2.button("AL", key="o2"): buy("osim", "Uber", "uber", "90")
    c3.write(f"☕ Kahve: {oe.get('price','-')} $")
    if c3.button("AL", key="o3"): buy("osim", "Espressolab", "espressolab", "90")
    
    st.divider()
    with st.expander("🛠️ OnlineSim Debug Modu (Hata Ayıklama)"):
        st.write("Eğer üstteki butonlarda fiyat/stok yoksa burayı kontrol edin:")
        st.json(st.session_state.osim_debug)

with t3:
    st.subheader("Hero Servisleri")
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {s_h.get('yi',{}).get('cost','-')} $")
    c2.write(f"🚗 Uber: {s_h.get('ub',{}).get('cost','-')} $")

# --- 8. TAKİP ---
# (Önceki sürümlerdeki takip döngüsü buraya gelmeli)
