import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Pro SMS Multi-Panel", layout="wide", page_icon="🇹🇷")

# --- KONFİGÜRASYON ---
try:
    TIGER_API_KEY = st.secrets["TIGER_API_KEY"]
    ONLINESIM_API_KEY = st.secrets["ONLINESIM_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except KeyError as e:
    st.error(f"🚨 Secrets dosyası eksik! Eksik anahtar: {e}")
    st.stop()

# API URL'leri
TIGER_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
ONLINESIM_BASE = "https://onlinesim.io/api/"
AUTO_CANCEL_SEC = 135 

# --- BOT SINIFLARI ---

class TigerSMSBot:
    def __init__(self, api_key):
        self.api_key = api_key

    def call_api(self, action, **kwargs):
        params = {"api_key": self.api_key, "action": action}
        params.update(kwargs)
        try:
            r = requests.get(TIGER_URL, params=params, timeout=10)
            return r.text
        except: return "ERROR"

    def get_tr_data(self, service_code):
        res = self.call_api("getPrices", service=service_code)
        try:
            data = json.loads(res)
            # Türkiye ID: 62
            if "62" in data and service_code in data["62"]:
                info = data["62"][service_code]
                return float(info.get('cost')), info.get('count')
            return None, 0
        except: return None, 0

class OnlineSimBot:
    def __init__(self, api_key):
        self.api_key = api_key

    def call_api(self, endpoint, **kwargs):
        params = {"apikey": self.api_key, "lang": "en"}
        params.update(kwargs)
        url = f"{ONLINESIM_BASE}{endpoint}.php"
        try:
            r = requests.get(url, params=params, timeout=10)
            return r.json()
        except Exception as e: 
            return {"response": "ERROR", "error": str(e)}

    def get_stock_data(self, country_id, service_name):
        # api_getTariffs_php endpoint'i stok ve fiyat verir
        res = self.call_api("getTariffs", country=country_id)
        try:
            if str(res.get("response")) == "1":
                # OnlineSim yapısında direkt servis adı üzerinden kontrol
                services = res.get("services", {})
                if service_name in services:
                    item = services[service_name]
                    return item.get("price"), item.get("count")
            return None, 0
        except: return None, 0

# --- YARDIMCI FONKSİYONLAR ---

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, data=payload, timeout=5)
    except: pass

# --- GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Pro Multi-SMS Panel Giriş")
    with st.form("login_form"):
        pwd_input = st.text_input("Şifre:", type="password")
        submit = st.form_submit_button("Giriş Yap", use_container_width=True)
        if submit:
            if pwd_input.strip() == PANEL_SIFRESI:
                st.session_state["authenticated"] = True
                st.rerun()
            else: st.error("❌ Hatalı Şifre!")
    st.stop()

# --- BAŞLATMA ---
tiger = TigerSMSBot(TIGER_API_KEY)
osim = OnlineSimBot(ONLINESIM_API_KEY)

if 'active_orders' not in st.session_state:
    st.session_state['active_orders'] = []

# --- SIDEBAR ---
st.sidebar.title("🤖 Panel Kontrol")

# Bakiyeler
try:
    t_bal_res = tiger.call_api("getBalance")
    t_bal = t_bal_res.split(":")[1] if "ACCESS_BALANCE" in t_bal_res else "0"
    st.sidebar.metric("🐯 Tiger Bakiye", f"{t_bal} RUB")
    
    o_bal_res = osim.call_api("getBalance")
    o_bal = o_bal_res.get("balance", "0") if str(o_bal_res.get("response")) == "1" else "0"
    st.sidebar.metric("🔵 OnlineSim Bakiye", f"{o_bal} $")
except:
    st.sidebar.error("Bakiye hatası!")

