import streamlit as st
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

# --- 1. AYARLAR ---
st.set_page_config(page_title="SMS Panel V4.3 Turbo", layout="wide", page_icon="🚀")

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
if 'balances' not in st.session_state: st.session_state.balances = {}
if 'stocks' not in st.session_state: st.session_state.stocks = {}

# --- 3. ÇEKİRDEK FONKSİYONLAR ---
def safe_get(url, params=None, is_json=False, timeout=5):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200: return r.json() if is_json else r.text
    except: pass
    return {} if is_json else "OFFLINE"

def send_tg(msg):
    url = f"https://api.telegram.org/bot{KEYS['tg_token']}/sendMessage"
    try: requests.post(url, data={"chat_id": str(KEYS['tg_chat']), "text": msg, "parse_mode": "HTML"}, timeout=2)
    except: pass

# --- 4. PARALEL VERİ ÇEKME (HIZIN KAYNAĞI) ---
def fetch_all_data():
    """Tüm API'leri aynı anda sorgular."""
    urls = {
        "t_bal": ("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getBalance"}, False),
        "h_bal": ("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getBalance"}, False),
        "o_bal": ("https://onlinesim.io/api/getBalance.php", {"apikey": KEYS["osim"]}, True),
        "t_stock": ("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getPrices", "country": "62"}, True),
        "h_stock": ("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getPrices", "country": "62"}, True),
        "o_stock": ("https://onlinesim.io/api/getTariffs.php", {"apikey": KEYS["osim"], "country": "90"}, True)
    }

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {k: executor.submit(safe_get, u, p, j) for k, (u, p, j) in urls.items()}
        results = {k: f.result() for k, f in futures.items()}

    # Verileri İşle
    st.session_state.balances = {
        "tiger": results["t_bal"].split(":")[1] if "ACCESS" in results["t_bal"] else "OFFLINE",
        "hero": results["h_bal"].split(":")[1] if "ACCESS" in results["h_bal"] else "OFFLINE",
        "osim": str(results["o_bal"].get("balance", "OFFLINE")) if isinstance(results["o_bal"], dict) else "OFFLINE"
    }
    
    st.session_state.stocks = {
        "tiger": results["t_stock"].get("62", {}) if isinstance(results["t_stock"], dict) else {},
        "hero": results["h_stock"].get("62", {}) if isinstance(results["h_stock"], dict) else {},
        "osim": results["o_stock"].get("90", {}).get("services", {}) if "90" in results["o_stock"] else results["o_stock"].get("services", {})
    }

# --- 5. GİRİŞ VE ANA EKRAN YÜKLEME ---
if not st.session_state.auth:
    st.title("🔒 Pro SMS Panel")
    with st.form("login"):
        pwd = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap", use_container_width=True):
            if pwd == KEYS["pass"]:
                st.session_state.auth = True
                st.rerun()
            else: st.error("Hatalı Şifre!")
    st.stop()

# Ana veriler yoksa yükle
if not st.session_state.balances:
    st.info("🚀 Veriler API üzerinden senkronize ediliyor, lütfen bekleyin...")
    fetch_all_data()
    st.rerun()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🤖 Panel Kontrol")
    st.metric("🐯 Tiger", f"{st.session_state.balances['tiger']} RUB")
    st.metric("🔵 OnlineSim", f"{st.session_state.balances['osim']} $")
    st.metric("🦸 Hero", f"{st.session_state.balances['hero']} $")
    
    if st.button("🔄 Verileri Yenile", use_container_width=True):
        fetch_all_data()
        st.rerun()
        
    if st.button("🔔 Botu Test Et", use_container_width=True):
        msg = f"🚀 <b>Test</b>\nTiger: {st.session_state.balances['tiger']} RUB\nOSim: {st.session_state.balances['osim']} $\nHero: {st.session_state.balances['hero']} $"
        send_tg(msg)
        st.sidebar.success("Test mesajı gönderildi!")

    canli = st.toggle("🟢 Canlı Takip", value=True)
    if st.button("🚪 Çıkış"):
        st.session_state.auth = False
        st.rerun()

