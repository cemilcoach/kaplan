import streamlit as st
import requests
import time
import json

# Mobil uyumluluk için meta + font fix
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        input, button, select, textarea { font-size: 16px !important; }
        .stButton>button { font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# Şifre ekranı + Giriş Yap butonu
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("SMS Kiralama Paneli - Giriş")
    password = st.text_input("Panel Şifresi", type="password", key="auth_pass")
    if st.button("Giriş Yap"):
        if password == st.secrets["PANEL_SIFRESI"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Yanlış şifre!")
    st.stop()

# Secrets'tan çek
api_key = st.secrets.get("HERO_API_KEY", "test_api_key")
tg_token = st.secrets.get("TELEGRAM_TOKEN", "")
tg_chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")

BASE_URL = "https://hero-sms.com/stubs/handler_api.php"

@st.cache_data(ttl=60)  # 60 saniye cache
def api_request(params):
    try:
        params["api_key"] = api_key
        resp = requests.get(BASE_URL, params=params, timeout=12)
        resp.raise_for_status()
        return resp.text.strip()
    except Exception as e:
        st.error(f"API bağlantı hatası: {str(e)}")
        return None

def get_balance():
    text = api_request({"action": "getBalance"})
    if text and text.startswith("ACCESS_BALANCE:"):
        try:
            return float(text.split(":", 1)[1])
        except:
            return None
    return None

@st.cache_data(ttl=60)
def get_prices(country_code):
    text = api_request({"action": "getPrices", "country": country_code})
    if not text:
        return {"ub": {"cost": "Hata", "count": "Hata"}, "yi": {"cost": "Hata", "count": "Hata"}}
    try:
        data = json.loads(text)
        cdata = data.get(str(country_code), {})
        return {
            "ub": cdata.get("ub", {"cost": "Yok", "count": "0"}),
            "yi": cdata.get("yi", {"cost": "Yok", "count": "0"})
        }
    except json.JSONDecodeError:
        st.error("Fiyat verisi JSON formatında değil.")
        return {"ub": {"cost": "Hata", "count": "Hata"}, "yi": {"cost": "Hata", "count": "Hata"}}

def get_number(service, country_code):
    text = api_request({"action": "getNumber", "service": service, "country": country_code})
    if text and text.startswith("ACCESS_NUMBER:"):
        parts = text.split(":")
        if len(parts) >= 3:
            return parts[1], parts[2]
    if text:
        st.error(f"Numara alınamadı → {text}")
    return None, None

def get_status(order_id):
    return api_request({"action": "getStatus", "id": order_id})

def send_to_telegram(message):
    if not tg_token or not tg_chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        requests.get(url, params={"chat_id": tg_chat_id, "text": message}, timeout=8)
    except:
        pass  # sessiz hata

# ────────────────────────────────────────────────
# Sidebar
st.sidebar.title("Panel Durumu")

balance = get_balance()
if balance is not None:
    st.sidebar.metric("Bakiye", f"{balance:.2f} ₽")
else:
    st.sidebar.error("Bakiye alınamadı")

# Ülke seçimi (default Türkiye)
country_map = {"Türkiye (90)": "90", "Endonezya (6)": "6", "Rusya (0)": "0", "Ukrayna (1)": "1"}
selected = st.sidebar.selectbox("Ülke Seç", list(country_map.keys()), index=0)
country = country_map[selected]

prices = get_prices(country)

# Session state temizle / başlat
if "active_orders" not in st.session_state:
    st.session_state.active_orders = {}

# ────────────────────────────────────────────────
st.title("HeroSMS Numara Kiralama")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Uber")
    st.caption(f"Stok: {prices['ub']['count']} | Fiyat: {prices['ub']['cost']}")
    
    if st.button("Uber Numara Al", use_container_width=True):
        oid, num = get_number("ub", country)
        if oid and num:
            st.session_state.active_orders["ub"] = {
                "id": oid, "number": num, "code": None, "country": selected
            }
            st.success(f"Numara alındı: **{num}**")
            st.rerun()

    if "ub" in st.session_state.active_orders:
        o = st.session_state.active_orders["ub"]
        with st.container(border=True):
            st.markdown(f"**Aktif Uber** ({o['country']})")
            st.write(f"Numara: **{o['number']}**")
            if o["code"]:
                st.success(f"Kod: **{o['code']}**")
            else:
                st.info("Kod bekleniyor...")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Yenile", key="refresh_ub"):
                    st.rerun()
            with col_b:
                if st.button("İptal", type="primary", key="cancel_ub"):
                    del st.session_state.active_orders["ub"]
                    st.rerun()

with col2:
    st.subheader("Yemeksepeti")
    st.caption(f"Stok: {prices['yi']['count']} | Fiyat: {prices['yi']['cost']}")
    
    if st.button("Yemeksepeti Numara Al", use_container_width=True):
        oid, num = get_number("yi", country)
        if oid and num:
            st.session_state.active_orders["yi"] = {
                "id": oid, "number": num, "code": None, "country": selected
            }
            st.success(f"Numara alındı: **{num}**")
            st.rerun()

    if "yi" in st.session_state.active_orders:
        o = st.session_state.active_orders["yi"]
        with st.container(border=True):
            st.markdown(f"**Aktif Yemeksepeti** ({o['country']})")
            st.write(f"Numara: **{o['number']}**")
            if o["code"]:
                st.success(f"Kod: **{o['code']}**")
            else:
                st.info("Kod bekleniyor...")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Yenile", key="refresh_yi"):
                    st.rerun()
            with col_b:
                if st.button("İptal", type="primary", key="cancel_yi"):
                    del st.session_state.active_orders["yi"]
                    st.rerun()

# Arka planda polling (her servis için)
for service in list(st.session_state.active_orders.keys()):
    order = st.session_state.active_orders[service]
    if order["code"] is None:
        status_text = get_status(order["id"])
        if status_text:
            if status_text.startswith("STATUS_OK:"):
                code = status_text.split(":", 1)[1]
                order["code"] = code
                msg = f"{service.upper()} kodu ({order['country']}): {code} | Numara: {order['number']}"
                send_to_telegram(msg)
                st.toast(f"{service.upper()} kodu alındı → Telegram'a gönderildi", icon="✅")
                st.rerun()
            elif "STATUS_WAIT" in status_text or status_text == "STATUS_WAIT_CODE":
                time.sleep(7)  # polling aralığı
                st.rerun()
            else:
                st.warning(f"{service.upper()} beklenmedik durum: {status_text}")
