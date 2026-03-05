import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Multi-SMS Panel V3.2", layout="wide", page_icon="🇹🇷")

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
        """OnlineSim Türkiye (90) verisini çeker."""
        res = self.call_api("getTariffs", country="90")
        try:
            # OnlineSim'de veriler ülke kodu (90) altında döner
            if "90" in res:
                services = res["90"].get("services", {})
                for _, val in services.items():
                    if val.get("slug") == service_slug or val.get("service").lower() == service_slug.lower():
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
st.sidebar.title("💰 Bakiyeler")
try:
    t_bal = tiger.call_api("getBalance").split(":")[1]
    st.sidebar.metric("🐯 Tiger", f"{t_bal} RUB")
    o_bal_res = osim.call_api("getBalance")
    o_bal = o_bal_res.get("balance", "0") if str(o_bal_res.get("response")) == "1" else "0"
    st.sidebar.metric("🔵 OnlineSim", f"{o_bal} $")
    h_bal = hero.call_api("getBalance").split(":")[1]
    st.sidebar.metric("🦸 Hero-SMS", f"{h_bal} $")
except:
    st.sidebar.warning("Bakiye bilgisi alınamadı.")

canli_takip = st.sidebar.toggle("🟢 Canlı Takip", value=True)
if st.sidebar.button("🚪 Çıkış", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

# --- NUMARA ALMA FONKSİYONU ---
def buy_num(source, s_name, s_code, country):
    res_id, res_num = None, None
    raw_response = ""

    if source == "tiger":
        r = tiger.call_api("getNumber", service=s_code, country=country)
        raw_response = r
        if "ACCESS_NUMBER" in r:
            parts = r.split(":")
            res_id, res_num = parts[1], parts[2]
            
    elif source == "hero":
        r = hero.call_api("getNumber", service=s_code, country=country)
        raw_response = r
        if "ACCESS_NUMBER" in r:
            parts = r.split(":")
            res_id, res_num = parts[1], parts[2]
            
    elif source == "onlinesim":
        r = osim.call_api("getNum", service=s_code, country=country)
        raw_response = str(r)
        if str(r.get("response")) == "1" and "tzid" in r:
            res_id = r.get("tzid")
            res_num = r.get("number") # KeyError önlendi
            
            # Numara anında atanmamışsa bekle ve sorgula
            if not res_num:
                time.sleep(1)
                check = osim.call_api("getState", tzid=res_id)
                res_num = check.get("number")

    if res_id and res_num:
        st.session_state['active_orders'].append({
            "id": res_id, "phone": res_num, "service": s_name, "source": source,
            "time": time.time(), "status": "Bekliyor", "code": None
        })
        st.toast(f"✅ {s_name} Alındı ({source})")
    else:
        st.error(f"❌ Alım Başarısız ({source}): {raw_response}")

# --- ANA EKRAN ---
st.title("🇹🇷 Multi-Service SMS Panel")
tab1, tab2, tab3 = st.tabs(["🐯 Tiger SMS", "🔵 OnlineSim", "🦸 Hero-SMS"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        cost, stock = tiger.get_info("yi")
        st.subheader("🍔 Yemeksepeti")
        st.write(f"💰 {cost} RUB | 📦 Stok: {stock}")
        if st.button("TIGER YEMEK AL", key="t_yi"): buy_num("tiger", "Yemeksepeti", "yi", "62")
    with c2:
        cost, stock = tiger.get_info("ub")
        st.subheader("🚗 Uber")
        st.write(f"💰 {cost} RUB | 📦 Stok: {stock}")
        if st.button("TIGER UBER AL", key="t_ub"): buy_num("tiger", "Uber", "ub", "62")

with tab2:
    c1, c2, c3 = st.columns(3)
    with c1:
        cost, stock = osim.get_info("yemeksepeti")
        st.subheader("🍔 Yemeksepeti")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("OSIM YEMEK AL", key="o_yi"): buy_num("onlinesim", "Yemeksepeti", "yemeksepeti", "90")
    with c2:
        cost, stock = osim.get_info("uber")
        st.subheader("🚗 Uber")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("OSIM UBER AL", key="o_ub"): buy_num("onlinesim", "Uber", "uber", "90")
    with c3:
        cost, stock = osim.get_info("espressolab")
        st.subheader("☕ Espressolab")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("OSIM KAHVE AL", key="o_es"): buy_num("onlinesim", "Espressolab", "espressolab", "90")

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        cost, stock = hero.get_info("yi")
        st.subheader("🍔 Yemeksepeti")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("HERO YEMEK AL", key="h_yi"): buy_num("hero", "Yemeksepeti", "yi", "62")
    with c2:
        cost, stock = hero.get_info("ub")
        st.subheader("🚗 Uber")
        st.write(f"💰 {cost} $ | 📦 Stok: {stock}")
        if st.button("HERO UBER AL", key="h_ub"): buy_num("hero", "Uber", "ub", "62")

# --- İŞLEM TAKİBİ ---
st.divider()
st.subheader("📋 Aktif İşlemler")
to_remove = []

for order in st.session_state['active_orders']:
    elapsed = int(time.time() - order['time'])
    
    # OTOMATİK İPTAL
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
                    # Telegram bildirimi
                    try:
                        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": f"📩 {order['service']} Kod: {order['code']}"})
                    except: pass
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
    time.sleep(5)
    st.rerun()
