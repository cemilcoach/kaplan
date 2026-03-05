import streamlit as st
import requests
import time
import json

# --- 1. AYARLAR VE GÜVENLİK ---
st.set_page_config(page_title="SMS Panel V4.0", layout="wide", page_icon="🇹🇷")

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

# --- 2. DURUM YÖNETİMİ (SESSION STATE) ---
DEFAULTS = {
    "auth": False,
    "orders": [],
    "balances": {"tiger": "0", "osim": "0", "hero": "0"},
    "stocks": {"tiger": {}, "osim": {}, "hero": {}}
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 3. API ÇEKİRDEĞİ ---
def fast_get(url, params=None, is_json=False):
    try:
        r = requests.get(url, params=params, timeout=5)
        return r.json() if is_json else r.text
    except:
        return {} if is_json else "ERROR"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{KEYS['tg_token']}/sendMessage"
    fast_get(url, {"chat_id": str(KEYS['tg_chat']), "text": msg, "parse_mode": "HTML"})

# --- 4. VERİ GÜNCELLEME (SADECE TETİKLENDİĞİNDE) ---
def refresh_panel():
    # Bakiyeler
    t = fast_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getBalance"})
    st.session_state.balances["tiger"] = t.split(":")[1] if "ACCESS" in t else "0"
    
    h = fast_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getBalance"})
    st.session_state.balances["hero"] = h.split(":")[1] if "ACCESS" in h else "0"
    
    o = fast_get("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["osim"]}, is_json=True)
    st.session_state.balances["osim"] = o.get("balance", "0")

    # Stoklar
    st.session_state.stocks["tiger"] = json.loads(fast_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getPrices", "country": "62"})).get("62", {})
    st.session_state.stocks["hero"] = json.loads(fast_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getPrices", "country": "62"})).get("62", {})
    st.session_state.stocks["osim"] = fast_get("https://onlinesim.io/api/getTariffs.php", {"apikey": KEYS["osim"], "country": "90"}, is_json=True).get("90", {}).get("services", {})

# --- 5. GİRİŞ KONTROLÜ ---
if not st.session_state.auth:
    with st.form("login"):
        if st.form_submit_button("Giriş", use_container_width=True) and st.text_input("Şifre", type="password") == KEYS["pass"]:
            st.session_state.auth = True
            refresh_panel()
            st.rerun()
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

# --- 7. ALIM İŞLEMİ ---
def buy(source, s_name, s_code, country):
    res_id, res_num = None, None
    if source == "tiger":
        r = fast_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getNumber", "service": s_code, "country": country})
        if "ACCESS" in r: res_id, res_num = r.split(":")[1], r.split(":")[2]
    elif source == "hero":
        r = fast_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getNumber", "service": s_code, "country": country})
        if "ACCESS" in r: res_id, res_num = r.split(":")[1], r.split(":")[2]
    elif source == "osim":
        r = fast_get("https://onlinesim.io/api/getNum.php", {"apikey": KEYS["osim"], "service": s_code, "country": country}, is_json=True)
        if str(r.get("response")) == "1": res_id, res_num = r.get("tzid"), r.get("number")

    if res_id and res_num:
        st.session_state.orders.append({"id":res_id, "phone":res_num, "name":s_name, "src":source, "time":time.time(), "code":None})
        st.toast("Numara Alındı!")
    else: st.error("Stok yok veya bakiye yetersiz.")

# --- 8. ARAYÜZ ---
st.title("🇹🇷 Multi-SMS Panel")
tabs = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

with tabs[0]: # Tiger
    c1, c2 = st.columns(2)
    s = st.session_state.stocks["tiger"]
    c1.write(f"🍔 Yemek: {s.get('yi',{}).get('cost','-')} RUB")
    if c1.button("AL", key="t1"): buy("tiger", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {s.get('ub',{}).get('cost','-')} RUB")
    if c2.button("AL", key="t2"): buy("tiger", "Uber", "ub", "62")

with tabs[1]: # OnlineSim
    c1, c2, c3 = st.columns(3)
    s = st.session_state.stocks["osim"]
    c1.write(f"🍔 Yemek: {s.get('yemeksepeti',{}).get('price','-')} $")
    if c1.button("AL", key="o1"): buy("osim", "Yemeksepeti", "yemeksepeti", "90")
    c2.write(f"🚗 Uber: {s.get('uber',{}).get('price','-')} $")
    if c2.button("AL", key="o2"): buy("osim", "Uber", "uber", "90")
    c3.write(f"☕ Kahve: {s.get('espressolab',{}).get('price','-')} $")
    if c3.button("AL", key="o3"): buy("osim", "Espressolab", "espressolab", "90")

with tabs[2]: # Hero
    c1, c2 = st.columns(2)
    s = st.session_state.stocks["hero"]
    c1.write(f"🍔 Yemek: {s.get('yi',{}).get('cost','-')} $")
    if c1.button("AL", key="h1"): buy("hero", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {s.get('ub',{}).get('cost','-')} $")
    if c2.button("AL", key="h2"): buy("hero", "Uber", "ub", "62")

# --- 9. TAKİP VE OTO-YENİLEME ---
st.divider()
to_rem = []
for o in st.session_state.orders:
    elap = int(time.time() - o['time'])
    if elap > 135 and o['code'] is None:
        to_rem.append(o['id'])
        continue

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        if o['code'] is None:
            if o['src'] == "tiger":
                res = fast_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getStatus", "id": o['id']})
                if "STATUS_OK" in res: o['code'] = res.split(":")[1]
            elif o['src'] == "hero":
                res = fast_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getStatus", "id": o['id']})
                if "STATUS_OK" in res: o['code'] = res.split(":")[1]
            elif o['src'] == "osim":
                res = fast_get("https://onlinesim.io/api/getState.php", {"apikey": KEYS["osim"], "tzid": o['id']}, is_json=True)
                if res.get("response") == "1" and "msg" in res: o['code'] = res['msg']
            
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
    time.sleep(2)
    st.rerun()
