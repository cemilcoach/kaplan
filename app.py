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
            # Dökümana göre JSON dönmesi bekleniyor
            return r.json()
        except Exception as e: 
            return {"response": "ERROR", "error": str(e)}

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

# Bakiyeleri try-except ile alalım ki API hatası tüm paneli dondurmasın
try:
    t_bal_res = tiger.call_api("getBalance")
    t_bal = t_bal_res.split(":")[1] if "ACCESS_BALANCE" in t_bal_res else "Hata"
    st.sidebar.metric("🐯 Tiger Bakiye", f"{t_bal} RUB")
    
    o_bal_res = osim.call_api("getBalance")
    # OnlineSim dökümanında getBalance JSON döner
    o_bal = o_bal_res.get("balance", "Hata") if str(o_bal_res.get("response")) == "1" else "Hata"
    st.sidebar.metric("🔵 OnlineSim Bakiye", f"{o_bal} RUB")
except:
    st.sidebar.error("Bakiye çekilemedi.")

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
        # OnlineSim api_getNum_php endpoint kullanımı
        res = osim.call_api("getNum", service=s_code, country=country_id)
        if str(res.get("response")) == "1":
            st.session_state['active_orders'].append({
                "id": res['tzid'], "phone": res['number'], "service": s_name, "source": "onlinesim",
                "s_code": s_code, "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.toast(f"✅ {s_name} Alındı!")
        else: st.error(f"OnlineSim Hatası: {res.get('response', 'Bilinmiyor')}")

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        y_cost, y_count = tiger.get_tr_data("yi")
        if st.button("🍔 YEMEKSEPETİ AL", key="tg_yi", use_container_width=True):
            buy_number("tiger", "Yemeksepeti", "yi", "62")
    with c2:
        u_cost, u_count = tiger.get_tr_data("ub")
        if st.button("🚗 UBER AL", key="tg_ub", use_container_width=True):
            buy_number("tiger", "Uber", "ub", "62")

with tab2:
    st.subheader("☕ Espressolab (OnlineSim)")
    # Espressolab için OnlineSim servis kodu 'espressolab'
    if st.button("☕ ESPRESSOLAB AL (TR)", key="os_es", use_container_width=True):
        buy_number("onlinesim", "Espressolab", "espressolab", "90")

st.divider()

# --- İŞLEM TAKİBİ ---
st.subheader("📋 Aktif İşlemler")
to_remove = []

for order in st.session_state['active_orders']:
    elapsed = int(time.time() - order['time'])
    
    if order['code'] is None and elapsed >= AUTO_CANCEL_SEC:
        if order['source'] == "tiger":
            tiger.call_api("setStatus", id=order['id'], status=8)
        else:
            # OnlineSim iptal için setOperationRevise kullanılır
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
                    # OnlineSim durum sorgulama
                    check = osim.call_api("getState", tzid=order['id'])
                    if str(check.get("response")) == "1" and "msg" in check:
                        order['code'] = check['msg']

                if order['code']:
                    order['status'] = "✅ TAMAMLANDI"
                    send_telegram(f"📩 <b>SMS!</b> {order['service']}: {order['code']}")
                else:
                    order['status'] = f"⌛ {elapsed}s / {AUTO_CANCEL_SEC}s"
            st.write(f"Durum: {order['status']}")
            if order['code']: st.success(f"KOD: {order['code']}")
        with c2:
            st.code(f"+{order['phone']}")
        with c3:
            if st.button("🗑️", key=f"del_{order['id']}"):
                to_remove.append(order['id'])

if to_remove:
    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] not in to_remove]
    st.rerun()

if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(5) # Yenileme süresini 5 saniyeye çıkararak yükü azalttık
    st.rerun()
