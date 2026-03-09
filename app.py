import streamlit as st
import requests
import time
import json

# Mobil fix
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        input, button, select, textarea { font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# Auth
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Giriş")
    password = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if password == st.secrets["PANEL_SIFRESI"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Yanlış şifre")
    st.stop()

# Secrets
api_key = st.secrets.get("HERO_API_KEY", "test")
tg_token = st.secrets.get("TELEGRAM_TOKEN", "")
tg_chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")

BASE = "https://hero-sms.com/stubs/handler_api.php"

def api_call(params):
    params["api_key"] = api_key
    try:
        r = requests.get(BASE, params=params, timeout=10)
        r.raise_for_status()
        text = r.text.strip()
        return text
    except Exception as e:
        st.error(f"API bağlantı sorunu: {e}")
        return f"REQUEST_ERROR: {str(e)}"

def get_balance():
    text = api_call({"action": "getBalance"})
    if text.startswith("ACCESS_BALANCE:"):
        return float(text.split(":",1)[1])
    st.warning(f"Bakiye response: {text}")
    return None

@st.cache_data(ttl=45)
def get_prices(country):
    text = api_call({"action": "getPrices", "country": country})
    st.session_state.last_prices_raw = text  # debug için sakla
    if not text or ":" in text or "BAD" in text.upper():
        st.warning(f"getPrices raw: {text}")
        return {"ub": {"cost":"?", "count":0}, "yi": {"cost":"?", "count":0}}
    try:
        data = json.loads(text)
        cdata = data.get(str(country), {})
        ub = cdata.get("ub", {"cost":"Yok", "count":0})
        yi = cdata.get("yi", {"cost":"Yok", "count":0})
        return {"ub": ub, "yi": yi}
    except:
        st.error(f"JSON parse hatası - raw: {text}")
        return {"ub": {"cost":"Hata", "count":0}, "yi": {"cost":"Hata", "count":0}}

def get_number(service, country):
    text = api_call({"action": "getNumber", "service": service, "country": country})
    if text.startswith("ACCESS_NUMBER:"):
        parts = text.split(":")
        return parts[1], parts[2]
    else:
        st.error(f"Numara alınamadı → Response: **{text}**  (NO_NUMBERS = stok yok, NO_BALANCE = bakiye yetersiz, BAD_KEY = api key hatalı)")
        return None, None

def get_status(oid):
    return api_call({"action": "getStatus", "id": oid})

def send_tg(msg):
    if tg_token and tg_chat_id:
        try:
            requests.get(f"https://api.telegram.org/bot{tg_token}/sendMessage", params={"chat_id": tg_chat_id, "text": msg})
        except:
            pass

# Sidebar
st.sidebar.title("Durum")
bal = get_balance()
if bal:
    st.sidebar.metric("Bakiye", f"{bal:.2f}")
else:
    st.sidebar.warning("Bakiye alınamadı")

# Ülke seç (SMS-Activate standart kodlar)
countries = {
    "Türkiye": "90",
    "Endonezya": "6",
    "Rusya": "0",
    "Ukrayna": "1",
    "Hindistan": "49",
    "Vietnam": "55",
    "Filipinler": "58",
    "ABD": "187",
    "Kazakistan": "123"
}
selected_country = st.sidebar.selectbox("Ülke", list(countries.keys()), index=0)
country_code = countries[selected_country]

prices = get_prices(country_code)

# Aktif siparişler
if "orders" not in st.session_state:
    st.session_state.orders = {}

st.title(f"SMS Panel - {selected_country}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Uber (ub)")
    count_ub = int(prices["ub"].get("count", 0))
    cost_ub = prices["ub"].get("cost", "?")
    st.write(f"Stok: **{count_ub}** | Fiyat: **{cost_ub}**")
    
    disabled_ub = count_ub <= 0
    if st.button("Uber Numara Al", disabled=disabled_ub, use_container_width=True):
        oid, num = get_number("ub", country_code)
        if oid and num:
            st.session_state.orders["ub"] = {"id": oid, "num": num, "code": None, "country": selected_country}
            st.success(f"Alındı: {num}")
            st.rerun()

    if "ub" in st.session_state.orders:
        o = st.session_state.orders["ub"]
        with st.expander(f"Aktif Uber ({o['country']})", expanded=True):
            st.write(f"Numara: **{o['num']}**")
            if o["code"]:
                st.success(f"**Kod: {o['code']}**")
            else:
                st.info("Kod bekleniyor...")
            cols = st.columns(2)
            if cols[0].button("Yenile"):
                st.rerun()
            if cols[1].button("İptal", type="primary"):
                del st.session_state.orders["ub"]
                st.rerun()

with col2:
    st.subheader("Yemeksepeti (yi)")
    count_yi = int(prices["yi"].get("count", 0))
    cost_yi = prices["yi"].get("cost", "?")
    st.write(f"Stok: **{count_yi}** | Fiyat: **{cost_yi}**")
    
    disabled_yi = count_yi <= 0
    if st.button("Yemeksepeti Numara Al", disabled=disabled_yi, use_container_width=True):
        oid, num = get_number("yi", country_code)
        if oid and num:
            st.session_state.orders["yi"] = {"id": oid, "num": num, "code": None, "country": selected_country}
            st.success(f"Alındı: {num}")
            st.rerun()

    if "yi" in st.session_state.orders:
        o = st.session_state.orders["yi"]
        with st.expander(f"Aktif Yemeksepeti ({o['country']})", expanded=True):
            st.write(f"Numara: **{o['num']}**")
            if o["code"]:
                st.success(f"**Kod: {o['code']}**")
            else:
                st.info("Kod bekleniyor...")
            cols = st.columns(2)
            if cols[0].button("Yenile"):
                st.rerun()
            if cols[1].button("İptal", type="primary"):
                del st.session_state.orders["yi"]
                st.rerun()

# Polling
for srv in list(st.session_state.orders.keys()):
    o = st.session_state.orders[srv]
    if o["code"] is None:
        status = get_status(o["id"])
        if status and status.startswith("STATUS_OK:"):
            code = status.split(":",1)[1]
            o["code"] = code
            send_tg(f"{srv.upper()} kodu ({o['country']}): {code} | {o['num']}")
            st.toast(f"{srv.upper()} kodu geldi!", icon="🎉")
            st.rerun()
        elif "WAIT" in status:
            time.sleep(6)
            st.rerun()
        elif status:
            st.warning(f"{srv} durum: {status}")
