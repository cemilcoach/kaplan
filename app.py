import streamlit as st
import requests
import time
import json

# --- 1. AYARLAR ---
st.set_page_config(page_title="SMS Panel V4.1", layout="wide", page_icon="🇹🇷")

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

# --- 3. API ÇEKİRDEĞİ ---
def fast_get(url, params=None, is_json=False):
    try:
        r = requests.get(url, params=params, timeout=7)
        if is_json:
            return r.json()
        return r.text
    except:
        return {} if is_json else "ERROR"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{KEYS['tg_token']}/sendMessage"
    requests.post(url, data={"chat_id": str(KEYS['tg_chat']), "text": msg, "parse_mode": "HTML"}, timeout=3)

# --- 4. VERİ GÜNCELLEME (REBUILT FOR ONLINESIM) ---
def refresh_panel():
    with st.spinner("Veriler yenileniyor..."):
        # --- Tiger & Hero ---
        t_b = fast_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getBalance"})
        st.session_state.balances["tiger"] = t_b.split(":")[1] if "ACCESS" in t_b else "0"
        
        h_b = fast_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getBalance"})
        st.session_state.balances["hero"] = h_b.split(":")[1] if "ACCESS" in h_b else "0"

        # --- OnlineSim Bakiye (Özel Fix) ---
        # Hem json hem string yanıtı kontrol ediyoruz
        o_b_raw = fast_get("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["osim"]}, is_json=True)
        if isinstance(o_b_raw, dict) and "balance" in o_b_raw:
            st.session_state.balances["osim"] = str(o_b_raw["balance"])
        else:
            # Yedek yöntem: String denemesi
            o_b_str = fast_get("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["osim"]})
            st.session_state.balances["osim"] = o_b_str if "." in o_b_str else "0"

        # --- Stoklar ---
        # Tiger & Hero
        try:
            st.session_state.stocks["tiger"] = json.loads(fast_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getPrices", "country": "62"})).get("62", {})
            st.session_state.stocks["hero"] = json.loads(fast_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getPrices", "country": "62"})).get("62", {})
        except: pass

        # OnlineSim Stoklar (Derin Tarama)
        o_tariffs = fast_get("https://onlinesim.io/api/getTariffs.php", {"apikey": KEYS["osim"], "country": "90"}, is_json=True)
        # Default country turkey ise yanıt "90" anahtarı altında gelir, değilse direkt gelebilir.
        if "90" in o_tariffs:
            st.session_state.stocks["osim"] = o_tariffs["90"].get("services", {})
        else:
            st.session_state.stocks["osim"] = o_tariffs.get("services", {})

# --- 5. GİRİŞ ---
if not st.session_state.auth:
    st.title("🔒 Pro SMS Panel")
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

# --- 7. ALIM ---
def buy(source, s_name, s_code, country):
    res_id, res_num = None, None
    if source == "tiger":
        r = fast_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getNumber", "service": s_code, "country": country})
        if "ACCESS" in r: parts = r.split(":"); res_id, res_num = parts[1], parts[2]
    elif source == "hero":
        r = fast_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getNumber", "service": s_code, "country": country})
        if "ACCESS" in r: parts = r.split(":"); res_id, res_num = parts[1], parts[2]
    elif source == "osim":
        r = fast_get("https://onlinesim.io/api/getNum.php", {"apikey": KEYS["osim"], "service": s_code, "country": country}, is_json=True)
        if str(r.get("response")) == "1": res_id, res_num = r.get("tzid"), r.get("number")

    if res_id and res_num:
        st.session_state.orders.append({"id":res_id, "phone":res_num, "name":s_name, "src":source, "time":time.time(), "code":None})
        st.toast("✅ Başarılı!")
    else: st.error(f"Hata: {source}")

# --- 8. ARAYÜZ ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

# Veri kısayolları
s_t = st.session_state.stocks["tiger"]
s_o = st.session_state.stocks["osim"]
s_h = st.session_state.stocks["hero"]

with t1:
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {s_t.get('yi',{}).get('cost','-')} RUB")
    if c1.button("T-YEMEK AL", key="bt1"): buy("tiger", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {s_t.get('ub',{}).get('cost','-')} RUB")
    if c2.button("T-UBER AL", key="bt2"): buy("tiger", "Uber", "ub", "62")

with t2:
    c1, c2, c3 = st.columns(3)
    # OnlineSim'de servis isimleri bazen farklılık gösterebilir, hem slug hem key bakıyoruz
    oy = s_o.get("yemeksepeti", {}) or next((v for k,v in s_o.items() if v.get('slug')=='yemeksepeti'), {})
    ou = s_o.get("uber", {}) or next((v for k,v in s_o.items() if v.get('slug')=='uber'), {})
    oe = s_o.get("espressolab", {}) or next((v for k,v in s_o.items() if v.get('slug')=='espressolab'), {})
    
    c1.write(f"🍔 Yemek: {oy.get('price','-')} $")
    if c1.button("O-YEMEK AL", key="bo1"): buy("osim", "Yemeksepeti", "yemeksepeti", "90")
    c2.write(f"🚗 Uber: {ou.get('price','-')} $")
    if c2.button("O-UBER AL", key="bo2"): buy("osim", "Uber", "uber", "90")
    c3.write(f"☕ Kahve: {oe.get('price','-')} $")
    if c3.button("O-KAHVE AL", key="bo3"): buy("osim", "Espressolab", "espressolab", "90")

with t3:
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {s_h.get('yi',{}).get('cost','-')} $")
    if c1.button("H-YEMEK AL", key="bh1"): buy("hero", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {s_h.get('ub',{}).get('cost','-')} $")
    if c2.button("H-UBER AL", key="bh2"): buy("hero", "Uber", "ub", "62")

# --- 9. TAKİP ---
st.divider()
to_rem = []
for o in st.session_state.orders:
    elap = int(time.time() - o['time'])
    if elap > 135 and o['code'] is None:
        to_rem.append(o['id']); continue

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
    time.sleep(2); st.rerun()
