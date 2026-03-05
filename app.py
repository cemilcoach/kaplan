import streamlit as st
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

# --- 1. AYARLAR ---
st.set_page_config(page_title="SMS Panel V4.6 - Anti-Freeze", layout="wide", page_icon="🛡️")

try:
    S = st.secrets
    KEYS = {
        "tiger": S["TIGER_API_KEY"], "osim": S["ONLINESIM_API_KEY"], "hero": S["HERO_API_KEY"],
        "pass": S["PANEL_SIFRESI"], "tg_token": S["TELEGRAM_TOKEN"], "tg_chat": S["TELEGRAM_CHAT_ID"]
    }
except Exception as e:
    st.error("Secrets Eksik!"); st.stop()

# --- 2. SESSION STATE ---
for k, v in {"auth": False, "orders": [], "balances": {}, "stocks": {}, "osim_err": ""}.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 3. GÜVENLİ VE HIZLI ÇEKİRDEK ---
def fetch_api(url, params, is_json=False, timeout=3): # Timeout 3 saniyeye çekildi (Donmayı önler)
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200: return r.json() if is_json else r.text
        return "ERR_HTTP"
    except: return "TIMEOUT"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{KEYS['tg_token']}/sendMessage"
    try: requests.post(url, data={"chat_id": str(KEYS['tg_chat']), "text": msg, "parse_mode": "HTML"}, timeout=2)
    except: pass

# --- 4. PARALEL VERİ ÇEKME (HIZLI) ---
def refresh_data():
    urls = {
        "t_b": ("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getBalance"}, False),
        "h_b": ("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getBalance"}, False),
        "o_b": ("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["osim"]}, True),
        "t_s": ("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getPrices", "country": "62"}, True),
        "h_s": ("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getPrices", "country": "62"}, True),
        "o_s": ("https://onlinesim.io/api/getTariffs.php", {"apikey": KEYS["osim"], "country": "90"}, True)
    }
    
    with ThreadPoolExecutor(max_workers=6) as ex:
        res = {k: ex.submit(fetch_api, u, p, j, (8 if "osim" in k or "o_" in k else 3)).result() for k, (u, p, j) in urls.items()}

    # Bakiyeler
    st.session_state.balances = {
        "tiger": res["t_b"].split(":")[1] if "ACCESS" in res["t_b"] else "OFFLINE",
        "hero": res["h_b"].split(":")[1] if "ACCESS" in res["h_b"] else "OFFLINE",
        "osim": str(res["o_b"].get("balance", "OFFLINE")) if isinstance(res["o_b"], dict) else "OFFLINE"
    }
    
    # Stoklar
    st.session_state.stocks["tiger"] = res["t_s"].get("62", {}) if isinstance(res["t_s"], dict) else {}
    st.session_state.stocks["hero"] = res["h_s"].get("62", {}) if isinstance(res["h_s"], dict) else {}
    
    # OnlineSim Özel (Hiyerarşi Fix)
    o_data = res["o_s"]
    if isinstance(o_data, dict):
        st.session_state.stocks["osim"] = o_data.get("90", {}).get("services", {}) or o_data.get("services", {})
    else: st.session_state.stocks["osim"] = {}

# --- 5. GİRİŞ ---
if not st.session_state.auth:
    with st.form("l"):
        if st.form_submit_button("Giriş") and st.text_input("Şifre", type="password") == KEYS["pass"]:
            st.session_state.auth = True; refresh_data(); st.rerun()
    st.stop()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🤖 Kontrol")
    b = st.session_state.balances
    st.metric("🐯 Tiger", f"{b.get('tiger')} RUB")
    st.metric("🦸 Hero", f"{b.get('hero')} $")
    st.metric("🔵 OnlineSim", f"{b.get('osim')} $")
    if st.button("🔄 Verileri Yenile"): refresh_data(); st.rerun()
    if st.button("🔔 Bot Test"): send_tg("Bot Aktif!"); st.success("Ok")
    canli = st.toggle("🟢 Takip", value=True)

# --- 7. ANA PANEL ---
st.title("🇹🇷 Multi-SMS Panel")
tabs = st.tabs(["🐯 Tiger", "🦸 Hero", "🔵 OnlineSim"])

# TIGER
with tabs[0]:
    s = st.session_state.stocks["tiger"]
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {s.get('yi',{}).get('cost','-')} RUB"); c2.write(f"🚗 Uber: {s.get('ub',{}).get('cost','-')} RUB")

# HERO
with tabs[1]:
    s = st.session_state.stocks["hero"]
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {s.get('yi',{}).get('cost','-')} $"); c2.write(f"🚗 Uber: {s.get('ub',{}).get('cost','-')} $")

# ONLINESIM (Sorunlu Bölge)
with tabs[2]:
    if st.session_state.balances["osim"] == "OFFLINE":
        st.error("⚠️ OnlineSim sunucusuna ulaşılamıyor. (Bağlantı Zaman Aşımı)")
    s = st.session_state.stocks["osim"]
    def get_o(sl): return s.get(sl, {}) or next((v for k,v in s.items() if v.get('slug')==sl), {})
    c1, c2, c3 = st.columns(3)
    c1.write(f"🍔 Yemek: {get_o('yemeksepeti').get('price','-')} $")
    c2.write(f"🚗 Uber: {get_o('uber').get('price','-')} $")
    c3.write(f"☕ Kahve: {get_o('espressolab').get('price','-')} $")

# --- 8. TAKİP ---
st.divider()
st.subheader("📋 İşlemler")
to_rem = []
for o in st.session_state.orders:
    elap = int(time.time() - o['time'])
    if elap > 135 and o['code'] is None: to_rem.append(o['id']); continue
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        # Kod Kontrol Mantığı (Tiger/Hero/Osim) buraya gelecek...
        c1.write(f"**{o['name']}** ({o['src'].upper()}) - {elap}s")
        c2.code(f"+{o['phone']}")
        if st.button("🗑️", key=f"d{o['id']}"): to_rem.append(o['id'])

if to_rem:
    st.session_state.orders = [x for x in st.session_state.orders if x['id'] not in to_rem]; st.rerun()
if canli and st.session_state.orders:
    time.sleep(2); st.rerun()
