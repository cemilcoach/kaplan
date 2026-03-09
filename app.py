import streamlit as st
import requests
import time
import json

# Mobil uyumluluk
st.markdown("""
    <style>
        input, button, select, textarea { font-size: 16px !important; }
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
""", unsafe_allow_html=True)

# Authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Panel Şifresi:", type="password", key="auth_input")
    if st.button("Giriş Yap"):
        if password == st.secrets["PANEL_SIFRESI"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Yanlış şifre!")
    st.stop()

# Secrets
api_key = st.secrets.get("HERO_API_KEY", "test_key")
tg_token = st.secrets.get("TELEGRAM_TOKEN", "test_token")
tg_chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "test_chat")

base_url = "https://hero-sms.com/stubs/handler_api.php"

def api_request(params):
    try:
        params["api_key"] = api_key
        r = requests.get(base_url, params=params, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        st.error(f"API hatası: {e}")
        return None

def get_balance():
    text = api_request({"action": "getBalance"})
    if text and text.startswith("ACCESS_BALANCE:"):
        return float(text.split(":")[1])
    return None

def get_prices(country="90"):
    text = api_request({"action": "getPrices", "country": country})
    if not text:
        return {"ub": {"cost":"N/A","count":"N/A"}, "yi": {"cost":"N/A","count":"N/A"}}
    try:
        data = json.loads(text)
        cdata = data.get(str(country), {})
        return {
            "ub": cdata.get("ub", {"cost":"N/A","count":"N/A"}),
            "yi": cdata.get("yi", {"cost":"N/A","count":"N/A"})
        }
    except:
        return {"ub": {"cost":"N/A","count":"N/A"}, "yi": {"cost":"N/A","count":"N/A"}}

def get_number(service, country="90"):
    text = api_request({"action": "getNumber", "service": service, "country": country})
    if text and text.startswith("ACCESS_NUMBER:"):
        _, order_id, number = text.split(":")
        return order_id, number
    elif text:
        st.error(f"Numara alınamadı: {text}")
    return None, None

def get_status(order_id):
    text = api_request({"action": "getStatus", "id": order_id})
    return text

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        requests.get(url, params={"chat_id": tg_chat_id, "text": msg}, timeout=10)
    except:
        pass  # silent fail

# Sidebar
st.sidebar.title("Durum")
balance = get_balance()
if balance:
    st.sidebar.success(f"Bakiye: {balance} ₽")  # genelde ruble ama ₺ da olabilir
else:
    st.sidebar.error("Bakiye alınamadı")

# Ülke seçimi
country_options = {"Türkiye": "90", "Endonezya": "6", "Diğer": "custom"}
selected_country_name = st.sidebar.selectbox("Ülke", list(country_options.keys()))
country = country_options[selected_country_name]
if selected_country_name == "Diğer":
    country = st.sidebar.text_input("Ülke Kodu (sayı)", "6")

prices = get_prices(country)

# Session state
if "active_orders" not in st.session_state:
    st.session_state.active_orders = {}

# Ana arayüz
st.title("SMS Kiralama Paneli")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Uber")
    st.write(f"Stok: {prices['ub']['count']} | Fiyat: {prices['ub']['cost']}")
    
    if st.button("Numara Al → Uber"):
        oid, num = get_number("ub", country)
        if oid and num:
            st.session_state.active_orders["ub"] = {"id": oid, "number": num, "code": None, "country": selected_country_name}
            st.success(f"Numara alındı: {num}")
            st.rerun()

    if "ub" in st.session_state.active_orders:
        ord = st.session_state.active_orders["ub"]
        st.info(f"Aktif: {ord['number']} ({ord['country']})")
        st.write("Kod:" if ord["code"] else "Kod bekleniyor...")
        if ord["code"]:
            st.success(ord["code"])
        if st.button("Durumu Yenile (Uber)"):
            st.rerun()
        if st.button("İptal Et (Uber)"):
            del st.session_state.active_orders["ub"]
            st.rerun()

with col2:
    st.subheader("Yemeksepeti")
    st.write(f"Stok: {prices['yi']['count']} | Fiyat: {prices['yi']['cost']}")
    
    if st.button("Numara Al → Yemeksepeti"):
        oid, num = get_number("yi", country)
        if oid and num:
            st.session_state.active_orders["yi"] = {"id": oid, "number": num, "code": None, "country": selected_country_name}
            st.success(f"Numara alındı: {num}")
            st.rerun()

    if "yi" in st.session_state.active_orders:
        ord = st.session_state.active_orders["yi"]
        st.info(f"Aktif: {ord['number']} ({ord['country']})")
        st.write("Kod:" if ord["code"] else "Kod bekleniyor...")
        if ord["code"]:
            st.success(ord["code"])
        if st.button("Durumu Yenile (Yemeksepeti)"):
            st.rerun()
        if st.button("İptal Et (Yemeksepeti)"):
            del st.session_state.active_orders["yi"]
            st.rerun()

# Polling (her 10 sn'de bir kontrol)
for svc in list(st.session_state.active_orders.keys()):
    ord = st.session_state.active_orders[svc]
    if ord["code"] is None:
        status = get_status(ord["id"])
        if status:
            if status.startswith("STATUS_OK:"):
                code = status.split(":", 1)[1]
                ord["code"] = code
                send_telegram(f"{svc.upper()} kodu ({ord['country']}): {code} - Numara: {ord['number']}")
                st.success(f"{svc.upper()} kodu alındı → Telegram'a gönderildi!")
                st.rerun()
            elif "STATUS_WAIT" in status or "WAIT" in status:
                time.sleep(8)  # biraz daha kısa polling
                st.rerun()
            else:
                st.warning(f"{svc.upper()} durum: {status}")
