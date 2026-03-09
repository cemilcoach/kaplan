import streamlit as st
import requests
import time

# --- 1. Sayfa ve Mobil Ayarları ---
st.set_page_config(page_title="HeroSMS TR Panel", layout="wide")
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <style>
    input, button { font-size: 16px !important; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #0088cc; color: white; font-weight: bold; }
    .active-card { padding: 15px; border-radius: 12px; background-color: #f0f9ff; border: 2px solid #0088cc; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. API ve Güvenlik Bilgileri ---
API_KEY = "6ce1bb5837f81db1f4cA0b341Ac58956"
PANEL_PASS = "asnaeb68%A"
TG_TOKEN = "8443974633:AAEErjkHLykfsNdbvaty_5Z02YUJ3oPQx0E"
TG_CHAT_ID = "1009360711"
BASE_URL = "https://hero-sms.com/stubs/handler_api.php"

# KRİTİK DÜZELTME: Dokümana göre Türkiye ID'si 143'tür (Telefon kodu 90 ile karıştırılmamalıdır)
TR_COUNTRY_ID = 143 

# --- 3. Kimlik Doğrulama ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Giriş Şifresi", type="password")
    if st.button("Paneli Aç") and pwd == PANEL_PASS:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- 4. API Fonksiyonları ---
def api_request(action, additional_params=None):
    params = {"api_key": API_KEY, "action": action}
    if additional_params:
        params.update(additional_params)
    try:
        response = requests.get(BASE_URL, params=params)
        return response.json() if "getPrices" in action or "getNumberV2" in action else response.text
    except: return None

# --- 5. Arayüz ve Bakiye ---
balance_raw = api_request("getBalance")
balance = balance_raw.split(":")[1] if isinstance(balance_raw, str) and "ACCESS" in balance_raw else "0.00"
st.sidebar.metric("Bakiye", f"{balance} ₽")

st.title("🇹🇷 Türkiye (TR) SMS Servisi")

if "active_order" not in st.session_state: st.session_state.active_order = None

# Fiyatları Listele
prices = api_request("getPrices", {"country": TR_COUNTRY_ID})

if isinstance(prices, dict) and str(TR_COUNTRY_ID) in prices:
    tr_data = prices[str(TR_COUNTRY_ID)]
    c1, c2 = st.columns(2)
    
    services = [("Uber", "ub"), ("Yemeksepeti", "yi")]
    for i, (name, code) in enumerate(services):
        srv_info = tr_data.get(code, {"cost": 0, "count": 0})
        with (c1 if i == 0 else c2):
            st.subheader(name)
            st.write(f"Fiyat: **{srv_info['cost']} ₽** | Stok: **{srv_info['count']}**")
            
            if st.button(f"{name} Al", key=code, disabled=st.session_state.active_order is not None):
                # getNumberV2 kullanarak Türkiye (143) üzerinden numara istiyoruz
                res = api_request("getNumberV2", {"service": code, "country": TR_COUNTRY_ID})
                
                if isinstance(res, dict) and "phoneNumber" in res:
                    st.session_state.active_order = {
                        "id": res["activationId"],
                        "num": res["phoneNumber"],
                        "name": name
                    }
                    # SMS alımını aktifleştir
                    api_request("setStatus", {"id": res["activationId"], "status": 1})
                    st.rerun()
                else:
                    st.error(f"Hata: {res}")

# --- 6. Aktif Sipariş ve Kod Bekleme ---
if st.session_state.active_order:
    order = st.session_state.active_order
    st.markdown(f"""<div class="active-card">
        <h3>🔥 Bekleyen Numara: {order['name']}</h3>
        <h2 style='color:#0088cc;'>+{order['num']}</h2>
        <p>İşlem ID: {order['id']}</p>
    </div>""", unsafe_allow_html=True)

    status = api_request("getStatus", {"id": order['id']})
    
    if "STATUS_OK" in status:
        sms_code = status.split(":")[1]
        st.success(f"📩 KOD: {sms_code}")
        # Telegram Bildirimi
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      json={"chat_id": TG_CHAT_ID, "text": f"✅ {order['name']} Kodu: {sms_code}\nNumara: {order['num']}"})
        
        if st.button("Tamamla"):
            api_request("setStatus", {"id": order['id'], "status": 6})
            st.session_state.active_order = None
            st.rerun()
            
    elif "STATUS_WAIT_CODE" in status:
        st.info("⌛ Kod bekleniyor... (Ekranı yenilemeyin)")
        time.sleep(5)
        st.rerun()

    if st.button("❌ İptal Et (İade)"):
        api_request("setStatus", {"id": order['id'], "status": 8})
        st.session_state.active_order = None
        st.rerun()
