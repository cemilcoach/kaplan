import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Tiger SMS - Manuel Seçim", layout="wide", page_icon="🌍")

# --- KONFİGÜRASYON ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
except KeyError:
    st.error("🚨 .streamlit/secrets.toml dosyası eksik!")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"

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

    def get_full_stock_list(self, service_code):
        res = self.call_api("getPrices", service=service_code)
        stock_list = []
        try:
            data = json.loads(res)
            # YENİ MANTIK: Gelen veride her ülkeyi tek tek geziyoruz
            for country_id, services in data.items():
                # Eğer servis kodu bu ülkenin içinde varsa
                if service_code in services:
                    info = services[service_code]
                    if info.get('count', 0) > 0:
                        stock_list.append({
                            "id": country_id,
                            "fiyat": float(info.get('cost')),
                            "stok": info.get('count')
                        })
            # Fiyata göre en ucuzdan en pahalıya sırala
            return sorted(stock_list, key=lambda x: x['fiyat']), res
        except:
            return [], res

# --- GİRİŞ EKRANI ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Güvenli SMS Paneli")
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
canli_takip = st.sidebar.toggle("🟢 Canlı SMS Takibi", value=True)
if st.sidebar.button("🚪 Çıkış"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("🌍 Manuel Sağlayıcı Seçimi")

service_map = {"Yemeksepeti": "yi", "Uber": "ub"}
selected_service_name = st.radio("Bir servis seçin:", list(service_map.keys()), horizontal=True)
selected_code = service_map[selected_service_name]

if st.button(f"🔍 {selected_service_name} Sağlayıcılarını Listele"):
    st.session_state['last_service_code'] = selected_code
    st.session_state['last_service_name'] = selected_service_name
    st.rerun()

st.divider()

# Sağlayıcı Listesini Göster
if 'last_service_code' in st.session_state:
    s_code = st.session_state['last_service_code']
    s_name = st.session_state['last_service_name']
    stocks, raw = bot.get_full_stock_list(s_code)
    
    if stocks:
        st.subheader(f"📍 {s_name} İçin Mevcut Ülkeler")
        cols = st.columns(4) # Daha geniş görünüm için 4 kolon
        for idx, item in enumerate(stocks):
            with cols[idx % 4]:
                with st.container(border=True):
                    # Türkiye vurgusu (ID 62 veya 9 olabilir, Tiger bazen değiştiriyor)
                    label = "🇹🇷 TÜRKİYE" if item['id'] in ["62", "9"] else f"🌍 Ülke ID: {item['id']}"
                    st.write(f"**{label}**")
                    st.write(f"💰 {item['fiyat']} RUB")
                    st.write(f"📦 Stok: {item['stok']}")
                    
                    if st.button(f"Satın Al", key=f"buy_{item['id']}_{idx}"):
                        num_res = bot.call_api("getNumber", service=s_code, country=item['id'])
                        if "ACCESS_NUMBER" in num_res:
                            parts = num_res.split(":")
                            st.session_state['active_orders'].append({
                                "id": parts[1], "phone": parts[2], "service": s_name,
                                "time": time.time(), "status": "Bekliyor", "code": None
                            })
                            st.success(f"✅ +{parts[2]} Alındı!")
                        else:
                            st.error(f"Hata: {num_res}")
    else:
        st.warning("Stok bulunamadı.")
        with st.expander("Ham Veriyi Gör"):
            st.code(raw)

st.divider()

# --- AKTİF İŞLEMLER (Kalıcı Liste) ---
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
