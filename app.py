import streamlit as st
import requests
import time

# --- 1. Güvenlik ve Mobil Uyumluluk ---
st.set_page_config(page_title="Safe SMS Panel TR", layout="wide")
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
    input, button { font-size: 16px !important; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #d32f2f; color: white; font-weight: bold; }
    .active-card { padding: 15px; border-radius: 12px; background-color: #fdf2f2; border: 2px solid #d32f2f; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Secrets Yönetimi (Paramı Koru Modu) ---
# Bilgiler artık kodun içinde değil, st.secrets içinde saklanıyor.
try:
    API_KEY_HERO = st.secrets["HERO_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
    TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except KeyError as e:
    st.error(f"Hata: Secrets içinde {e} anahtarı bulunamadı! Lütfen ayarları yapın.")
    st.stop()

BASE_URL = "https://hero-sms.com/stubs/handler_api.php"
TR_COUNTRY_ID = 62 # Türkiye Sistem ID'si

# --- 3. Kimlik Doğrulama ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🛡️ Güvenli Erişim")
    pwd = st.text_input("Giriş Şifresi", type="password")
    if st.button("Sistemi Başlat"):
        if pwd == PANEL_SIFRESI:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Hatalı Şifre! Erişim reddedildi.")
    st.stop()

# --- 4. API Fonksiyonları ---
def api_call(action, extra_params=None):
    params = {"api_key": API_KEY_HERO, "action": action}
    if extra_params:
        params.update(extra_params)
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        # V2 protokolü ve getPrices JSON döner
        if "V2" in action or "getPrices" in action:
            return response.json()
        return response.text
    except Exception:
        return None

# --- 5. Arayüz ve Bakiye ---
balance_text = api_call("getBalance")
balance = balance_text.split(":")[1] if balance_text and "ACCESS" in balance_text else "0.00"
st.sidebar.metric("Cüzdan Bakiyesi", f"{balance} ₽")

st.title("🇹🇷 Türkiye (TR) SMS Hattı")

if "order" not in st.session_state:
    st.session_state.order = None

# Fiyatları Çek (TR: 62)
prices = api_call("getPrices", {"country": TR_COUNTRY_ID})

if prices and str(TR_COUNTRY_ID) in prices:
    tr_prices = prices[str(TR_COUNTRY_ID)]
    col1, col2 = st.columns(2)
    
    services = [("Uber", "ub"), ("Yemeksepeti", "yi")]
    for i, (name, srv_code) in enumerate(services):
        srv_data = tr_prices.get(srv_code, {"cost": 0, "count": 0})
        with (col1 if i == 0 else col2):
            st.subheader(f"📍 {name}")
            st.write(f"Fiyat: **{srv_data['cost']} ₽** | Stok: **{srv_data['count']}**")
            
            if st.button(f"{name} Numarası Satın Al", key=srv_code, disabled=st.session_state.order is not None):
                # getNumberV2 kullanımı
                res = api_call("getNumberV2", {"service": srv_code, "country": TR_COUNTRY_ID})
                
                if isinstance(res, dict) and "phoneNumber" in res:
                    st.session_state.order = {
                        "id": res["activationId"],
                        "num": res["phoneNumber"],
                        "name": name
                    }
                    # Durumu hemen "SMS Bekleniyor" (1) yapıyoruz
                    api_call("setStatus", {"id": res["activationId"], "status": 1})
                    st.rerun()
                else:
                    st.error(f"Hata: {res}")

# --- 6. Aktif Sipariş ve Telegram Bildirimi ---
if st.session_state.order:
    ord = st.session_state.order
    st.markdown(f"""<div class="active-card">
        <h3>🚀 Aktif Sipariş: {ord['name']}</h3>
        <h2 style='color:#d32f2f;'>+{ord['num']}</h2>
        <p>İşlem ID: {ord['id']}</p>
    </div>""", unsafe_allow_html=True)

    status_res = api_call("getStatus", {"id": ord['id']})
    
    if status_res and "STATUS_OK" in status_res:
        sms_code = status_res.split(":")[1]
        st.success(f"📩 KOD GELDİ: {sms_code}")
        
        # Telegram'a gönder
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(tg_url, json={"chat_id": TELEGRAM_CHAT_ID, "text": f"📩 {ord['name']} KODU: {sms_code}\nNumara: +{ord['num']}"})
        
        if st.button("Onayla ve Kapat"):
            api_call("setStatus", {"id": ord['id'], "status": 6}) # Aktivasyon Tamam
            st.session_state.order = None
            st.rerun()
            
    elif status_res and "STATUS_WAIT_CODE" in status_res:
        st.info("⌛ Kod bekleniyor... Otomatik yenileniyor.")
        time.sleep(5)
        st.rerun()

    if st.button("❌ İptal Et ve Parayı Geri Al"):
        api_call("setStatus", {"id": ord['id'], "status": 8}) # İptal
        st.session_state.order = None
        st.rerun()
