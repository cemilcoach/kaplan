import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Multi SMS Panel - Pro", layout="wide", page_icon="📲")

# --- KONFİGÜRASYON ---
try:
    # Tiger Secrets
    API_KEY_TIGER = st.secrets["TIGER_API_KEY"]
    # Hero SMS Secrets (Secrets kısmına eklemeyi unutmayın!)
    API_KEY_HERO = st.secrets["HERO_API_KEY"]
    
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except KeyError:
    st.error("🚨 Secrets dosyası eksik! TIGER_API_KEY ve HERO_API_KEY bilgilerini kontrol edin.")
    st.stop()

# API URL'leri
TIGER_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
HERO_URL = "https://hero-sms.com/api"
TR_ID = "62"
AUTO_CANCEL_SEC = 135 

class SMSBot:
    def __init__(self, tiger_key, hero_key):
        self.tiger_key = tiger_key
        self.hero_key = hero_key

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
        try: requests.post(url, data=payload, timeout=5)
        except: pass

    # --- TIGER SMS METODLARI ---
    def tiger_api(self, action, **kwargs):
        params = {"api_key": self.tiger_key, "action": action}
        params.update(kwargs)
        try:
            r = requests.get(TIGER_URL, params=params, timeout=10)
            return r.text
        except: return "ERROR"

    # --- HERO SMS METODLARI ---
    def hero_api(self, action, **kwargs):
        # Hero SMS genellikle POST veya GET ile 'api_key' parametresini bekler
        params = {"api_key": self.hero_key, "action": action}
        params.update(kwargs)
        try:
            r = requests.get(HERO_URL, params=params, timeout=10)
            return r.json() # Hero genellikle JSON döner
        except: return {"status": "error", "message": "Bağlantı Hatası"}

# --- GİRİŞ KONTROLÜ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Pro SMS Panel Giriş")
    pwd_input = st.text_input("Şifre:", type="password")
    if st.button("Giriş Yap", use_container_width=True):
        if pwd_input.strip() == PANEL_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("❌ Hatalı Şifre!")
    st.stop()

bot = SMSBot(API_KEY_TIGER, API_KEY_HERO)
if 'active_orders' not in st.session_state:
    st.session_state['active_orders'] = []

# --- SIDEBAR ---
st.sidebar.title("🤖 Panel Kontrol")

# Bakiyeleri Çekme
t_bal_res = bot.tiger_api("getBalance")
t_balance = t_bal_res.split(":")[1] if "ACCESS_BALANCE" in t_bal_res else "0"
st.sidebar.metric("💰 Tiger Bakiye", f"{t_balance} RUB")

h_bal_res = bot.hero_api("getBalance")
h_balance = h_bal_res.get("balance", "0") if isinstance(h_bal_res, dict) else "0"
st.sidebar.metric("💰 Hero Bakiye", f"{h_balance} RUB")

canli_takip = st.sidebar.toggle("🟢 Canlı Takip", value=True)

# --- ANA EKRAN SEKMELERİ ---
tab1, tab2 = st.tabs(["🐯 Tiger SMS", "🦸 Hero SMS"])

with tab1:
    st.header("Tiger SMS Servisleri")
    col1, col2 = st.columns(2)
    
    # Örnek Tiger Satın Alma Fonksiyonu (Eski mantık)
    def buy_tiger(s_name, s_code):
        res = bot.tiger_api("getNumber", service=s_code, country=TR_ID)
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            st.session_state['active_orders'].append({
                "id": parts[1], "phone": parts[2], "service": f"Tiger - {s_name}",
                "provider": "tiger", "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.toast(f"✅ {s_name} Alındı (Tiger)")
        else: st.error(f"Hata: {res}")

    with col1:
        if st.button("Tiger Yemeksepeti Al", use_container_width=True):
            buy_tiger("Yemeksepeti", "yi")
    with col2:
        if st.button("Tiger Uber Al", use_container_width=True):
            buy_tiger("Uber", "ub")

with tab2:
    st.header("Hero SMS Servisleri")
    st.info("Hero SMS API üzerinden Türkiye numaraları listeleniyor.")
    
    def buy_hero(s_name, s_code):
        # Hero API getNumber dökümanına göre düzenlenmiştir
        res = bot.hero_api("getNumber", service=s_code, country="tr") 
        if res.get("status") == "success":
            st.session_state['active_orders'].append({
                "id": res["id"], "phone": res["number"], "service": f"Hero - {s_name}",
                "provider": "hero", "time": time.time(), "status": "Bekliyor", "code": None
            })
            st.toast(f"✅ {s_name} Alındı (Hero)")
        else:
            st.error(f"Hero Hatası: {res.get('message', 'Bilinmeyen Hata')}")

    h_col1, h_col2 = st.columns(2)
    with h_col1:
        if st.button("Hero Yemeksepeti Al", use_container_width=True):
            buy_hero("Yemeksepeti", "yemeksepeti") # Servis kodunu hero'ya göre güncelleyin
    with h_col2:
        if st.button("Hero Uber Al", use_container_width=True):
            buy_hero("Uber", "uber")

# --- ORTAK İŞLEM TAKİBİ ---
st.divider()
st.subheader("📋 Aktif İşlemler (Tüm Sağlayıcılar)")

to_remove = []
for idx, order in enumerate(st.session_state['active_orders']):
    elapsed = int(time.time() - order['time'])
    
    # Otomatik İptal (Tiger & Hero için ortak)
    if order['code'] is None and elapsed >= AUTO_CANCEL_SEC:
        if order['provider'] == "tiger":
            bot.tiger_api("setStatus", id=order['id'], status=8)
        else:
            bot.hero_api("setStatus", id=order['id'], status="cancel")
            
        bot.send_telegram(f"⚠️ <b>OTOMATİK İPTAL</b>\n{order['service']} (+{order['phone']}) iptal edildi.")
        to_remove.append(order['id'])
        continue

    with st.container(border=True):
        c_info, c_copy, c_actions = st.columns([2, 2, 2])
        with c_info:
            st.write(f"**{order['service']}**")
            # SMS Kontrol
            if order['code'] is None:
                if order['provider'] == "tiger":
                    check = bot.tiger_api("getStatus", id=order['id'])
                    if "STATUS_OK" in check:
                        order['code'] = check.split(":")[1]
                        bot.tiger_api("setStatus", id=order['id'], status=6)
                else:
                    check = bot.hero_api("getStatus", id=order['id'])
                    if check.get("status") == "success" and check.get("code"):
                        order['code'] = check["code"]

                if order['code']:
                    order['status'] = "✅ TAMAMLANDI"
                    bot.send_telegram(f"📩 <b>SMS!</b> {order['service']}: {order['code']}")
                else:
                    order['status'] = f"⌛ {elapsed//60:02d}:{elapsed%60:02d}"
            
            st.write(f"Durum: {order['status']}")
            if order['code']: st.success(f"KOD: **{order['code']}**")

        with c_copy:
            st.code(f"+{order['phone']}")

        with c_actions:
            if st.button("🗑️", key=f"del_{order['id']}"):
                to_remove.append(order['id'])

# Temizleme ve Yenileme
if to_remove:
    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] not in to_remove]
    st.rerun()

if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(3)
    st.rerun()
