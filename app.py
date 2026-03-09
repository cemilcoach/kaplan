import streamlit as st
import requests
import time
import json

# Mobil uyumluluk
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        input, button, select, textarea { font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# Auth (Giriş Yap butonu)
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
api_key = st.secrets.get("HERO_API_KEY")
if not api_key:
    st.error("secrets.toml'da HERO_API_KEY tanımlı değil!")
    st.stop()

tg_token = st.secrets.get("TELEGRAM_TOKEN", "")
tg_chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")

BASE = "https://hero-sms.com/stubs/handler_api.php"

def api_call(params):
    params["api_key"] = api_key
    try:
        r = requests.get(BASE, params=params, timeout=10)
        r.raise_for_status()
        return r.text.strip()
    except Exception as e:
        st.error(f"API hatası: {e}")
        return None

def get_balance():
    text = api_call({"action": "getBalance"})
    if text and text.startswith("ACCESS_BALANCE:"):
        return float(text.split(":", 1)[1])
    return None

@st.cache_data(ttl=30)
def get_prices(country="90"):
    text = api_call({"action": "getPrices", "country": country})
    if not text:
        return {}, text
    try:
        data = json.loads(text)
        return data.get(str(country), {}), text
    except:
        return {}, text

def get_number(service, country="90"):
    text = api_call({"action": "getNumber", "service": service, "country": country})
    if text and text.startswith("ACCESS_NUMBER:"):
        _, oid, num = text.split(":", 2)
        return oid, num
    else:
        st.error(f"Numara alınamadı → {text or 'Boş yanıt'} (NO_NUMBERS = stok bitti, BAD_SERVICE = servis kodu hatalı)")
        return None, None

def get_status(oid):
    return api_call({"action": "getStatus", "id": oid})

def send_tg(msg):
    if tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            requests.get(url, params={"chat_id": tg_chat_id, "text": msg})
        except:
            pass

# ──────────────── UI ────────────────
st.sidebar.title("Durum")
bal = get_balance()
if bal is not None:
    st.sidebar.metric("Bakiye", f"{bal:.2f}")
else:
    st.sidebar.warning("Bakiye alınamadı")

country = "90"  # Sadece TR odaklanıyoruz, Yemeksepeti genelde sadece TR'de

prices_dict, raw_prices = get_prices(country)

# Debug için raw göster (gerekirse yorum satırı yap)
with st.sidebar.expander("Raw getPrices (debug)"):
    st.json(raw_prices)

st.title("SMS Panel - Türkiye (90)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Uber")
    ub_data = prices_dict.get("ub", {"cost": "?", "count": 0})
    count_ub = int(ub_data.get("count", 0))
    cost_ub = ub_data.get("cost", "?")
    st.write(f"Stok: **{count_ub}** | Fiyat: **{cost_ub}** ₽")
    
    if count_ub > 0:
        if st.button("Uber Numara Al", use_container_width=True):
            oid, num = get_number("ub", country)
            if oid and num:
                st.session_state.setdefault("orders", {})["ub"] = {"id": oid, "num": num, "code": None}
                st.success(f"Numara: {num}")
                st.rerun()
    else:
        st.warning("Uber stok yok")
    
    if "ub" in st.session_state.get("orders", {}):
        o = st.session_state.orders["ub"]
        with st.container(border=True):
            st.write(f"**Uber** - Numara: {o['num']}")
            if o["code"]:
                st.success(f"Kod: {o['code']}")
            else:
                st.info("Kod bekleniyor...")
            c1, c2 = st.columns(2)
            if c1.button("Yenile"):
                st.rerun()
            if c2.button("İptal", type="primary"):
                del st.session_state.orders["ub"]
                st.rerun()

with col2:
    st.subheader("Yemeksepeti")
    # Denenecek kodlar: yp > ys > yi (en yaygın yp)
    possible_codes = ["yp", "ys", "yi"]
    yi_data = None
    used_code = None
    for code in possible_codes:
        yi_data = prices_dict.get(code)
        if yi_data:
            used_code = code
            break
    
    if yi_data:
        count_yi = int(yi_data.get("count", 0))
        cost_yi = yi_data.get("cost", "?")
        st.write(f"Stok: **{count_yi}** | Fiyat: **{cost_yi}** ₽ (kod: {used_code})")
        
        if count_yi > 0:
            if st.button("Yemeksepeti Numara Al", use_container_width=True):
                oid, num = get_number(used_code, country)
                if oid and num:
                    st.session_state.setdefault("orders", {})["yi"] = {"id": oid, "num": num, "code": None}
                    st.success(f"Numara: {num}")
                    st.rerun()
        else:
            st.warning("Yemeksepeti stok yok")
    else:
        st.error("Yemeksepeti servisi bulunamadı! (yp/ys/yi kodlarında yok)")

    if "yi" in st.session_state.get("orders", {}):
        o = st.session_state.orders["yi"]
        with st.container(border=True):
            st.write(f"**Yemeksepeti** - Numara: {o['num']}")
            if o["code"]:
                st.success(f"Kod: {o['code']}")
            else:
                st.info("Kod bekleniyor...")
            c1, c2 = st.columns(2)
            if c1.button("Yenile"):
                st.rerun()
            if c2.button("İptal", type="primary"):
                del st.session_state.orders["yi"]
                st.rerun()

# Polling
orders = st.session_state.get("orders", {})
for srv, o in list(orders.items()):
    if o["code"] is None:
        status = get_status(o["id"])
        if status and status.startswith("STATUS_OK:"):
            code = status.split(":", 1)[1]
            o["code"] = code
            send_tg(f"{srv.upper()} kodu: {code} | Numara: {o['num']}")
            st.toast(f"{srv.upper()} kodu geldi!", icon="✅")
            st.rerun()
        elif status and "WAIT" in status:
            time.sleep(5)
            st.rerun()
        elif status:
            st.warning(f"{srv} durum: {status}")