# --- 7. ALIM FONKSİYONU ---
def buy(source, s_name, s_code, country):
    res_id, res_num = None, None
    with st.spinner(f"{source.upper()} üzerinden numara alınıyor..."):
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
        st.toast("✅ İşlem Başarılı!")
        st.rerun()
    else: st.error(f"❌ {source} şu an bu numarayı veremiyor.")

# --- 8. ANA PANEL SEKME İÇERİKLERİ ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

s_t = st.session_state.stocks["tiger"]
s_o = st.session_state.stocks["osim"]
s_h = st.session_state.stocks["hero"]

with t1:
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemeksepeti: **{s_t.get('yi',{}).get('cost','-')} RUB** | Stok: {s_t.get('yi',{}).get('count',0)}")
    if c1.button("T-YEMEK AL", key="bt1"): buy("tiger", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: **{s_t.get('ub',{}).get('cost','-')} RUB** | Stok: {s_t.get('ub',{}).get('count',0)}")
    if c2.button("T-UBER AL", key="bt2"): buy("tiger", "Uber", "ub", "62")

with t2:
    c1, c2, c3 = st.columns(3)
    oy = s_o.get("yemeksepeti", {}) or next((v for k,v in s_o.items() if v.get('slug')=='yemeksepeti'), {})
    ou = s_o.get("uber", {}) or next((v for k,v in s_o.items() if v.get('slug')=='uber'), {})
    oe = s_o.get("espressolab", {}) or next((v for k,v in s_o.items() if v.get('slug')=='espressolab'), {})
    
    c1.write(f"🍔 Yemek: **{oy.get('price','-')} $** | Stok: {oy.get('count',0)}")
    if c1.button("O-YEMEK AL", key="bo1"): buy("osim", "Yemeksepeti", "yemeksepeti", "90")
    c2.write(f"🚗 Uber: **{ou.get('price','-')} $** | Stok: {ou.get('count',0)}")
    if c2.button("O-UBER AL", key="bo2"): buy("osim", "Uber", "uber", "90")
    c3.write(f"☕ Kahve: **{oe.get('price','-')} $** | Stok: {oe.get('count',0)}")
    if c3.button("O-KAHVE AL", key="bo3"): buy("osim", "Espressolab", "espressolab", "90")

with t3:
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemeksepeti: **{s_h.get('yi',{}).get('cost','-')} $** | Stok: {s_h.get('yi',{}).get('count',0)}")
    if c1.button("H-YEMEK AL", key="bh1"): buy("hero", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: **{s_h.get('ub',{}).get('cost','-')} $** | Stok: {s_h.get('ub',{}).get('count',0)}")
    if c2.button("H-UBER AL", key="bh2"): buy("hero", "Uber", "ub", "62")

# --- 9. TAKİP SİSTEMİ ---
st.divider()
st.subheader("📋 İşlem Takibi")
to_rem = []
for o in st.session_state.orders:
    elap = int(time.time() - o['time'])
    if elap > 135 and o['code'] is None:
        if o['src'] == "tiger": safe_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "setStatus", "id": o['id'], "status": 8})
        elif o['src'] == "hero": safe_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "setStatus", "id": o['id'], "status": 8})
        else: safe_get("https://onlinesim.io/api/setOperationRevise.php", {"apikey": KEYS["osim"], "tzid": o['id']}, is_json=True)
        to_rem.append(o['id']); continue

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        if o['code'] is None:
            if o['src'] == "tiger":
                res = safe_get("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": KEYS["tiger"], "action": "getStatus", "id": o['id']})
                if "STATUS_OK" in res: o['code'] = res.split(":")[1]
            elif o['src'] == "hero":
                res = safe_get("https://hero-sms.com/stubs/handler_api.php", {"api_key": KEYS["hero"], "action": "getStatus", "id": o['id']})
                if "STATUS_OK" in res: o['code'] = res.split(":")[1]
            elif o['src'] == "osim":
                res = safe_get("https://onlinesim.io/api/getState.php", {"apikey": KEYS["osim"], "tzid": o['id']}, is_json=True)
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
