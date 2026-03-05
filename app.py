import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Multi-SMS Panel V3.7 - Ultra Fast", layout="wide", page_icon="🇹🇷")

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

AUTO_CANCEL_SEC = 135 

# --- SESSION STATE BAŞLATMA ---
if 'active_orders' not in st.session_state: st.session_state['active_orders'] = []
if 'cached_data' not in st.session_state: st.session_state['cached_data'] = {}
if 'authenticated' not in st.session_state: st.session_state["authenticated"] = False

# --- HIZLI TELEGRAM ---
def send_tg(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try: requests.post(url, data={"chat_id": str(TG_CHAT_ID), "text": msg, "parse_mode": "HTML"}, timeout=3)
    except: pass

# --- API SINIFLARI ---
class TigerSMSBot:
    def call(self, action, **kwargs):
        try: return requests.get("https://api.tiger-sms.com/stubs/handler_api.php", params={"api_key": TIGER_API_KEY, "action": action, **kwargs}, timeout=8).text
        except: return "ERROR"

class OnlineSimBot:
    def call(self, endpoint, **kwargs):
        try: return requests.get(f"https://onlinesim.io/api/{endpoint}.php", params={"apikey": ONLINESIM_API_KEY, "lang": "en", **kwargs}, timeout=8).json()
        except: return {"response": "ERROR"}

class HeroSMSBot:
    def call(self, action, **kwargs):
        try: return requests.get("https://hero-sms.com/stubs/handler_api.php", params={"api_key": HERO_API_KEY, "action": action, **kwargs}, timeout=8).text
        except: return "ERROR"

tiger = TigerSMSBot()
osim = OnlineSimBot()
hero = HeroSMSBot()

# --- VERİ GÜNCELLEME FONKSİYONU (HIZIN KAYNAĞI) ---
def refresh_all_data():
    with st.spinner("Veriler çekiliyor..."):
        data = {"balances": {}, "stocks": {}}
        
        # Bakiyeler
        t_b = tiger.call("getBalance")
        data["balances"]["tiger"] = t_b.split(":")[1] if "ACCESS_BALANCE" in t_b else "0"
        
        o_b = osim.call("getBalance")
        data["balances"]["onlinesim"] = o_b.get("balance", "0") if str(o_b.get("response")) == "1" else "0"
        
        h_b = hero.call("getBalance")
        data["balances"]["hero"] = h_b.split(":")[1] if "ACCESS_BALANCE" in h_b else "0"
        
        # Tiger Stoklar (Toplu çekim)
        t_prices = tiger.call("getPrices", country="62")
        try: data["stocks"]["tiger"] = json.loads(t_prices).get("62", {})
        except: data["stocks"]["tiger"] = {}
        
        # Hero Stoklar (Toplu çekim)
        h_prices = hero.call("getPrices", country="62")
        try: data["stocks"]["hero"] = json.loads(h_prices).get("62", {})
        except: data["stocks"]["hero"] = {}
        
        # OnlineSim Stoklar (Ülke bazlı toplu çekim)
        o_prices = osim.call("getTariffs", country="90")
        if "90" in o_prices: data["stocks"]["onlinesim"] = o_prices["90"].get("services", {})
        else: data["stocks"]["onlinesim"] = {}
        
        st.session_state['cached_data'] = data

# --- GİRİŞ EKRANI ---
if not st.session_state["authenticated"]:
    st.title("🔒 Pro SMS Panel")
    with st.form("l"):
        if st.form_submit_button("Giriş", use_container_width=True) and st.text_input("Şifre:", type="password") == PANEL_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# İlk açılışta veriyi bir kez çek
if not st.session_state['cached_data']: refresh_all_data()

# --- SIDEBAR ---
sd = st.sidebar
sd.title("🤖 Kontrol")
bal = st.session_state['cached_data']["balances"]
sd.metric("🐯 Tiger", f"{bal['tiger']} RUB")
sd.metric("🔵 OnlineSim", f"{bal['onlinesim']} $")
sd.metric("🦸 Hero", f"{bal['hero']} $")

if sd.button("🔄 Verileri Şimdi Güncelle", use_container_width=True):
    refresh_all_data()
    st.rerun()

if sd.button("🔔 Test & Bakiye Gönder", use_container_width=True):
    send_tg(f"🚀 <b>Bakiye Raporu</b>\nTiger: {bal['tiger']} RUB\nOSim: {bal['onlinesim']} $\nHero: {bal['hero']} $")
    sd.success("Gönderildi!")

canli = sd.toggle("🟢 Canlı Takip", value=True)

# --- ALIM FONKSİYONU ---
def buy_num(source, s_name, s_code, country):
    res_id, res_num = None, None
    if source == "tiger":
        r = tiger.call("getNumber", service=s_code, country=country)
        if "ACCESS_NUMBER" in r: res_id, res_num = r.split(":")[1], r.split(":")[2]
    elif source == "hero":
        r = hero.call("getNumber", service=s_code, country=country)
        if "ACCESS_NUMBER" in r: res_id, res_num = r.split(":")[1], r.split(":")[2]
    elif source == "onlinesim":
        r = osim.call("getNum", service=s_code, country=country)
        if str(r.get("response")) == "1":
            res_id = r.get("tzid")
            res_num = r.get("number") or osim.call("getState", tzid=res_id).get("number")

    if res_id and res_num:
        st.session_state['active_orders'].append({"id":res_id, "phone":res_num, "service":s_name, "source":source, "time":time.time(), "status":"Bekliyor", "code":None})
        st.toast(f"✅ Alındı: {source}")
    else: st.error(f"❌ Hata: {source}")

# --- ARAYÜZ (STOKLARI CACHE'DEN OKU) ---
st.title("🇹🇷 Multi-SMS Panel")
t1, t2, t3 = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

stocks = st.session_state['cached_data']["stocks"]

with t1:
    c1, c2 = st.columns(2)
    y = stocks["tiger"].get("yi", {})
    u = stocks["tiger"].get("ub", {})
    c1.write(f"🍔 Yemek: {y.get('cost','-')} RUB | Stok: {y.get('count',0)}")
    if c1.button("TIGER YEMEK", key="bt1"): buy_num("tiger", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {u.get('cost','-')} RUB | Stok: {u.get('count',0)}")
    if c2.button("TIGER UBER", key="bt2"): buy_num("tiger", "Uber", "ub", "62")

with t2:
    c1, c2, c3 = st.columns(3)
    # OnlineSim'de yemeksepeti ve uber anahtarlarını kontrol et
    oy = stocks["onlinesim"].get("yemeksepeti", {})
    ou = stocks["onlinesim"].get("uber", {})
    oe = stocks["onlinesim"].get("espressolab", {})
    c1.write(f"🍔 Yemek: {oy.get('price','-')} $ | Stok: {oy.get('count',0)}")
    if c1.button("OSIM YEMEK", key="bo1"): buy_num("onlinesim", "Yemeksepeti", "yemeksepeti", "90")
    c2.write(f"🚗 Uber: {ou.get('price','-')} $ | Stok: {ou.get('count',0)}")
    if c2.button("OSIM UBER", key="bo2"): buy_num("onlinesim", "Uber", "uber", "90")
    c3.write(f"☕ Kahve: {oe.get('price','-')} $ | Stok: {oe.get('count',0)}")
    if c3.button("OSIM KAHVE", key="bo3"): buy_num("onlinesim", "Espressolab", "espressolab", "90")

with t3:
    c1, c2 = st.columns(2)
    hy = stocks["hero"].get("yi", {})
    hu = stocks["hero"].get("ub", {})
    c1.write(f"🍔 Yemek: {hy.get('cost','-')} $ | Stok: {hy.get('count',0)}")
    if c1.button("HERO YEMEK", key="bh1"): buy_num("hero", "Yemeksepeti", "yi", "62")
    c2.write(f"🚗 Uber: {hu.get('cost','-')} $ | Stok: {hu.get('count',0)}")
    if c2.button("HERO UBER", key="bh2"): buy_num("hero", "Uber", "ub", "62")

# --- TAKİP SİSTEMİ ---
st.divider()
to_rem = []
for o in st.session_state['active_orders']:
    elap = int(time.time() - o['time'])
    if o['code'] is None and elap >= AUTO_CANCEL_SEC:
        if o['source'] == "tiger": tiger.call("setStatus", id=o['id'], status=8)
        elif o['source'] == "hero": hero.call("setStatus", id=o['id'], status=8)
        else: osim.call("setOperationRevise", tzid=o['id'])
        to_rem.append(o['id'])
        continue
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.write(f"**{o['service']}** ({o['source'].upper()})")
            if o['code'] is None:
                if o['source'] == "tiger":
                    r = tiger.call("getStatus", id=o['id'])
                    if "STATUS_OK" in r: o['code'] = r.split(":")[1]
                elif o['source'] == "hero":
                    r = hero.call("getStatus", id=o['id'])
                    if "STATUS_OK" in r: o['code'] = r.split(":")[1]
                else:
                    r = osim.call("getState", tzid=o['id'])
                    if r.get("response") == "1" and "msg" in r: o['code'] = r['msg']
                
                if o['code']:
                    send_tg(f"📩 <b>{o['service']}</b>\nKod: <code>{o['code']}</code>\nNumara: +{o['phone']}")
                    o['status'] = "✅ TAMAMLANDI"
                    st.rerun()
                o['status'] = f"⌛ {elap}s"
            st.write(f"Durum: {o['status']}")
            if o['code']: st.success(f"KOD: {o['code']}")
        c2.code(f"+{o['phone']}")
        if c3.button("🗑️", key=f"d{o['id']}"): to_rem.append(o['id'])

if to_rem:
    st.session_state['active_orders'] = [x for x in st.session_state['active_orders'] if x['id'] not in to_rem]
    st.rerun()

if canli and st.session_state['active_orders']:
    time.sleep(2)
    st.rerun()
 
