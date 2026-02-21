import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Tiger SMS - Pro Panel", layout="wide", page_icon="🇹🇷")

# --- KONFİGÜRASYON ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except KeyError:
    st.error("🚨 Secrets dosyası eksik! Lütfen Telegram bilgilerini ekleyin.")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
TR_ID = "62"

class TigerSMSBot:
    def __init__(self, api_key):
        self.api_key = api_key

    def call_api(self, action, **kwargs):
        params = {"api_key": self.api_key, "action": action}
        params.update(kwargs)
        try:
            r = requests.get(BASE_URL, params=params, timeout=10)
            return r.text
        except: return "ERROR"

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
        try: requests.post(url, data=payload)
        except: pass

    def get_tr_62_data(self, service_code):
        res = self.call_api("getPrices", service=service_code)
        try:
            data = json.loads(res)
            if TR_ID in data and service_code in data[TR_ID]:
                info = data[TR_ID][service_code]
                return float(info.get('cost')), info.get('count')
            return None, 0
        except: return None, 0

# --- GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Pro SMS Panel Giriş")
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
canli_takip = st.sidebar.toggle("🟢 Canlı Takip", value=True)
if st.sidebar.button("🚪 Çıkış"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("🇹🇷 Tiger Pro SMS Paneli")

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
        st.toast(f"✅ {s_name} Alındı!", icon='🇹🇷')
    else: st.error(f"Hata: {num_res}")

col_y, col_u = st.columns(2)
with col_y:
    st.header("🍔 Yemeksepeti")
    y_cost, y_count = bot.get_tr_62_data("yi")
    with st.container(border=True):
        if y_cost:
            st.write(f"💰 {y_cost} RUB | 📦 {y_count} Adet")
            if st.button("TR YEMEK AL", key="buy_yi_62", use_container_width=True):
                buy_process("Yemeksepeti", "yi")
        else: st.warning("Stok Yok")

with col_u:
    st.header("🚗 Uber")
    u_cost, u_count = bot.get_tr_62_data("ub")
    with st.container(border=True):
        if u_cost:
            st.write(f"💰 {u_cost} RUB | 📦 {u_count} Adet")
            if st.button("TR UBER AL", key="buy_ub_62", use_container_width=True):
                buy_process("Uber", "ub")
        else: st.warning("Stok Yok")

st.divider()

# --- AKTİF İŞLEMLER ---
st.subheader("📋 İşlem Takibi")
for order in st.session_state['active_orders']:
    with st.container(border=True):
        c_info, c_copy, c_actions = st.columns([2, 2, 2])
        
        # 1. Bilgi Alanı
        c_info.write(f"**{order['service']}**\n`+{order['phone']}`")
        if order['code'] is None:
            check = bot.call_api("getStatus", id=order['id'])
            if "STATUS_OK" in check:
                order['code'] = check.split(":")[1]
                order['status'] = "✅ TAMAMLANDI"
                bot.call_api("setStatus", id=order['id'], status=6)
                # TELEGRAM BİLDİRİMİ
                msg = f"<b>📩 SMS GELDİ!</b>\n\n<b>Servis:</b> {order['service']}\n<b>Numara:</b> +{order['phone']}\n<b>KOD:</b> <code>{order['code']}</code>"
                bot.send_telegram(msg)
            elif "STATUS_WAIT_CODE" in check:
                ds = int(time.time() - order['time'])
                order['status'] = f"⌛ {ds//60:02d}:{ds%60:02d}"
        c_info.write(f"Durum: {order['status']}")
        if order['code']: c_info.success(f"KOD: **{order['code']}**")

        # 2. Kopyalama Butonları
        with c_copy:
            st.write("📋 Numarayı Kopyala")
            # Ülke Kodlu (+90)
            st.code(f"+{order['phone']}", language="text")
            # Kodsuz (Sadece numara) - Türkiye için 90'ı siliyoruz
            pure_phone = order['phone'][2:] if order['phone'].startswith("90") else order['phone']
            st.code(pure_phone, language="text")

        # 3. İşlem Butonları (Hızlı Al, İptal, Sil)
        with c_actions:
            ca1, ca2, ca3 = st.columns(3)
            ca1.button("➕", key=f"more_{order['id']}", on_click=buy_process, args=(order['service'], order['service_code']))
            
            ks = max(0, 120 - int(time.time() - order['time']))
            if order['code'] is None:
                if ks > 0: ca2.button(f"{ks}s", key=f"w_{order['id']}", disabled=True)
                else:
                    if ca2.button("✖️", key=f"c_{order['id']}"):
                        bot.call_api("setStatus", id=order['id'], status=8)
                        st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
                        st.rerun()
            if ca3.button("🗑️", key=f"d_{order['id']}"):
                st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
                st.rerun()

if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(2); st.rerun()
