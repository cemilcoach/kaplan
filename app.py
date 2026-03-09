import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Multi SMS Pro", layout="wide", page_icon="🇹🇷")

# --- GÜVENLİ VERİ ÇEKME (SECRETS) ---
try:
    # Tiger & Hero Keys
    API_KEY_TIGER = st.secrets["TIGER_API_KEY"]
    API_KEY_HERO = st.secrets["HERO_API_KEY"]
    
    # Genel Ayarlar
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except KeyError as e:
    st.error(f"🚨 Secrets dosyasında eksik değişken: {e}")
    st.info("Lütfen .streamlit/secrets.toml dosyanızı kontrol edin.")
    st.stop()

# Sabitler
TIGER_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
HERO_URL = "https://hero-sms.com/api"
TR_ID_TIGER = "62"
TR_ID_HERO = "tr"
AUTO_CANCEL_SEC = 135

class SMSManager:
    def __init__(self, t_key, h_key):
        self.t_key = t_key
        self.h_key = h_key

    def send_tg(self, msg):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        try: requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=5)
        except: pass

    # --- TIGER API ---
    def tiger_call(self, action, **kwargs):
        params = {"api_key": self.t_key, "action": action}
        params.update(kwargs)
        try:
            r = requests.get(TIGER_URL, params=params, timeout=10)
            return r.text
        except: return "ERROR"

    # --- HERO API ---
    def hero_call(self, action, **kwargs):
        params = {"api_key": self.h_key, "action": action}
        params.update(kwargs)
        try:
            r = requests.get(HERO_URL, params=params, timeout=10)
            return r.json()
        except: return {"status": "error"}

# --- SESSION STATE ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if 'orders' not in st.session_state: st.session_state['orders'] = []

# --- LOGIN ---
if not st.session_state["auth"]:
    st.title("🔒 SMS Panel Giriş")
    pwd = st.text_input("Şifre:", type="password")
    if st.button("Giriş", use_container_width=True):
        if pwd == PANEL_SIFRESI:
            st.session_state["auth"] = True
            st.rerun()
        else: st.error("Hatalı!")
    st.stop()

bot = SMSManager(API_KEY_TIGER, API_KEY_HERO)

# --- SIDEBAR ---
st.sidebar.title("🎮 Kontrol Merkezi")
t_res = bot.tiger_call("getBalance")
t_bal = t_res.split(":")[1] if "BALANCE" in t_res else "0"
st.sidebar.metric("🐯 Tiger Bakiio", f"{t_bal} RUB")

h_res = bot.hero_call("getBalance")
h_bal = h_res.get("balance", "0") if isinstance(h_res, dict) else "0"
st.sidebar.metric("🦸 Hero Bakiye", f"{h_bal} RUB")

live = st.sidebar.toggle("Canlı Takip", value=True)
if st.sidebar.button("Çıkış Yap"):
    st.session_state["auth"] = False
    st.rerun()

# --- ANA PANEL ---
st.title("📲 Pro SMS Otomasyon")

tab1, tab2 = st.tabs(["🐯 Tiger SMS (TR)", "🦸 Hero SMS (TR)"])

def add_order(prov, p_id, phone, service, s_code):
    st.session_state['orders'].append({
        "provider": prov, "id": p_id, "phone": phone, 
        "service": service, "s_code": s_code, 
        "start": time.time(), "code": None, "status": "Bekliyor"
    })

# --- TIGER SEKİMESİ ---
with tab1:
    c1, c2 = st.columns(2)
    services = {"Yemeksepeti": "yi", "Uber": "ub", "Getir": "gt", "Whatsapp": "wa"}
    for i, (name, code) in enumerate(services.items()):
        col = c1 if i % 2 == 0 else c2
        if col.button(f"Al: {name} (Tiger)", key=f"t_{code}", use_container_width=True):
            res = bot.tiger_call("getNumber", service=code, country=TR_ID_TIGER)
            if "ACCESS_NUMBER" in res:
                p = res.split(":")
                add_order("tiger", p[1], p[2], name, code)
                st.toast(f"Tiger {name} Alındı!")
            else: st.error(res)

# --- HERO SEKİMESİ ---
with tab2:
    h1, h2 = st.columns(2)
    # Hero servis kodlarını dökümanına göre düzenleyin (Örnek: yemeksepeti, uber)
    h_services = {"Yemeksepeti": "yemeksepeti", "Uber": "uber", "Getir": "getir"}
    for i, (name, code) in enumerate(h_services.items()):
        col = h1 if i % 2 == 0 else h2
        if col.button(f"Al: {name} (Hero)", key=f"h_{code}", use_container_width=True):
            res = bot.hero_call("getNumber", service=code, country=TR_ID_HERO)
            if res.get("status") == "success":
                add_order("hero", res["id"], res["number"], name, code)
                st.toast(f"Hero {name} Alındı!")
            else: st.error("Stok yok veya hata!")

# --- TAKİP ALANI ---
st.divider()
st.subheader("📋 Aktif Numaralar")

to_del = []
for order in st.session_state['orders']:
    elapsed = int(time.time() - order['start'])
    
    # Otomatik İptal Kontrolü
    if order['code'] is None and elapsed > AUTO_CANCEL_SEC:
        if order['provider'] == "tiger": bot.tiger_call("setStatus", id=order['id'], status=8)
        else: bot.hero_call("setStatus", id=order['id'], status="cancel")
        bot.send_tg(f"⚠️ İptal: {order['service']} (+{order['phone']})")
        to_del.append(order['id'])
        continue

    with st.container(border=True):
        col_m, col_p, col_btn = st.columns([3, 2, 1])
        
        with col_m:
            st.write(f"**{order['provider'].upper()} - {order['service']}**")
            if order['code'] is None:
                # Durum Sorgulama
                if order['provider'] == "tiger":
                    s = bot.tiger_call("getStatus", id=order['id'])
                    if "STATUS_OK" in s:
                        order['code'] = s.split(":")[1]
                        bot.tiger_call("setStatus", id=order['id'], status=6)
                else:
                    s = bot.hero_call("getStatus", id=order['id'])
                    if s.get("status") == "success" and s.get("code"):
                        order['code'] = s["code"]
                
                if order['code']:
                    bot.send_tg(f"📩 <b>KOD GELDİ!</b>\n{order['service']}: <code>{order['code']}</code>")
                
            st.write(f"Kod: `{order['code'] if order['code'] else 'Bekleniyor...'}`")
            st.caption(f"Süre: {elapsed}sn / {AUTO_CANCEL_SEC}sn")

        with col_p:
            st.code(f"+{order['phone']}")
            
        with col_btn:
            if st.button("🗑️", key=f"del_{order['id']}"):
                to_del.append(order['id'])

# Listeyi Güncelle
if to_del:
    st.session_state['orders'] = [o for o in st.session_state['orders'] if o['id'] not in to_del]
    st.rerun()

if live and len(st.session_state['orders']) > 0:
    time.sleep(4)
    st.rerun()
