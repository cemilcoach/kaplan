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
        except: return {"response": "ERROR"}

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
    pwd_input = st.text_input("Şifre:", type="password")
    if st.button("Giriş Yap", use_container_width=True):
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

# Bakiye Bilgileri
t_bal_res = tiger.call_api("getBalance")
t_bal = t_bal_res.split(":")[1] if "ACCESS_BALANCE" in t_bal_res else "0"
st.sidebar.metric("🐯 Tiger Bakiye", f"{t_bal} RUB")

o_bal_res = osim.call_api("getBalance")
o_bal = o_bal_res.get("balance", "0") if o_bal_res.get("response") == "1" else "0"
st.sidebar.metric("🔵 OnlineSim Bakiye", f"{o_bal} RUB")

canli_takip = st.sidebar.toggle("🟢 Canlı Takip", value=True)
if st.sidebar.button("🚪 Çıkış"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA PANEL ---
st.title("🇹🇷 Multi-Service SMS Panel")

tab1, tab2 = st.tabs(["🐯 Tiger SMS (Yemek/Uber)", "☕ OnlineSim (Espressolab)"])

# NUMARA ALMA FONKSİYONU
def buy_number(source, s_name, s_code, country_id):
    if source == "tiger":
        res = tiger.call_api("getNumber", service=s_code, country=country_id)
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            st.session_state['active_orders'].append({
                "id": parts[1], "phone": parts[2], "service": s_name, "source": "tiger",
                "s_code": s_code, "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.toast(f"✅ {s_name} (Tiger) Alındı!")
        else: st.error(f"Tiger Hatası: {res}")
    
    elif source == "onlinesim":
        res = osim.call_api("getNum", service=s_code, country=country_id)
        if res.get("response") == "1":
            st.session_state['active_orders'].append({
                "id": res['tzid'], "phone": res['number'], "service": s_name, "source": "onlinesim",
                "s_code": s_code, "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.toast(f"✅ {s_name} (OnlineSim) Alındı!")
        else: st.error(f"OnlineSim Hatası: {res}")

# TAB 1: TIGER SMS
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        y_cost, y_count = tiger.get_tr_data("yi")
        st.subheader("🍔 Yemeksepeti")
        st.write(f"Fiyat: {y_cost} RUB | Stok: {y_count}")
        if st.button("YEMEKSEPETİ AL", key="tg_yi"):
            buy_number("tiger", "Yemeksepeti", "yi", "62")
    
    with col2:
        u_cost, u_count = tiger.get_tr_data("ub")
        st.subheader("🚗 Uber")
        st.write(f"Fiyat: {u_cost} RUB | Stok: {u_count}")
        if st.button("UBER AL", key="tg_ub"):
            buy_number("tiger", "Uber", "ub", "62")

# TAB 2: ONLINESIM (ESPRESSOLAB)
with tab2:
    st.subheader("☕ Espressolab Özel Bölümü")
    st.info("OnlineSim üzerinden Espressolab numarası alır.")
    # OnlineSim'de Espressolab kodu genelde 'espressolab'dır. 
    # Türkiye kodu genelde '90' veya '7'dir (API dökümanından kontrol edilmelidir).
    if st.button("☕ ESPRESSOLAB AL (TR)", use_container_width=True):
        buy_number("onlinesim", "Espressolab", "espressolab", "90")

st.divider()

# --- İŞLEM TAKİBİ ---
st.subheader("📋 Aktif İşlemler")
to_remove = []

for idx, order in enumerate(st.session_state['active_orders']):
    elapsed = int(time.time() - order['time'])
    
    # OTOMATİK İPTAL
    if order['code'] is None and elapsed >= AUTO_CANCEL_SEC:
        if order['source'] == "tiger":
            tiger.call_api("setStatus", id=order['id'], status=8)
        else:
            osim.call_api("setOperationRevise", tzid=order['id'])
        
        send_telegram(f"⚠️ <b>OTOMATİK İPTAL</b>\n{order['service']} (+{order['phone']}) zaman aşımı.")
        to_remove.append(order['id'])
        continue

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        
        with c1:
            st.write(f"**{order['service']}** ({order['source'].upper()})")
            # KOD KONTROLÜ
            if order['code'] is None:
                if order['source'] == "tiger":
                    check = tiger.call_api("getStatus", id=order['id'])
                    if "STATUS_OK" in check:
                        order['code'] = check.split(":")[1]
                        tiger.call_api("setStatus", id=order['id'], status=6)
                else:
                    check = osim.call_api("getState", tzid=order['id'])
                    if check.get("response") == "1" and "msg" in check:
                        order['code'] = check['msg']
                        osim.call_api("setOperationOk", tzid=order['id'])

                if order['code']:
                    order['status'] = "✅ TAMAMLANDI"
                    send_telegram(f"📩 <b>SMS GELDİ!</b>\n{order['service']}: <code>{order['code']}</code>\n+{order['phone']}")
                else:
                    order['status'] = f"⌛ {elapsed//60:02d}:{elapsed%60:02d}"

            st.write(f"Durum: {order['status']}")
            if order['code']: st.success(f"KOD: {order['code']}")

        with c2:
            st.code(f"+{order['phone']}")
            
        with c3:
            if st.button("🗑️", key=f"del_{order['id']}"):
                to_remove.append(order['id'])

# Temizlik
if to_remove:
    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] not in to_remove]
    st.rerun()

# Otomatik Yenileme
if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(3)
    st.rerun()
