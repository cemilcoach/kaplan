import streamlit as st
import requests
import time
import re

# --- 1. Sayfa Yapılandırması ve Mobil Uyumluluk ---
st.set_page_config(page_title="SMS Kiralama Paneli", layout="wide", initial_sidebar_state="collapsed")

# Mobil cihazlarda zoom engelleme ve şık görünüm için CSS
st.markdown("""
    <meta name="viewport" content="width=device-width, initial_scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
    /* Input ve butonlarda otomatik zoom'u engellemek için font size 16px */
    input, select, textarea, button {
        font-size: 16px !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
    }
    .status-card {
        padding: 20px;
        border-radius: 15px;
        background-color: #f0f2f6;
        border-left: 5px solid #00c853;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Kimlik Doğrulama ve Secrets ---
# Not: Gerçek kullanımda bunları .streamlit/secrets.toml dosyasına eklemelisin.
try:
    API_KEY = st.secrets["HERO_API_KEY"]
    PANEL_PASS = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except:
    # Test amaçlı fallback (Secrets yoksa hata vermemesi için)
    API_KEY = "6ce1bb5837f81db1f4cA0b341Ac58956"
    PANEL_PASS = "asnaeb68%A"
    TG_TOKEN = "8443974633:AAEErjkHLykfsNdbvaty_5Z02YUJ3oPQx0E"
    TG_CHAT_ID = "1009360711"

BASE_URL = "https://hero-sms.com/stubs/handler_api.php"

# --- 3. Yardımcı Fonksiyonlar ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except:
        pass

def get_hero_balance():
    params = {"api_key": API_KEY, "action": "getBalance"}
    try:
        res = requests.get(BASE_URL, params=params).text
        if "ACCESS_BALANCE" in res:
            return res.split(":")[1]
    except:
        return "0.00"
    return "Hata"

def get_hero_prices():
    params = {"api_key": API_KEY, "action": "getPrices", "country": "90"}
    try:
        res = requests.get(BASE_URL, params=params).json()
        # Sadece Uber (ub) ve Yemeksepeti (yi) çekiliyor
        data = {
            "Uber": res.get("90", {}).get("ub", {"cost": 0, "count": 0}),
            "Yemeksepeti": res.get("90", {}).get("yi", {"cost": 0, "count": 0})
        }
        return data
    except:
        return None

# --- 4. Giriş Ekranı (Password Protection) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Panel Girişi")
    password_input = st.text_input("Şifre Giriniz", type="password")
    if st.button("Giriş Yap"):
        if password_input == PANEL_PASS:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Hatalı Şifre!")
    st.stop()

# --- 5. Ana Uygulama Mantığı ---
st.sidebar.title("👤 Kullanıcı Paneli")
balance = get_hero_balance()
st.sidebar.metric("Güncel Bakiye", f"{balance} ₽")

if st.sidebar.button("🔄 Bakiyeyi Yenile"):
    st.rerun()

st.title("📲 SMS Kiralama (TR)")

# Session State Yönetimi
if "active_order" not in st.session_state:
    st.session_state.active_order = None

# Fiyatları Çek
prices = get_hero_prices()

if prices:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🚗 Uber")
        st.write(f"💰 Fiyat: **{prices['Uber']['cost']} ₽**")
        st.write(f"📦 Stok: **{prices['Uber']['count']}**")
        if st.button("Uber Al", key="btn_ub", disabled=st.session_state.active_order is not None):
            res = requests.get(BASE_URL, params={"api_key": API_KEY, "action": "getNumber", "service": "ub", "country": "90"}).text
            if "ACCESS_NUMBER" in res:
                parts = res.split(":")
                st.session_state.active_order = {"id": parts[1], "number": parts[2], "service": "Uber"}
                st.rerun()
            else:
                st.error(f"Hata: {res}")

    with col2:
        st.subheader("🍔 Yemeksepeti")
        st.write(f"💰 Fiyat: **{prices['Yemeksepeti']['cost']} ₽**")
        st.write(f"📦 Stok: **{prices['Yemeksepeti']['count']}**")
        if st.button("Yemeksepeti Al", key="btn_yi", disabled=st.session_state.active_order is not None):
            res = requests.get(BASE_URL, params={"api_key": API_KEY, "action": "getNumber", "service": "yi", "country": "90"}).text
            if "ACCESS_NUMBER" in res:
                parts = res.split(":")
                st.session_state.active_order = {"id": parts[1], "number": parts[2], "service": "Yemeksepeti"}
                st.rerun()
            else:
                st.error(f"Hata: {res}")
else:
    st.warning("API verileri alınamadı. Lütfen API Key kontrol edin.")

# --- 6. Aktif Sipariş ve SMS Sorgulama ---
if st.session_state.active_order:
    order = st.session_state.active_order
    st.divider()
    
    st.markdown(f"""
    <div class="status-card">
        <h3>🔥 Aktif Sipariş: {order['service']}</h3>
        <p><b>Numara:</b> {order['number']}</p>
        <p><b>ID:</b> {order['id']}</p>
    </div>
    """, unsafe_allow_html=True)

    status_area = st.empty()
    
    # Otomatik Sorgulama Döngüsü (Simüle edilmiş veya gerçek)
    if "sms_code" not in order:
        with st.spinner("Kod bekleniyor..."):
            check_params = {"api_key": API_KEY, "action": "getStatus", "id": order['id']}
            status_res = requests.get(BASE_URL, params=check_params).text
            
            if "STATUS_OK" in status_res:
                sms_code = status_res.split(":")[1]
                st.session_state.active_order["sms_code"] = sms_code
                send_telegram(f"✅ Yeni SMS!\nServis: {order['service']}\nNo: {order['number']}\nKod: {sms_code}")
                st.success(f"GELEN KOD: {sms_code}")
                st.balloons()
            elif "STATUS_WAIT_CODE" in status_res:
                status_area.info("⏳ Kod bekleniyor, lütfen bekleyin...")
                time.sleep(3) # Çok sık istek atmamak için
                st.rerun()
            else:
                status_area.warning(f"Durum: {status_res}")

    if "sms_code" in order:
        st.success(f"📩 Alınan Kod: **{order['sms_code']}**")

    if st.button("❌ Siparişi Kapat / Yeni Numara"):
        st.session_state.active_order = None
        st.rerun()

# --- 7. Alt Bilgi ---
st.caption("Developed by Gemini with Streamlit • 2026")
