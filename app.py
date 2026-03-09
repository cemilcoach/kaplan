import streamlit as st
import requests
import time

# --- 1. Sayfa Yapılandırması ve Mobil Uyumluluk ---
st.set_page_config(page_title="HeroSMS VIP Panel", layout="wide")

st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
    input, button { font-size: 16px !important; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #007bff; color: white; font-weight: bold; }
    .order-card { padding: 15px; border-radius: 15px; background-color: #f8f9fa; border-left: 5px solid #28a745; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Kimlik Doğrulama ve Sabitler ---
# Dokümana göre ana sunucu adresi
BASE_URL = "https://hero-sms.com/stubs/handler_api.php"

try:
    API_KEY = st.secrets["HERO_API_KEY"]
    PANEL_PASS = st.secrets["PANEL_SIFRESI"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except:
    # Hata almamak için fallback değerler
    API_KEY = "6ce1bb5837f81db1f4cA0b341Ac58956"
    PANEL_PASS = "asnaeb68%A"
    TG_TOKEN = "8443974633:AAEErjkHLykfsNdbvaty_5Z02YUJ3oPQx0E"
    TG_CHAT_ID = "1009360711"

# --- 3. API Fonksiyonları ---
def get_balance():
    # Doküman: action=getBalance -> ACCESS_BALANCE:<amount>
    params = {"api_key": API_KEY, "action": "getBalance"}
    try:
        res = requests.get(BASE_URL, params=params).text
        if "ACCESS_BALANCE" in res:
            return res.split(":")[1]
    except: return "0.00"
    return "Hata"

def get_prices(country_id=90):
    # Doküman: action=getPrices
    params = {"api_key": API_KEY, "action": "getPrices", "country": country_id}
    try:
        res = requests.get(BASE_URL, params=params).json()
        # API yanıtı { "90": { "ub": { "cost": X, "count": Y } } } formatındadır
        country_data = res.get(str(country_id), {})
        return {
            "Uber": country_data.get("ub", {"cost": 0, "count": 0}),
            "Yemeksepeti": country_data.get("yi", {"cost": 0, "count": 0})
        }
    except: return None

def set_status(activation_id, status):
    # Doküman: action=setStatus (1: Hazır, 8: İptal, 6: Tamamla)
    params = {"api_key": API_KEY, "action": "setStatus", "id": activation_id, "status": status}
    return requests.get(BASE_URL, params=params).text

# --- 4. Giriş Kontrolü ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Panel Şifresi", type="password")
    if st.button("Giriş"):
        if pwd == PANEL_PASS:
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 5. Arayüz ---
st.sidebar.metric("Bakiye", f"{get_balance()} ₽")
st.title("🇹🇷 HeroSMS Türkiye Paneli")

if "order" not in st.session_state: st.session_state.order = None

prices = get_prices(90) # Türkiye ID: 90 olarak zorlanıyor

if prices:
    cols = st.columns(2)
    for i, (name, data) in enumerate(prices.items()):
        with cols[i]:
            st.subheader(name)
            st.write(f"Fiyat: **{data['cost']} ₽** | Stok: **{data['count']}**")
            # Numara Alma (getNumber)
            if st.button(f"{name} Al", key=name, disabled=st.session_state.order is not None):
                srv = "ub" if name == "Uber" else "yi"
                # KRİTİK: country parametresi int(90) olarak gönderiliyor
                req_params = {"api_key": API_KEY, "action": "getNumber", "service": srv, "country": 90}
                res = requests.get(BASE_URL, params=req_params).text
                
                if "ACCESS_NUMBER" in res:
                    _, active_id, active_num = res.split(":")
                    st.session_state.order = {"id": active_id, "num": active_num, "name": name}
                    # Numara alındıktan sonra durumu 'Hazır' yapıyoruz
                    set_status(active_id, 1)
                    st.rerun()
                else:
                    st.error(f"Hata: {res}")

# --- 6. Aktif Sipariş Takibi ---
if st.session_state.order:
    ord = st.session_state.order
    st.markdown(f"""<div class="order-card">
        <h3>✅ {ord['name']} Numarası Hazır</h3>
        <p style='font-size:20px;'>📞 <b>{ord['num']}</b></p>
        <p>ID: {ord['id']}</p>
    </div>""", unsafe_allow_html=True)

    # Durum Sorgulama (getStatus)
    if "code" not in ord:
        with st.spinner("SMS bekleniyor..."):
            check = requests.get(BASE_URL, params={"api_key": API_KEY, "action": "getStatus", "id": ord['id']}).text
            if "STATUS_OK" in check:
                code = check.split(":")[1]
                st.session_state.order["code"] = code
                # Telegram Bildirimi
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              data={"chat_id": TG_CHAT_ID, "text": f"✅ {ord['name']} Kodu: {code}\nNo: {ord['num']}"})
                st.rerun()
            elif "STATUS_WAIT_CODE" in check:
                time.sleep(4)
                st.rerun()

    if "code" in ord:
        st.success(f"📩 GELEN KOD: {ord['code']}")
        if st.button("İşlemi Tamamla (Onayla)"):
            set_status(ord['id'], 6) # Aktivasyonu tamamla
            st.session_state.order = None
            st.rerun()

    if st.button("🚫 İptal Et ve İade Al"):
        set_status(ord['id'], 8) # Aktivasyonu iptal et
        st.session_state.order = None
        st.rerun()