canli_takip = st.sidebar.toggle("🟢 Canlı Takip", value=True)
if st.sidebar.button("🚪 Çıkış", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA PANEL ---
st.title("🇹🇷 Multi-Service SMS Panel")

tab1, tab2 = st.tabs(["🐯 Tiger SMS", "☕ OnlineSim"])

def buy_number(source, s_name, s_code, country_id):
    if source == "tiger":
        res = tiger.call_api("getNumber", service=s_code, country=country_id)
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            st.session_state['active_orders'].append({
                "id": parts[1], "phone": parts[2], "service": s_name, "source": "tiger",
                "s_code": s_code, "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.toast(f"✅ {s_name} Alındı!")
        else: st.error(f"Hata: {res}")
    elif source == "onlinesim":
        res = osim.call_api("getNum", service=s_code, country=country_id)
        if str(res.get("response")) == "1":
            st.session_state['active_orders'].append({
                "id": res['tzid'], "phone": res['number'], "service": s_name, "source": "onlinesim",
                "s_code": s_code, "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.toast(f"✅ {s_name} Alındı!")
        else: st.error(f"OnlineSim Hatası: {res.get('response')}")

# TAB 1: TIGER SMS
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🍔 Yemeksepeti")
        y_cost, y_count = tiger.get_tr_data("yi")
        st.write(f"💰 **{y_cost} RUB** | 📦 Stok: **{y_count} Adet**")
        if st.button("YEMEKSEPETİ AL", key="tg_yi", use_container_width=True):
            buy_number("tiger", "Yemeksepeti", "yi", "62")
    with c2:
        st.subheader("🚗 Uber")
        u_cost, u_count = tiger.get_tr_data("ub")
        st.write(f"💰 **{u_cost} RUB** | 📦 Stok: **{u_count} Adet**")
        if st.button("UBER AL", key="tg_ub", use_container_width=True):
            buy_number("tiger", "Uber", "ub", "62")

# TAB 2: ONLINESIM (ESPRESSOLAB)
with tab2:
    st.subheader("☕ Espressolab (OnlineSim)")
    # OnlineSim'den Türkiye (90) Espressolab stok verisi çekme
    e_price, e_count = osim.get_stock_data("90", "espressolab")
    
    st.write(f"💰 **{e_price} $** | 📦 Stok: **{e_count} Adet**")
    
    if st.button("☕ ESPRESSOLAB AL (TR)", key="os_es", use_container_width=True):
        buy_number("onlinesim", "Espressolab", "espressolab", "90")

st.divider()

# --- İŞLEM TAKİBİ ---
st.subheader("📋 Aktif İşlemler")
to_remove = []

for order in st.session_state['active_orders']:
    elapsed = int(time.time() - order['time'])
    
    # OTOMATİK İPTAL
    if order['code'] is None and elapsed >= AUTO_CANCEL_SEC:
        if order['source'] == "tiger":
            tiger.call_api("setStatus", id=order['id'], status=8)
        else:
            osim.call_api("setOperationRevise", tzid=order['id'])
        to_remove.append(order['id'])
        continue

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.write(f"**{order['service']}** ({order['source'].upper()})")
            if order['code'] is None:
                if order['source'] == "tiger":
                    check = tiger.call_api("getStatus", id=order['id'])
                    if "STATUS_OK" in check:
                        order['code'] = check.split(":")[1]
                else:
                    check = osim.call_api("getState", tzid=order['id'])
                    if str(check.get("response")) == "1" and "msg" in check:
                        order['code'] = check['msg']

                if order['code']:
                    order['status'] = "✅ TAMAMLANDI"
                    send_telegram(f"📩 <b>SMS GELDİ!</b>\n{order['service']}: <code>{order['code']}</code>\n+{order['phone']}")
                else:
                    order['status'] = f"⌛ {elapsed//60:02d}:{elapsed%60:02d}"
            
            st.write(f"Durum: {order['status']}")
            if order['code']: st.success(f"KOD: **{order['code']}**")

        with c2:
            st.code(f"+{order['phone']}")
            # Temiz numara (kopyalama kolaylığı için)
            st.code(order['phone'][2:] if order['phone'].startswith("90") else order['phone'])

        with c3:
            if st.button("🗑️", key=f"del_{order['id']}"):
                if order['code'] is None:
                    if order['source'] == "tiger": tiger.call_api("setStatus", id=order['id'], status=8)
                    else: osim.call_api("setOperationRevise", tzid=order['id'])
                to_remove.append(order['id'])

# Temizlik ve Yenileme
if to_remove:
    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] not in to_remove]
    st.rerun()

if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(5)
    st.rerun()
