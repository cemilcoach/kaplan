import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Tiger SMS - Profesyonel TR Panel", layout="wide", page_icon="🇹🇷")

# --- KONFİGÜRASYON ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
except KeyError:
    st.error("🚨 .streamlit/secrets.toml dosyası eksik!")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
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

    def get_tr_all_options(self, service_code):
        # Tüm fiyat seçeneklerini görmek için geniş sorgu
        res = self.call_api("getPrices", service=service_code)
        options = []
        try:
            data = json.loads(res)
            for tr_id in TR_IDS:
                if tr_id in data and service_code in data[tr_id]:
                    info = data[tr_id][service_code]
                    if info.get('count', 0) > 0:
                        options.append({
                            "tr_id": tr_id,
                            "cost": float(info.get('cost')),
                            "count": info.get('count')
                        })
            return sorted(options, key=lambda x: x['cost']), res
        except:
            return [], res

# --- GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Profesyonel TR Panel Giriş")
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
canli_takip = st.sidebar.toggle("🟢 Canlı Takip (Yenileme)", value=True)
if st.sidebar.button("🚪 Çıkış"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("🇹🇷 Türkiye Özel Servis Seçimi")

def buy_process(s_name, s_code, tr_id):
    num_res = bot.call_api("getNumber", service=s_code, country=tr_id)
    if "ACCESS_NUMBER" in num_res:
        parts = num_res.split(":")
        st.session_state['active_orders'].append({
            "id": parts[1], "phone": parts[2], "service": s_name,
            "service_code": s_code, "tr_id": tr_id,
            "time": time.time(), "status": "Bekliyor", "code": None
        })
        st.toast(f"✅ +{parts[2]} başarıyla eklendi!", icon='🎉')
    else:
        st.error(f"Hata: {num_res}")

col_y, col_u = st.columns(2)

# Yemeksepeti Bölümü
with col_y:
    st.header("🍔 Yemeksepeti (TR)")
    y_options, _ = bot.get_tr_all_options("yi")
    if y_options:
        for opt in y_options:
            with st.container(border=True):
                c_btn, c_txt = st.columns([1, 2])
                if c_btn.button(f"AL", key=f"buy_yi_{opt['tr_id']}_{opt['cost']}"):
                    buy_process("Yemeksepeti", "yi", opt['tr_id'])
                c_txt.write(f"💰 **{opt['cost']} RUB** | 📦 Stok: **{opt['count']}**")
    else:
        st.warning("Yemeksepeti TR stokta yok.")

# Uber Bölümü
with col_u:
    st.header("🚗 Uber (TR)")
    u_options, _ = bot.get_tr_all_options("ub")
    if u_options:
        for opt in u_options:
            with st.container(border=True):
                c_btn, c_txt = st.columns([1, 2])
                if c_btn.button(f"AL", key=f"buy_ub_{opt['tr_id']}_{opt['cost']}"):
                    buy_process("Uber", "ub", opt['tr_id'])
                c_txt.write(f"💰 **{opt['cost']} RUB** | 📦 Stok: **{opt['count']}**")
    else:
        st.warning("Uber TR stokta yok.")

st.divider()

# --- AKTİF İŞLEMLER ---
st.subheader("📋 Aktif Numaralar ve Hızlı İşlemler")

for order in st.session_state['active_orders']:
    with st.container(border=True):
        # 5 kolonlu yapı: Servis/Numara, Durum/Kod, Hızlı Al, İptal, Sil
        c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
        
        c1.write(f"**{order['service']}**\n\n`+{order['phone']}`")
        
        # Kod Sorgulama
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

        # 1. HIZLI AL TUŞU (Aynı servisten bir tane daha)
        if c3.button("➕ Yeni", key=f"more_{order['id']}", help=f"Aynı servisten ({order['service']}) bir numara daha al"):
            buy_process(order['service'], order['service_code'], order['tr_id'])
            st.rerun()

        # 2. İPTAL TUŞU
        ks = max(0, 120 - int(time.time() - order['time']))
        if order['code'] is None:
            if ks > 0:
                c4.button(f"⌛ {ks}s", key=f"w_{order['id']}", disabled=True)
            else:
                if c4.button("✖️", key=f"c_{order['id']}", help="İptal Et ve İade Al"):
                    bot.call_api("setStatus", id=order['id'], status=8)
                    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
                    st.rerun()
        
        # 3. ÇÖP KOVASI (Listeden Sil)
        if c5.button("🗑️", key=f"d_{order['id']}", help="Listeden Kaldır"):
            st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
            st.rerun()

if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(2); st.rerun()
 
