import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Tiger SMS - Sadece Türkiye", layout="centered", page_icon="🇹🇷")

# --- KONFİGÜRASYON ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
except KeyError:
    st.error("🚨 .streamlit/secrets.toml dosyası eksik!")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
# Paylaştığın veriye göre Türkiye ID'si 62. Bazı durumlarda 9 da olabilir.
TR_IDS = ["62", "9"] 

class TigerSMSBot:
    def __init__(self, api_key):
        self.api_key = api_key

    def call_api(self, action, **kwargs):
        params = {"api_key": self.api_key, "action": action}
        params.update(kwargs)
        try:
            r = requests.get(BASE_URL, params=params, timeout=10)
            return r.text
        except:
            return "ERROR"

    def get_tr_data(self, service_code):
        res = self.call_api("getPrices", service=service_code)
        try:
            data = json.loads(res)
            # JSON içinde TR_IDS listesindeki ID'leri tara
            for tr_id in TR_IDS:
                # Veri yapısı: data[ülke_id][servis_kodu]
                if tr_id in data and service_code in data[tr_id]:
                    info = data[tr_id][service_code]
                    return tr_id, info.get('cost'), info.get('count')
            return None, None, 0
        except:
            return None, None, 0

# --- GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🇹🇷 TR Panel Girişi")
    pwd_input = st.text_input("Şifre:", type="password")
    if st.button("Giriş Yap"):
        if pwd_input.strip() == PANEL_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("❌ Şifre Yanlış!")
    st.stop()

bot = TigerSMSBot(API_KEY)
if 'active_orders' not in st.session_state:
    st.session_state['active_orders'] = []

# --- SIDEBAR ---
balance_res = bot.call_api("getBalance")
balance = balance_res.split(":")[1] if "ACCESS_BALANCE" in balance_res else "0"
st.sidebar.metric("💰 Bakiyeniz", f"{balance} RUB")
canli_takip = st.sidebar.toggle("🟢 Canlı SMS Takibi", value=True)
if st.sidebar.button("🚪 Çıkış"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("🇹🇷 Türkiye Özel SMS Paneli")
st.info("Sadece Türkiye (TR) stokları listelenmektedir.")

col_y, col_u = st.columns(2)

def buy_tr(s_name, s_code, tr_id):
    with st.spinner("Numara alınıyor..."):
        num_res = bot.call_api("getNumber", service=s_code, country=tr_id)
        if "ACCESS_NUMBER" in num_res:
            parts = num_res.split(":")
            st.session_state['active_orders'].append({
                "id": parts[1], "phone": parts[2], "service": s_name,
                "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.success(f"✅ +{parts[2]} Alındı!")
        else:
            st.error(f"Hata: {num_res}")

# Yemeksepeti TR
with col_y:
    st.subheader("🍔 Yemeksepeti")
    tr_id, cost, count = bot.get_tr_data("yi")
    if tr_id:
        st.write(f"💰 Fiyat: **{cost} RUB**")
        st.write(f"📦 Stok: **{count} Adet**")
        if st.button("TR YEMEKSEPETİ SATIN AL", use_container_width=True):
            buy_tr("Yemeksepeti", "yi", tr_id)
    else:
        st.error("❌ Yemeksepeti TR Stokta Yok")

# Uber TR
with col_u:
    st.subheader("🚗 Uber")
    tr_id, cost, count = bot.get_tr_data("ub")
    if tr_id:
        st.write(f"💰 Fiyat: **{cost} RUB**")
        st.write(f"📦 Stok: **{count} Adet**")
        if st.button("TR UBER SATIN AL", use_container_width=True):
            buy_tr("Uber", "ub", tr_id)
    else:
        st.error("❌ Uber TR Stokta Yok")

st.divider()

# --- AKTİF İŞLEMLER ---
st.subheader("📋 İşlem Takibi")
for order in st.session_state['active_orders']:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"**{order['service']}**\n`+{order['phone']}`")
        
        if order['code'] is None:
            check = bot.call_api("getStatus", id=order['id'])
            if "STATUS_OK" in check:
                order['code'] = check.split(":")[1]; order['status'] = "✅ TAMAMLANDI"
                bot.call_api("setStatus", id=order['id'], status=6)
            elif "STATUS_WAIT_CODE" in check:
                ds = int(time.time() - order['time'])
                order['status'] = f"⌛ {ds//60:02d}:{ds%60:02d}"
        
        c2.write(f"**Durum:** {order['status']}")
        if order['code']: c2.success(f"**KOD: {order['code']}**")

        ks = max(0, 120 - int(time.time() - order['time']))
        if order['code'] is None:
            if ks > 0: c3.button(f"İptal ({ks}s)", key=f"w_{order['id']}", disabled=True)
            else:
                if c3.button("✖️ İptal Et", key=f"c_{order['id']}"):
                    bot.call_api("setStatus", id=order['id'], status=8)
                    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
                    st.rerun()
        
        if c4.button("🗑️", key=f"d_{order['id']}"):
            st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
            st.rerun()

if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(2); st.rerun()
