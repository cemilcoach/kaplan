import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Tiger SMS - TR 62 Panel", layout="wide", page_icon="🇹🇷")

# --- KONFİGÜRASYON ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
except KeyError:
    st.error("🚨 .streamlit/secrets.toml dosyası eksik!")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
TR_ID = "62" # Sadece bu kod aktif

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

    def get_tr_62_data(self, service_code):
        res = self.call_api("getPrices", service=service_code)
        try:
            data = json.loads(res)
            # Sadece ID 62 kontrolü
            if TR_ID in data and service_code in data[TR_ID]:
                info = data[TR_ID][service_code]
                return float(info.get('cost')), info.get('count')
            return None, 0
        except:
            return None, 0

# --- GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 TR 62 Panel Giriş")
    pwd_input = st.text_input("Şifre:", type="password")
    if st.button("Giriş Yap"):
        if pwd_input.strip() == PANEL_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("❌ Hatalı Şifre!")
    st.stop()

bot = TigerSMSBot(API_KEY)
if 'active_orders' not in st.session_state:
    st.session_state['active_orders'] = []

# --- SIDEBAR ---
balance_res = bot.call_api("getBalance")
balance = balance_res.split(":")[1] if "ACCESS_BALANCE" in balance_res else "0"
st.sidebar.metric("💰 Bakiyeniz", f"{balance} RUB")
canli_takip = st.sidebar.toggle("🟢 Kod Takibi", value=True)
if st.sidebar.button("🚪 Çıkış"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("🇹🇷 Türkiye (ID: 62) Numara Paneli")

# MANUEL YENİLEME BUTONU
if st.button("🔄 Stokları ve Fiyatları Güncelle", use_container_width=True):
    st.rerun()

def buy_process(s_name, s_code):
    num_res = bot.call_api("getNumber", service=s_code, country=TR_ID)
    if "ACCESS_NUMBER" in num_res:
        parts = num_res.split(":")
        st.session_state['active_orders'].append({
            "id": parts[1], "phone": parts[2], "service": s_name,
            "service_code": s_code, "time": time.time(), "status": "Bekliyor", "code": None
        })
        st.toast(f"✅ TR {s_name} Alındı!", icon='🇹🇷')
    else:
        st.error(f"Hata: {num_res}")

col_y, col_u = st.columns(2)

# Yemeksepeti
with col_y:
    st.header("🍔 Yemeksepeti")
    y_cost, y_count = bot.get_tr_62_data("yi")
    with st.container(border=True):
        if y_cost:
            st.write(f"💰 Fiyat: **{y_cost} RUB**")
            st.write(f"📦 Stok: **{y_count} Adet**")
            if st.button("TR YEMEK AL", key="buy_yi_62", use_container_width=True):
                buy_process("Yemeksepeti", "yi")
        else:
            st.warning("Yemeksepeti TR (62) stokta yok.")

# Uber
with col_u:
    st.header("🚗 Uber")
    u_cost, u_count = bot.get_tr_62_data("ub")
    with st.container(border=True):
        if u_cost:
            st.write(f"💰 Fiyat: **{u_cost} RUB**")
            st.write(f"📦 Stok: **{u_count} Adet**")
            if st.button("TR UBER AL", key="buy_ub_62", use_container_width=True):
                buy_process("Uber", "ub")
        else:
            st.warning("Uber TR (62) stokta yok.")

st.divider()

# --- AKTİF İŞLEMLER ---
st.subheader("📋 İşlem Takibi")
for order in st.session_state['active_orders']:
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
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
        if order['code']: c2.success(f"**{order['code']}**")

        # HIZLI AL (Aynı servisten bir tane daha)
        if c3.button("➕", key=f"more_{order['id']}", help="Aynı servisten bir numara daha al"):
            buy_process(order['service'], order['service_code'])
            st.rerun()

        # İPTAL
        ks = max(0, 120 - int(time.time() - order['time']))
        if order['code'] is None:
            if ks > 0: c4.button(f"⌛{ks}s", key=f"w_{order['id']}", disabled=True)
            else:
                if c4.button("✖️", key=f"c_{order['id']}"):
                    bot.call_api("setStatus", id=order['id'], status=8)
                    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
                    st.rerun()
        
        # SİL
        if c5.button("🗑️", key=f"d_{order['id']}"):
            st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
            st.rerun()

if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(2); st.rerun()
