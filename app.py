import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Multi-SMS Hunter", layout="wide", page_icon="🚀")

# --- KONFİGÜRASYON ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
except KeyError:
    st.error("🚨 Lütfen .streamlit/secrets.toml dosyasını kontrol edin!")
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

    def get_cheapest_info(self, service_code):
        res = self.call_api("getPrices", service=service_code)
        try:
            data = json.loads(res)
            if service_code in data:
                countries = data[service_code]
                # Stoku 0'dan büyük olanları filtrele
                available = {k: v for k, v in countries.items() if v.get('count', 0) > 0}
                if not available: 
                    return None, res # Stok yoksa ham veriyi de dön
                cheapest_id = min(available, key=lambda x: available[x]['cost'])
                return {"id": cheapest_id, "cost": available[cheapest_id]['cost']}, res
            return None, res
        except: 
            return None, res

# --- GİRİŞ EKRANI ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Güvenli SMS Paneli")
    pwd_input = st.text_input("Şifrenizi Girin:", type="password")
    if st.button("Giriş Yap"):
        if pwd_input.strip() == PANEL_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("❌ Hatalı şifre!")
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

# --- ANA EKRAN VE FİYAT SORGULAMA ---
st.title("🚀 Çoklu Numara Paneli")

# Fiyatları butonların üzerinde göstermek için sorguluyoruz
with st.spinner("Fiyatlar güncelleniyor..."):
    yem_info, _ = bot.get_cheapest_info("yi")
    ub_info, _ = bot.get_cheapest_info("ub")

yem_fiyat = f"({yem_info['cost']} RUB)" if yem_info else "(Stok Yok)"
ub_fiyat = f"({ub_info['cost']} RUB)" if ub_info else "(Stok Yok)"

col_yem, col_ub = st.columns(2)

def buy_process(s_name, s_code, info, raw_res):
    if info:
        num_res = bot.call_api("getNumber", service=s_code, country=info['id'])
        if "ACCESS_NUMBER" in num_res:
            parts = num_res.split(":")
            st.session_state['active_orders'].append({
                "id": parts[1], "phone": parts[2], "service": s_name,
                "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.success(f"✅ +{parts[2]} Alındı")
        else:
            st.error(f"Numara Alma Hatası: {num_res}")
    else:
        st.error("⚠️ Uygun stok bulunamadı!")
        with st.expander("API Detayını Gör"):
            st.code(raw_res)

if col_yem.button(f"🍔 YEMEKSEPETİ AL {yem_fiyat}", use_container_width=True):
    _, raw = bot.get_cheapest_info("yi")
    buy_process("Yemeksepeti", "yi", yem_info, raw)

if col_ub.button(f"🚗 UBER AL {ub_fiyat}", use_container_width=True):
    _, raw = bot.get_cheapest_info("ub")
    buy_process("Uber", "ub", ub_info, raw)

st.divider()

# --- LİSTELEME ---
st.subheader("📋 Aktif İşlemler")
for order in st.session_state['active_orders']:
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
        if order['code'] is None and "İptal" not in order['status']:
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
    time.sleep(2)
    st.rerun()
