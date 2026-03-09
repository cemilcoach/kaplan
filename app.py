import streamlit as st
import requests
import time

# --- 1. Mobil ve Arayüz Ayarları ---
st.set_page_config(page_title="HeroSMS TR V2", layout="wide")
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
    input, button { font-size: 16px !important; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #d32f2f; color: white; font-weight: bold; }
    .order-box { padding: 20px; border-radius: 15px; background-color: #fff3e0; border: 2px solid #ff9800; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API Bilgileri ---
# Dokümana göre API Anahtarı ve Endpoint'ler
API_KEY = "6ce1bb5837f81db1f4cA0b341Ac58956"
PANEL_PASS = "asnaeb68%A"
TG_TOKEN = "8443974633:AAEErjkHLykfsNdbvaty_5Z02YUJ3oPQx0E"
TG_CHAT_ID = "1009360711"
BASE_URL = "https://hero-sms.com/stubs/handler_api.php"

# --- 3. Gelişmiş API Fonksiyonları ---
def call_api(action, params):
    params["api_key"] = API_KEY
    params["action"] = action
    try:
        response = requests.get(BASE_URL, params=params)
        # V2 ve getPrices JSON döner, getStatus/setStatus metin döner
        try:
            return response.json()
        except:
            return response.text
    except Exception as e:
        return f"Hata: {str(e)}"

# --- 4. Giriş Paneli ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    with st.container():
        st.title("🛡️ Güvenli Giriş")
        sifre = st.text_input("Panel Şifresi", type="password")
        if st.button("Sistemi Aç") and sifre == PANEL_PASS:
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 5. Ana Panel ---
balance_res = call_api("getBalance", {})
balance = balance_res.split(":")[1] if isinstance(balance_res, str) and "ACCESS_BALANCE" in balance_res else "0.00"
st.sidebar.metric("Cüzdan", f"{balance} ₽")

st.title("🇹🇷 Türkiye Özel SMS Paneli")

if "active_id" not in st.session_state: st.session_state.active_id = None

# Fiyatları Çek (Türkiye - 90)
prices_json = call_api("getPrices", {"country": 90})

if isinstance(prices_json, dict) and "90" in prices_json:
    tr_prices = prices_json["90"]
    col1, col2 = st.columns(2)
    
    for idx, (srv_label, srv_code) in enumerate([("Uber", "ub"), ("Yemeksepeti", "yi")]):
        data = tr_prices.get(srv_code, {"cost": 0, "count": 0})
        with (col1 if idx == 0 else col2):
            st.subheader(f"📍 {srv_label}")
            st.write(f"Fiyat: **{data['cost']} ₽**")
            st.write(f"Stok: **{data['count']}**")
            
            # KRİTİK DÜZELTME: getNumberV2 kullanımı
            if st.button(f"{srv_label} Numarası Al", key=srv_code, disabled=st.session_state.active_id is not None):
                # Doküman: getNumberV2 daha güvenli bir parametre yapısı sunar
                res = call_api("getNumberV2", {"service": srv_code, "country": 90})
                
                if isinstance(res, dict) and "phoneNumber" in res:
                    st.session_state.active_id = res["activationId"]
                    st.session_state.active_num = res["phoneNumber"]
                    st.session_state.active_srv = srv_label
                    # Numarayı SMS alımına hazır hale getir (Status 1)
                    call_api("setStatus", {"id": res["activationId"], "status": 1})
                    st.rerun()
                else:
                    st.error(f"API Hatası: {res}")
else:
    st.error("Türkiye stok verisi çekilemedi. API anahtarını veya ülke ID'sini kontrol edin.")

# --- 6. Aktif Sipariş ve Telegram Takibi ---
if st.session_state.active_id:
    st.divider()
    st.markdown(f"""
    <div class="order-box">
        <h3>🚀 AKTİF HAT: {st.session_state.active_srv}</h3>
        <h2 style='color: #d32f2f;'>+{st.session_state.active_num}</h2>
        <p>İşlem ID: {st.session_state.active_id}</p>
    </div>
    """, unsafe_allow_html=True)

    # Durum Kontrolü
    status_check = call_api("getStatus", {"id": st.session_state.active_id})
    
    if "STATUS_OK" in status_check:
        sms_code = status_check.split(":")[1]
        st.success(f"📩 KOD GELDİ: {sms_code}")
        # Telegram'a gönder
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      json={"chat_id": TG_CHAT_ID, "text": f"✅ {st.session_state.active_srv} KODU: {sms_code}\nNumara: {st.session_state.active_num}"})
        
        if st.button("✅ Kodu Onayla ve Kapat"):
            call_api("setStatus", {"id": st.session_state.active_id, "status": 6})
            st.session_state.active_id = None
            st.rerun()
    elif "STATUS_WAIT_CODE" in status_check:
        st.info("⌛ SMS bekleniyor... (Otomatik Yenilenir)")
        time.sleep(5)
        st.rerun()

    if st.button("❌ Numarayı İptal Et (İade)"):
        call_api("setStatus", {"id": st.session_state.active_id, "status": 8})
        st.session_state.active_id = None
        st.rerun()
