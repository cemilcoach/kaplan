import streamlit as st
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

# --- 1. AYARLAR ---
st.set_page_config(page_title="SMS Panel V4.4 - Fix", layout="wide", page_icon="🚀")

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

# --- 3. API ÇEKİRDEĞİ ---
def safe_get(url, params=None, is_json=False, timeout=8):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json() if is_json else r.text
    except: pass
    return {} if is_json else "OFFLINE"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{KEYS['tg_token']}/sendMessage"
    try: requests.post(url, data={"chat_id": str(KEYS['tg_chat']), "text": msg, "parse_mode": "HTML"}, timeout=3)
    except: pass

# --- 4. VERİ ÇEKME (ONLINESIM ODAKLI GÜNCEL) ---
def fetch_all_data():
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

    # BAKİYE İŞLEME
    st.session_state.balances = {
        "tiger": results["t_bal"].split(":")[1] if "ACCESS" in results["t_bal"] else "OFFLINE",
        "hero": results["h_bal"].split(":")[1] if "ACCESS" in results["h_bal"] else "OFFLINE",
        "osim": str(results["o_bal"].get("balance", "0")) if isinstance(results["o_bal"], dict) else "OFFLINE"
    }
    
    # ONLINESIM STOK İŞLEME (Default Country Ayarı Fix)
    o_data = results["o_stock"]
    # Eğer API 90 parametresine rağmen datayı 90 anahtarı içine koymadıysa diye kontrol ekliyoruz
    if isinstance(o_data, dict):
        if "90" in o_data:
            st.session_state.stocks["osim"] = o_data["90"].get("services", {})
        else:
            st.session_state.stocks["osim"] = o_data.get("services", o_data)
    else:
        st.session_state.stocks["osim"] = {}

    st.session_state.stocks["tiger"] = results["t_stock"].get("62", {}) if isinstance(results["t_stock"], dict) else {}
    st.session_state.stocks["hero"] = results["h_stock"].get("62", {}) if isinstance(results["h_stock"], dict) else {}

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
    if st.button("🔔 Botu Test Et", use_container_width=True):
        send_tg(f"🚀 Test\nTiger: {st.session_state.balances['tiger']} RUB\nOSim: {st.session_state.balances['osim']} $\nHero: {st.session_state.balances['hero']} $")
    canli = st.toggle("🟢 Canlı Takip", value=True)

# --- 7. ALIM FONKSİYONU ---
def buy(source, s_name, s_code, country):
    res_id, res_num = None, None
    if source == "tiger":
        r = safe_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getNumber", "service": s_code, "country": country})
        if "ACCESS" in r: parts = r.split(":"); res_id, res_num = parts[1], parts[2]
    elif source == "hero":
        r = safe_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getNumber", "service": s_code, "country": country})
        if "ACCESS" in r: parts = r.split(":"); res_id, res_num = parts[1], parts[2]
    elif source == "osim":
        # Default Country ayarı varsa bile country=90'ı zorunlu gönderiyoruz
        r = safe_get("https://onlinesim.io/api/getNum.php", {"apikey": KEYS["osim"], "service": s_code, "country": "90"}, is_json=True)
        if str(r.get("response")) == "1": res_id, res_num = r.get("tzid"), r.get("number")

    if res_id and res_num:
        st.session_state.orders.append({"id":res_id, "phone":res_num, "name":s_name, "src":source, "time":time.time(), "code":None})
        st.toast("✅ Numara Alındı!")
        st.rerun()
    else: st.error(f"❌ {source.upper()} yanıt vermedi veya stok yok.")

# --- 8. ANA PANEL ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

s_t = st.session_state.stocks["tiger"]
s_o = st.session_state.stocks["osim"]
s_h = st.session_state.stocks["hero"]

with t1:
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {s_t.get('yi',{}).get('cost','-')} RUB")
    if c1.button("T-YEMEK AL", key="t1"): buy("tiger", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {s_t.get('ub',{}).get('cost','-')} RUB")
    if c2.button("T-UBER AL", key="t2"): buy("tiger", "Uber", "ub", "62")

with t2:
    c1, c2, c3 = st.columns(3)
    # OnlineSim araması (Esnek arama)
    def find_osim(slug):
        return s_o.get(slug, {}) or next((v for k,v in s_o.items() if v.get('slug')==slug), {})
    
    oy, ou, oe = find_osim("yemeksepeti"), find_osim("uber"), find_osim("espressolab")
    c1.write(f"🍔 Yemek: {oy.get('price','-')} $")
    if c1.button("O-YEMEK AL", key="o1"): buy("osim", "Yemeksepeti", "yemeksepeti", "90")
    c2.write(f"🚗 Uber: {ou.get('price','-')} $")
    if c2.button("O-UBER AL", key="o2"): buy("osim", "Uber", "uber", "90")
    c3.write(f"☕ Kahve: {oe.get('price','-')} $")
    if c3.button("O-KAHVE AL", key="o3"): buy("osim", "Espressolab", "espressolab", "90")

with t3:
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {s_h.get('yi',{}).get('cost','-')} $")
    if c1.button("H-YEMEK AL", key="h1"): buy("hero", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {s_h.get('ub',{}).get('cost','-')} $")
    if c2.button("H-UBER AL", key="h2"): buy("hero", "Uber", "ub", "62")

# --- 9. TAKİP SİSTEMİ ---
st.divider()
to_rem = []
for o in st.session_state.orders:
    elap = int(time.time() - o['time'])
    if elap > 135 and o['code'] is None:
        if o['src'] == "tiger": safe_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "setStatus", "id": o['id'], "status": 8})
        elif o['src'] == "hero": safe_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "setStatus", "id": o['id'], "status": 8})
        else: safe_get("https://onlinesim.io/api/setOperationRevise.php", {"apikey": KEYS["osim"], "tzid": o['id']})
        to_rem.append(o['id']); continue

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        if o['code'] is None:
            if o['src'] == "tiger":
                r = safe_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getStatus", "id": o['id']})
                if "STATUS_OK" in r: o['code'] = r.split(":")[1]
            elif o['src'] == "hero":
                r = safe_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getStatus", "id": o['id']})
                if "STATUS_OK" in r: o['code'] = r.split(":")[1]
            elif o['src'] == "osim":
                r = safe_get("https://onlinesim.io/api/getState.php", {"apikey": KEYS["osim"], "tzid": o['id']}, is_json=True)
                if r.get("response") == "1" and "msg" in r: o['code'] = r['msg']
            
            if o['code']:
                send_tg(f"📩 {o['name']} KOD: {o['code']} (+{o['phone']})")
                st.rerun()

        c1.write(f"**{o['name']}** ({o['src'].upper()}) - {elap}s")
        c2.code(f"+{o['phone']}")
        if o['code']: st.success(f"KOD: {o['code']}")
        if c3.button("🗑️", key=f"d{o['id']}"): to_rem.append(o['id'])

if to_rem:
    st.session_state.orders = [x for x in st.session_state.orders if x['id'] not in to_rem]
    st.rerun()

if canli and st.session_state.orders:
    time.sleep(2); st.rerun()
