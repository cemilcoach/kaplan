import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Tiger SMS TR Hunter", layout="centered", page_icon="🇹🇷")

# --- KONFİGÜRASYON ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
except KeyError:
    st.error("🚨 Lütfen .streamlit/secrets.toml dosyasını kontrol edin!")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
TR_ID = "9" # Tiger SMS Türkiye Ülke Kodu

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

    def get_tr_stock(self, service_code):
        # Sadece Türkiye (ID: 9) fiyat ve stok bilgisini çeker
        res = self.call_api("getPrices", service=service_code, country=TR_ID)
        try:
            data = json.loads(res)
            # Yanıt formatı: {"service": {"9": {"cost": X, "count": Y}}}
            if service_code in data and TR_ID in data[service_code]:
                info = data[service_code][TR_ID]
                return info.get('cost'), info.get('count')
            return None, 0
        except:
            return None, 0

# --- GİRİŞ EKRANI ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🇹🇷 TR SMS Paneli Giriş")
    pwd_input = st.text_input("Şifre:", type="password")
    if st.button("Giriş Yap"):
        if pwd_input.strip() == PANEL_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("❌ Hatalı!")
    st.stop()

bot = TigerSMSBot(API_KEY)
if 'active_orders' not in st.session_state:
    st.session_state['active_orders'] = []

# --- SIDEBAR ---
balance_res = bot.call_api("getBalance")
balance = balance_res.split(":")[1] if "ACCESS_BALANCE" in balance_res else "0"
st.sidebar.metric("💰 Bakiyeniz", f"{balance} RUB")
canli_takip = st.sidebar.toggle("🟢 Otomatik SMS Takibi", value=True)
if st.sidebar.button("🚪 Çıkış"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("🇹🇷 Türkiye Özel SMS Paneli")

# TR Fiyat ve Stok Sorgulama
with st.spinner("Türkiye stokları kontrol ediliyor..."):
    y_cost, y_count = bot.get_tr_stock("yi")
    u_cost, u_count = bot.get_tr_stock("ub")

st.divider()

col_y, col_u = st.columns(2)

def tr_buy(s_name, s_code, count):
    if count > 0:
        num_res = bot.call_api("getNumber", service=s_code, country=TR_ID)
        if "ACCESS_NUMBER" in num_res:
            parts = num_res.split(":")
            st.session_state['active_orders'].append({
                "id": parts[1], "phone": parts[2], "service": s_name,
                "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.success(f"✅ TR {s_name} numarası alındı!")
        else:
            st.error(f"Hata: {num_res}")
    else:
        st.error("❌ Türkiye stokta şu an numara yok!")

# Yemeksepeti Kartı
with col_y:
    st.subheader("🍔 Yemeksepeti")
    st.write(f"💰 Fiyat: **{y_cost if y_cost else '--'} RUB**")
    st.write(f"📦 Stok: **{y_count} Adet**")
    if st.button("TR NUMARA AL (YEMEK)", use_container_width=True, disabled=(y_count == 0)):
        tr_buy("Yemeksepeti", "yi", y_count)

# Uber Kartı
with col_u:
    st.subheader("🚗 Uber")
    st.write(f"💰 Fiyat: **{u_cost if u_cost else '--'} RUB**")
    st.write(f"📦 Stok: **{u_count} Adet**")
    if st.button("TR NUMARA AL (UBER)", use_container_width=True, disabled=(u_count == 0)):
        tr_buy("Uber", "ub", u_count)

st.divider()

# --- AKTİF İŞLEMLER ---
st.subheader("📋 Aktif Numaralar")
for idx, order in enumerate(st.session_state['active_orders']):
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"**{order['service']}**\n\n`+{order['phone']}`")
        
        if order['code'] is None:
            check = bot.call_api("getStatus", id=order['id'])
            if "STATUS_OK" in check:
                order['code'] = check.split(":")[1]
                order['status'] = "✅ TAMAMLANDI"
                bot.call_api("setStatus", id=order['id'], status=6)
            elif "STATUS_WAIT_CODE" in check:
                ds = int(time.time() - order['time'])
                order['status'] = f"⌛ {ds//60:02d}:{ds%60:02d}"
        
        c2.write(f"**Durum:** {order['status']}")
        if order['code']: c2.success(f"**KOD: {order['code']}**")

        gs = time.time() - order['time']
        ks = max(0, 120 - int(gs))
        
        # İptal butonu 2 dk dolana kadar pasif
        if order['code'] is None and "İptal" not in order['status']:
            if ks > 0:
                c3.button(f"İptal ({ks}s)", key=f"w_{order['id']}", disabled=True)
            else:
                if c3.button("✖️ İptal Et", key=f"c_{order['id']}"):
                    bot.call_api("setStatus", id=order['id'], status=8)
                    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
                    st.rerun()
        
        if c4.button("🗑️", key=f"d_{order['id']}"):
            st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
            st.rerun()

if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(2)
    st.rerun()
