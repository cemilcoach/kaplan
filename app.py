import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Multi-SMS Panel V3.6", layout="wide", page_icon="🇹🇷")

# --- KONFİGÜRASYON ---
try:
    TIGER_API_KEY = st.secrets["TIGER_API_KEY"]
    ONLINESIM_API_KEY = st.secrets["ONLINESIM_API_KEY"]
    HERO_API_KEY = st.secrets["HERO_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception as e:
    st.error(f"🚨 Secrets dosyasında eksiklik var! Hata: {e}")
    st.stop()

AUTO_CANCEL_SEC = 135 

# --- GELİŞMİŞ TELEGRAM FONKSİYONU ---
def send_telegram_instant(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": str(TG_CHAT_ID), "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload, timeout=5)
        res_data = response.json()
        return res_data.get("ok"), res_data.get("description", "Başarılı")
    except Exception as e:
        return False, str(e)

# --- API SINIFLARI ---
class TigerSMSBot:
    def call_api(self, action, **kwargs):
        params = {"api_key": TIGER_API_KEY, "action": action, **kwargs}
        try:
            r = requests.get("https://api.tiger-sms.com/stubs/handler_api.php", params=params, timeout=10)
            return r.text
        except: return "ERROR"

    def get_info(self, service):
        res = self.call_api("getPrices", service=service, country="62")
        try:
            data = json.loads(res)
            if "62" in data and service in data["62"]:
                return data["62"][service].get('cost'), data["62"][service].get('count')
        except: pass
        return None, 0

class OnlineSimBot:
    def call_api(self, endpoint, **kwargs):
        params = {"apikey": ONLINESIM_API_KEY, "lang": "en", **kwargs}
        try:
            r = requests.get(f"https://onlinesim.io/api/{endpoint}.php", params=params, timeout=10)
            return r.json()
        except: return {"response": "ERROR"}

    def get_info(self, service_slug):
        """OnlineSim Türkiye (90) verisini hiyerarşik olarak çeker."""
        # Dökümana göre getTariffs çağrısı ülke parametresi ile yapılır
        res = self.call_api("getTariffs", country="90")
        try:
            # Yanıt yapısı: {"90": {"services": {"service_name": {...}}}}
            if "90" in res:
                services = res["90"].get("services", {})
                # OnlineSim'de servis anahtarı genellikle slug ile aynıdır
                if service_slug in services:
                    val = services[service_slug]
                    return val.get("price"), val.get("count")
                
                # Eğer anahtar olarak bulamazsa içerde ara (Yemeksepeti vb. için)
                for key, val in services.items():
                    if val.get("slug") == service_slug or key.lower() == service_slug.lower():
                        return val.get("price"), val.get("count")
        except: pass
        return None, 0

class HeroSMSBot:
    def call_api(self, action, **kwargs):
        params = {"api_key": HERO_API_KEY, "action": action, **kwargs}
        try:
            r = requests.get("https://hero-sms.com/stubs/handler_api.php", params=params, timeout=10)
            return r.text
        except: return "ERROR"

    def get_info(self, service):
        res = self.call_api("getPrices", service=service, country="62")
        try:
            data = json.loads(res)
            if "62" in data and service in data["62"]:
                return data["62"][service].get('cost'), data["62"][service].get('count')
        except: pass
        return None, 0

# --- GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Pro SMS Panel Giriş")
    with st.form("login_form"):
        pwd = st.text_input("Şifre:", type="password")
        if st.form_submit_button("Giriş Yap", use_container_width=True):
            if pwd == PANEL_SIFRESI:
                st.session_state["authenticated"] = True
                st.rerun()
            else: st.error("❌ Hatalı Şifre!")
    st.stop()

# --- BAŞLATMA ---
tiger = TigerSMSBot()
osim = OnlineSimBot()
hero = HeroSMSBot()

if 'active_orders' not in st.session_state:
    st.session_state['active_orders'] = []

# --- SIDEBAR ---
st.sidebar.title("🤖 Panel Kontrol")
try:
    t_bal_raw = tiger.call_api("getBalance")
    t_bal = t_bal_raw.split(":")[1] if "ACCESS_BALANCE" in t_bal_raw else "0"
    o_bal_res = osim.call_api("getBalance")
    o_bal = o_bal_res.get("balance", "0") if str(o_bal_res.get("response")) == "1" else "0"
    h_bal_raw = hero.call_api("getBalance")
    h_bal = h_bal_raw.split(":")[1] if "ACCESS_BALANCE" in h_bal_raw else "0"
except:
    t_bal, o_bal, h_bal = "Hata", "Hata", "Hata"

st.sidebar.metric("🐯 Tiger", f"{t_bal} RUB")
st.sidebar.metric("🔵 OnlineSim", f"{o_bal} $")
st.sidebar.metric("🦸 Hero-SMS", f"{h_bal} $")

if st.sidebar.button("🔄 Stok & Bakiye Güncelle", use_container_width=True):
    st.rerun()

if st.sidebar.button("🔔 Telegram Botu Test Et", use_container_width=True):
    msg = f"🚀 <b>Test</b>\nTiger: {t_bal} RUB\nOSim: {o_bal} $\nHero: {h_bal} $"
    success, detail = send_telegram_instant(msg)
    if success: st.sidebar.success("Mesaj gitti!")
    else: st.sidebar.error(f"Hata: {detail}")

st.sidebar.divider()
canli_takip = st.sidebar.toggle("🟢 Canlı Takip", value=True)
if st.sidebar.button("🚪 Çıkış", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

# --- NUMARA ALMA ---
def buy_num(source, s_name, s_code, country):
    res_id, res_num = None, None
    if source == "tiger":
        r = tiger.call_api("getNumber", service=s_code, country=country)
        if "ACCESS_NUMBER" in r:
            parts = r.split(":")
            res_id, res_num = parts[1], parts[2]
    elif source == "hero":
        r = hero.call_api("getNumber", service=s_code, country=country)
        if "ACCESS_NUMBER" in r:
            parts = r.split(":")
            res_id, res_num = parts[1], parts[2]
    elif source == "onlinesim":
        # OnlineSim alımında country parametresi E.164 formatında olmalı (Türkiye=90)
        r = osim.call_api("getNum", service=s_code, country=country)
        if str(r.get("response")) == "1" and "tzid" in r:
            res_id = r.get("tzid")
            res_num = r.get("number")
            if not res_num:
                time.sleep(1)
                res_num = osim.call_api("getState", tzid=res_id).get("number")

    if res_id and res_num:
        st.session_state['active_orders'].append({
            "id": res_id, "phone": res_num, "service": s_name, "source": source,
            "time": time.time(), "status": "Bekliyor", "code": None
        })
        st.toast(f"✅ {s_name} Alındı!")
    else: st.error(f"❌ Başarısız: {source}")

# --- ANA EKRAN ---
st.title("🇹🇷 Multi-Service SMS Panel")
tabs = st.tabs(["🐯 Tiger", "🔵 OnlineSim", "🦸 Hero"])

with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        cost, stock = tiger.get_info("yi")
        st.subheader("🍔 Yemeksepeti")
        st.write(f"💰 {cost} RUB | 📦 Stok: {stock}")
        if st.button("TIGER YEMEK", key="t1"): buy_num("tiger", "Yemeksepeti", "yi", "62")
    with c2:
        cost, stock = tiger.get_info("ub")
        st.subheader("🚗 Uber")
        st.write(f"💰 {cost} RUB | 📦 Stok: {stock}")
        if st.button("TIGER UBER", key="t2"): buy_num("tiger", "Uber", "ub", "62")

with tabs[1]:
    c1, c2, c3 = st.columns(3)
    with c1:
        cost, stock = osim.get_info("yemeksepeti")
        st.subheader("🍔 Yemeksepeti")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("OSIM YEMEK", key="o1"): buy_num("onlinesim", "Yemeksepeti", "yemeksepeti", "90")
    with c2:
        cost, stock = osim.get_info("uber")
        st.subheader("🚗 Uber")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("OSIM UBER", key="o2"): buy_num("onlinesim", "Uber", "uber", "90")
    with c3:
        cost, stock = osim.get_info("espressolab")
        st.subheader("☕ Espressolab")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("OSIM KAHVE", key="o3"): buy_num("onlinesim", "Espressolab", "espressolab", "90")

with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        cost, stock = hero.get_info("yi")
        st.subheader("🍔 Yemeksepeti")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("HERO YEMEK", key="h1"): buy_num("hero", "Yemeksepeti", "yi", "62")
    with c2:
        cost, stock = hero.get_info("ub")
        st.subheader("🚗 Uber")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("HERO UBER", key="h2"): buy_num("hero", "Uber", "ub", "62")

# --- İŞLEM TAKİBİ ---
st.divider()
st.subheader("📋 Aktif İşlemler")
to_remove = []

for order in st.session_state['active_orders']:
    elapsed = int(time.time() - order['time'])
    if order['code'] is None and elapsed >= AUTO_CANCEL_SEC:
        if order['source'] == "tiger": tiger.call_api("setStatus", id=order['id'], status=8)
        elif order['source'] == "hero": hero.call_api("setStatus", id=order['id'], status=8)
        else: osim.call_api("setOperationRevise", tzid=order['id'])
        to_remove.append(order['id'])
        continue

    with st.container(border=True):
        cols = st.columns([2, 2, 1])
        with cols[0]:
            st.write(f"**{order['service']}** ({order['source'].upper()})")
            if order['code'] is None:
                if order['source'] == "tiger":
                    res = tiger.call_api("getStatus", id=order['id'])
                    if "STATUS_OK" in res: order['code'] = res.split(":")[1]
                elif order['source'] == "hero":
                    res = hero.call_api("getStatus", id=order['id'])
                    if "STATUS_OK" in res: order['code'] = res.split(":")[1]
                else:
                    res = osim.call_api("getState", tzid=order['id'])
                    if str(res.get("response")) == "1" and "msg" in res: order['code'] = res['msg']
                
                if order['code']:
                    order['status'] = "✅ TAMAMLANDI"
                    send_telegram_instant(f"📩 <b>{order['service']}</b>\nKod: <code>{order['code']}</code>\nNumara: +{order['phone']}")
                    st.rerun()
                else: order['status'] = f"⌛ {elapsed}s"
            
            st.write(f"Durum: {order['status']}")
            if order['code']: st.success(f"KOD: **{order['code']}**")
        with cols[1]:
            st.code(f"+{order['phone']}")
        with cols[2]:
            if st.button("🗑️", key=f"del_{order['id']}"): to_remove.append(order['id'])

if to_remove:
    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] not in to_remove]
    st.rerun()

if canli_takip and st.session_state['active_orders']:
    time.sleep(2)
    st.rerun()
 
