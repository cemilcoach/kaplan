import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="SMS Panel V3.8 - Max Speed", layout="wide", page_icon="🇹🇷")

# --- KONFİGÜRASYON ---
try:
    TIGER_API_KEY = st.secrets["TIGER_API_KEY"]
    ONLINESIM_API_KEY = st.secrets["ONLINESIM_API_KEY"]
    HERO_API_KEY = st.secrets["HERO_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception as e:
    st.error(f"🚨 Secrets eksik: {e}")
    st.stop()

# --- SABİTLER ---
AUTO_CANCEL_SEC = 135 

# --- SESSION STATE YÖNETİMİ ---
# Verileri cache'de tutarak gereksiz API isteklerini önlüyoruz.
if 'active_orders' not in st.session_state: st.session_state['active_orders'] = []
if 'authenticated' not in st.session_state: st.session_state["authenticated"] = False
if 'data_cache' not in st.session_state: 
    st.session_state['data_cache'] = {"balances": {}, "stocks": {}}

# --- API FONKSİYONLARI ---
@st.cache_data(ttl=60) # 60 saniye boyunca aynı isteği tekrar yapmaz, hızı artırır
def call_generic_api(url, params):
    try:
        return requests.get(url, params=params, timeout=5).text
    except:
        return "ERROR"

def send_tg_fast(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try: requests.post(url, data={"chat_id": str(TG_CHAT_ID), "text": msg, "parse_mode": "HTML"}, timeout=2)
    except: pass

# --- GİRİŞ KONTROLÜ ---
if not st.session_state["authenticated"]:
    st.title("🔒 Pro SMS Panel")
    with st.form("login"):
        pwd = st.text_input("Şifre:", type="password")
        if st.form_submit_button("Giriş", use_container_width=True):
            if pwd == PANEL_SIFRESI:
                st.session_state["authenticated"] = True
                st.rerun()
    st.stop()

# --- SIDEBAR (BAKİYELER) ---
st.sidebar.title("🤖 Kontrol")

def update_balances():
    # Tiger (RUB)
    t_res = call_generic_api("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": TIGER_API_KEY, "action": "getBalance"})
    st.session_state['data_cache']["balances"]["tiger"] = t_res.split(":")[1] if "ACCESS_BALANCE" in t_res else "0"
    
    # Hero (USD)
    h_res = call_generic_api("https://hero-sms.com/stubs/handler_api.php", {"api_key": HERO_API_KEY, "action": "getBalance"})
    st.session_state['data_cache']["balances"]["hero"] = h_res.split(":")[1] if "ACCESS_BALANCE" in h_res else "0"
    
    # OnlineSim (USD)
    o_res = requests.get(f"https://onlinesim.io/api/getBalance.php", params={"apikey": ONLINESIM_API_KEY}).json()
    st.session_state['data_cache']["balances"]["onlinesim"] = o_res.get("balance", "0")

if st.sidebar.button("🔄 Bakiyeleri Güncelle", use_container_width=True) or not st.session_state['data_cache']["balances"]:
    update_balances()

bal = st.session_state['data_cache']["balances"]
st.sidebar.metric("🐯 Tiger", f"{bal.get('tiger', '0')} RUB")
st.sidebar.metric("🔵 OnlineSim", f"{bal.get('onlinesim', '0')} $")
st.sidebar.metric("🦸 Hero", f"{bal.get('hero', '0')} $")

if st.sidebar.button("🔔 Test Mesajı Gönder"):
    send_tg_fast(f"🚀 Bakiyeler:\nTiger: {bal.get('tiger')} RUB\nOSim: {bal.get('onlinesim')} $\nHero: {bal.get('hero')} $")

canli = st.sidebar.toggle("🟢 Canlı Takip", value=True)

# --- ANA PANEL ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

# --- ALIM FONKSİYONU ---
def buy_action(source, s_name, s_code, country):
    res_id, res_num = None, None
    if source == "tiger":
        r = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", params={"api_key":TIGER_API_KEY,"action":"getNumber","service":s_code,"country":country}).text
        if "ACCESS_NUMBER" in r: res_id, res_num = r.split(":")[1], r.split(":")[2]
    elif source == "hero":
        r = requests.get("https://hero-sms.com/stubs/handler_api.php", params={"api_key":HERO_API_KEY,"action":"getNumber","service":s_code,"country":country}).text
        if "ACCESS_NUMBER" in r: res_id, res_num = r.split(":")[1], r.split(":")[2]
    elif source == "onlinesim":
        r = requests.get("https://onlinesim.io/api/getNum.php", params={"apikey":ONLINESIM_API_KEY,"service":s_code,"country":country}).json()
        if str(r.get("response")) == "1":
            res_id, res_num = r.get("tzid"), r.get("number")

    if res_id and res_num:
        st.session_state['active_orders'].append({"id":res_id, "phone":res_num, "service":s_name, "source":source, "time":time.time(), "status":"Bekliyor", "code":None})
        st.toast("✅ Numara Alındı!")
    else: st.error(f"❌ Başarısız: {source}")

# --- SEKMELER ---
with t1:
    # Sadece bu sekme açıldığında stok çekilir
    t_stocks = json.loads(call_generic_api("https://api.tiger-sms.com/stubs/handler_api.php", {"api_key": TIGER_API_KEY, "action": "getPrices", "country": "62"})).get("62", {})
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {t_stocks.get('yi',{}).get('cost','-')} RUB")
    if c1.button("AL", key="bt1"): buy_action("tiger", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {t_stocks.get('ub',{}).get('cost','-')} RUB")
    if c2.button("AL", key="bt2"): buy_action("tiger", "Uber", "ub", "62")

with t2:
    # OnlineSim Türkiye (90) stokları
    o_stocks = requests.get("https://onlinesim.io/api/getTariffs.php", params={"apikey":ONLINESIM_API_KEY, "country":"90"}).json().get("90", {}).get("services", {})
    c1, c2, c3 = st.columns(3)
    c1.write(f"🍔 Yemek: {o_stocks.get('yemeksepeti',{}).get('price','-')} $")
    if c1.button("AL", key="bo1"): buy_action("onlinesim", "Yemeksepeti", "yemeksepeti", "90")
    c2.write(f"🚗 Uber: {o_stocks.get('uber',{}).get('price','-')} $")
    if c2.button("AL", key="bo2"): buy_action("onlinesim", "Uber", "uber", "90")
    c3.write(f"☕ Kahve: {o_stocks.get('espressolab',{}).get('price','-')} $")
    if c3.button("AL", key="bo3"): buy_action("onlinesim", "Espressolab", "espressolab", "90")

with t3:
    h_stocks = json.loads(call_generic_api("https://hero-sms.com/stubs/handler_api.php", {"api_key": HERO_API_KEY, "action": "getPrices", "country": "62"})).get("62", {})
    c1, c2 = st.columns(2)
    c1.write(f"🍔 Yemek: {h_stocks.get('yi',{}).get('cost','-')} $")
    if c1.button("AL", key="bh1"): buy_action("hero", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {h_stocks.get('ub',{}).get('cost','-')} $")
    if c2.button("AL", key="bh2"): buy_action("hero", "Uber", "ub", "62")

# --- TAKİP (SADECE SİPARİŞ VARSA ÇALIŞIR) ---
if st.session_state['active_orders']:
    st.divider()
    to_rem = []
    for o in st.session_state['active_orders']:
        elap = int(time.time() - o['time'])
        if o['code'] is None and elap >= AUTO_CANCEL_SEC:
            # İptal işlemleri
            if o['source'] == "tiger": requests.get("https://api.tiger-sms.com/stubs/handler_api.php", params={"api_key":TIGER_API_KEY,"action":"setStatus","id":o['id'],"status":8})
            elif o['source'] == "hero": requests.get("https://hero-sms.com/stubs/handler_api.php", params={"api_key":HERO_API_KEY,"action":"setStatus","id":o['id'],"status":8})
            else: requests.get("https://onlinesim.io/api/setOperationRevise.php", params={"apikey":ONLINESIM_API_KEY,"tzid":o['id']})
            to_rem.append(o['id'])
            continue
        
        # Durum Sorgulama
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            if o['code'] is None:
                if o['source'] == "tiger":
                    check = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", params={"api_key":TIGER_API_KEY,"action":"getStatus","id":o['id']}).text
                    if "STATUS_OK" in check: o['code'] = check.split(":")[1]
                elif o['source'] == "hero":
                    check = requests.get("https://hero-sms.com/stubs/handler_api.php", params={"api_key":HERO_API_KEY,"action":"getStatus","id":o['id']}).text
                    if "STATUS_OK" in check: o['code'] = check.split(":")[1]
                else:
                    check = requests.get("https://onlinesim.io/api/getState.php", params={"apikey":ONLINESIM_API_KEY,"tzid":o['id']}).json()
                    if check.get("response") == "1" and "msg" in check: o['code'] = check['msg']
                
                if o['code']:
                    send_tg_fast(f"📩 {o['service']} KOD: {o['code']}")
                    st.rerun()

            c1.write(f"**{o['service']}** ({o['source'].upper()}) - {elap}s")
            c2.code(f"+{o['phone']}")
            if o['code']: st.success(f"KOD: {o['code']}")
            if c3.button("🗑️", key=f"d{o['id']}"): to_rem.append(o['id'])

    if to_rem:
        st.session_state['active_orders'] = [x for x in st.session_state['active_orders'] if x['id'] not in to_rem]
        st.rerun()

    if canli:
        time.sleep(2)
        st.rerun()
 
