import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Tiger SMS - Pro Auto-Cancel", layout="wide", page_icon="ğŸ‡¹ğŸ‡·")

# --- KONFÄ°GÃœRASYON ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except KeyError:
    st.error("ğŸš¨ Secrets dosyasÄ± eksik! LÃ¼tfen Telegram ve API bilgilerini kontrol edin.")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"
TR_ID = "62"
AUTO_CANCEL_SEC = 135 # 2 Dakika 15 Saniye

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
        try: requests.post(url, data=payload, timeout=5)
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

# --- GÄ°RÄ°Å KONTROLÃœ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("ğŸ”’ Pro SMS Panel GiriÅŸ")
    pwd_input = st.text_input("Åifre:", type="password")
    if st.button("GiriÅŸ Yap", use_container_width=True):
        if pwd_input.strip() == PANEL_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("âŒ HatalÄ± Åifre!")
    st.stop()

bot = TigerSMSBot(API_KEY)
if 'active_orders' not in st.session_state:
    st.session_state['active_orders'] = []

# --- SIDEBAR ---
st.sidebar.title("ğŸ¤– Panel Kontrol")
balance_res = bot.call_api("getBalance")
balance = balance_res.split(":")[1] if "ACCESS_BALANCE" in balance_res else "0"
st.sidebar.metric("ğŸ’° Bakiyeniz", f"{balance} RUB")

if st.sidebar.button("ğŸ”” Telegram Botu Test Et", use_container_width=True):
    bot.send_telegram("<b>ğŸš€ Test MesajÄ±!</b>\nBaÄŸlantÄ± aktif.")
    st.sidebar.success("Test gÃ¶nderildi!")

canli_takip = st.sidebar.toggle("ğŸŸ¢ CanlÄ± Takip", value=True)

if st.sidebar.button("ğŸšª Ã‡Ä±kÄ±ÅŸ", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("ğŸ‡¹ğŸ‡· Tiger Pro SMS (Otomatik Ä°ptal Aktif)")

if st.button("ğŸ”„ StoklarÄ± GÃ¼ncelle", use_container_width=True):
    st.rerun()

def buy_process(s_name, s_code):
    num_res = bot.call_api("getNumber", service=s_code, country=TR_ID)
    if "ACCESS_NUMBER" in num_res:
        parts = num_res.split(":")
        st.session_state['active_orders'].append({
            "id": parts[1], "phone": parts[2], "service": s_name,
            "service_code": s_code, "time": time.time(), "status": "Bekliyor", "code": None
        })
        st.toast(f"âœ… {s_name} AlÄ±ndÄ±!", icon='ğŸ‡¹ğŸ‡·')
    else: st.error(f"Hata: {num_res}")

col_y, col_u = st.columns(2)
with col_y:
    st.header("ğŸ” Yemeksepeti")
    y_cost, y_count = bot.get_tr_62_data("yi")
    if y_cost:
        st.write(f"ğŸ’° {y_cost} RUB | ğŸ“¦ {y_count} Adet")
        if st.button("TR YEMEK AL", key="buy_yi_62", use_container_width=True):
            buy_process("Yemeksepeti", "yi")

with col_u:
    st.header("ğŸš— Uber")
    u_cost, u_count = bot.get_tr_62_data("ub")
    if u_cost:
        st.write(f"ğŸ’° {u_cost} RUB | ğŸ“¦ {u_count} Adet")
        if st.button("TR UBER AL", key="buy_ub_62", use_container_width=True):
            buy_process("Uber", "ub")

st.divider()

# --- AKTÄ°F Ä°ÅLEMLER ---
st.subheader("ğŸ“‹ Ä°ÅŸlem Takibi")

to_remove = []

for idx, order in enumerate(st.session_state['active_orders']):
    elapsed = int(time.time() - order['time'])
    
    # --- OTOMATÄ°K Ä°PTAL MANTIÄI ---
    if order['code'] is None and elapsed >= AUTO_CANCEL_SEC:
        bot.call_api("setStatus", id=order['id'], status=8) # API Ä°ptal
        bot.send_telegram(f"âš ï¸ <b>OTOMATÄ°K Ä°PTAL</b>\n{order['service']} (+{order['phone']}) numarasÄ±na 2:15 iÃ§inde SMS gelmediÄŸi iÃ§in iptal edildi.")
        to_remove.append(order['id'])
        continue

    with st.container(border=True):
        c_info, c_copy, c_actions = st.columns([2, 2, 2])
        
        with c_info:
            st.write(f"**{order['service']}**")
            if order['code'] is None:
                check = bot.call_api("getStatus", id=order['id'])
                if "STATUS_OK" in check:
                    order['code'] = check.split(":")[1]
                    order['status'] = "âœ… TAMAMLANDI"
                    bot.call_api("setStatus", id=order['id'], status=6)
                    bot.send_telegram(f"ğŸ“© <b>SMS GELDÄ°!</b>\n{order['service']}: <code>{order['code']}</code>\n+{order['phone']}")
                else:
                    order['status'] = f"âŒ› {elapsed//60:02d}:{elapsed%60:02d} / 02:15"
            
            st.write(f"Durum: {order['status']}")
            if order['code']: st.success(f"KOD: **{order['code']}**")

        with c_copy:
            st.code(f"+{order['phone']}", language="text")
            pure_phone = order['phone'][2:] if order['phone'].startswith("90") else order['phone']
            st.code(pure_phone, language="text")

        with c_actions:
            ca1, ca2, ca3 = st.columns(3)
            if ca1.button("â•", key=f"more_{order['id']}"):
                buy_process(order['service'], order['service_code'])
                st.rerun()
            
            if order['code'] is None:
                if ca2.button("âœ–ï¸", key=f"c_{order['id']}"):
                    bot.call_api("setStatus", id=order['id'], status=8)
                    to_remove.append(order['id'])
            
            if ca3.button("ğŸ—‘ï¸", key=f"d_{order['id']}"):
                to_remove.append(order['id'])

# Listeden temizle
if to_remove:
    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] not in to_remove]
    st.rerun()

# Ekran yenileme (Sadece aktif iÅŸlem varsa)
if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(2)
    st.rerun()
