import streamlit as st
import requests
import time
import json

# Mobil uyumluluk için CSS ve meta etiketi
st.markdown("""
    <style>
        input, button, select, textarea {
            font-size: 16px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
""", unsafe_allow_html=True)

# Kimlik doğrulama (şifre kontrolü)
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Panel Şifresi:", type="password")
    if password:
        if password == st.secrets["PANEL_SIFRESI"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Yanlış şifre. Lütfen tekrar deneyin.")
    st.stop()

# Secrets'tan verileri çek (test için örnek değerler, secrets.toml ile değiştirin)
api_key = st.secrets.get("HERO_API_KEY", "test_api_key_123")
panel_sifresi = st.secrets.get("PANEL_SIFRESI", "test_sifre_123")
tg_token = st.secrets.get("TELEGRAM_TOKEN", "test_tg_token_123")
tg_chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "test_chat_id_123")

# API base URL
base_url = "https://hero-sms.com/stubs/handler_api.php"

# Fonksiyon: Bakiye çekme
def get_balance():
    try:
        params = {"action": "getBalance", "api_key": api_key}
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        text = response.text
        if text.startswith("ACCESS_BALANCE:"):
            return float(text.split(":")[1])
        else:
            st.error(f"Bakiye yanıtı hatalı: {text}")
            return None
    except Exception as e:
        st.error(f"Bakiye çekme hatası: {e}")
        return None

# Fonksiyon: Stok ve fiyat çekme (sadece ub ve yi için)
def get_prices():
    try:
        params = {"action": "getPrices", "country": 90, "api_key": api_key}
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = json.loads(response.text)
        turkey_data = data.get("90", {})
        ub = turkey_data.get("ub", {"cost": "N/A", "count": "N/A"})
        yi = turkey_data.get("yi", {"cost": "N/A", "count": "N/A"})
        return {"ub": ub, "yi": yi}
    except Exception as e:
        st.error(f"Fiyat/stok çekme hatası: {e}")
        return {"ub": {"cost": "N/A", "count": "N/A"}, "yi": {"cost": "N/A", "count": "N/A"}}

# Fonksiyon: Numara alma
def get_number(service):
    try:
        params = {"action": "getNumber", "service": service, "country": 90, "api_key": api_key}
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        text = response.text
        if text.startswith("ACCESS_NUMBER:"):
            parts = text.split(":")
            order_id = parts[1]
            number = parts[2]
            return order_id, number
        else:
            st.error(f"Numara alma yanıtı hatalı: {text}")
            return None, None
    except Exception as e:
        st.error(f"Numara alma hatası: {e}")
        return None, None

# Fonksiyon: Durum sorgulama
def get_status(order_id):
    try:
        params = {"action": "getStatus", "id": order_id, "api_key": api_key}
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.text
    except Exception as e:
        st.error(f"Durum sorgulama hatası: {e}")
        return None

# Fonksiyon: Telegram'a mesaj gönderme
def send_to_telegram(message):
    try:
        tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        params = {"chat_id": tg_chat_id, "text": message}
        response = requests.post(tg_url, params=params)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Telegram gönderme hatası: {e}")

# Sidebar: Bakiye göster
st.sidebar.title("Bakiye Bilgisi")
balance = get_balance()
if balance is not None:
    st.sidebar.success(f"{balance} ₺")
else:
    st.sidebar.error("Bakiye alınamadı.")

# Fiyat ve stok verilerini çek
prices = get_prices()

# Session state: Aktif siparişler (her servis için ayrı)
if "active_orders" not in st.session_state:
    st.session_state.active_orders = {}

# Ana arayüz: 2 sütun
col1, col2 = st.columns(2)

# Uber sütunu
with col1:
    st.subheader("Uber")
    st.write(f"Stok: {prices['ub']['count']}")
    st.write(f"Fiyat: {prices['ub']['cost']} ₺")
    
    if st.button("Numara Al (Uber)"):
        order_id, number = get_number("ub")
        if order_id and number:
            st.session_state.active_orders["ub"] = {"id": order_id, "number": number, "code": None}
            st.success("Numara başarıyla alındı!")
            st.rerun()
    
    if "ub" in st.session_state.active_orders:
        order = st.session_state.active_orders["ub"]
        st.markdown(f"""
            <div style="background-color: lightgreen; padding: 10px; border-radius: 5px;">
                <strong>Aktif Sipariş (Uber)</strong><br>
                Numara: {order['number']}<br>
                {"Kod: " + order['code'] if order['code'] else "Kod bekleniyor..."}
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Siparişi İptal Et (Uber)"):
            del st.session_state.active_orders["ub"]
            st.rerun()

# Yemeksepeti sütunu
with col2:
    st.subheader("Yemeksepeti")
    st.write(f"Stok: {prices['yi']['count']}")
    st.write(f"Fiyat: {prices['yi']['cost']} ₺")
    
    if st.button("Numara Al (Yemeksepeti)"):
        order_id, number = get_number("yi")
        if order_id and number:
            st.session_state.active_orders["yi"] = {"id": order_id, "number": number, "code": None}
            st.success("Numara başarıyla alındı!")
            st.rerun()
    
    if "yi" in st.session_state.active_orders:
        order = st.session_state.active_orders["yi"]
        st.markdown(f"""
            <div style="background-color: lightgreen; padding: 10px; border-radius: 5px;">
                <strong>Aktif Sipariş (Yemeksepeti)</strong><br>
                Numara: {order['number']}<br>
                {"Kod: " + order['code'] if order['code'] else "Kod bekleniyor..."}
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Siparişi İptal Et (Yemeksepeti)"):
            del st.session_state.active_orders["yi"]
            st.rerun()

# Kod bekleme ve polling (her rerun'da kontrol et, 10 sn aralıklı)
for service in list(st.session_state.active_orders.keys()):
    order = st.session_state.active_orders[service]
    if order["code"] is None:
        status = get_status(order["id"])
        if status and status.startswith("STATUS_OK:"):
            code = status.split(":")[1]
            order["code"] = code
            message = f"{service.upper()} SMS Kodu: {code} (Numara: {order['number']})"
            send_to_telegram(message)
            st.success(f"{service.upper()} kodu alındı ve Telegram'a gönderildi!")
            st.rerun()
        elif status and "STATUS_WAIT" in status:
            # Bekle ve rerun
            time.sleep(10)  # 10 saniye aralıklı polling
            st.rerun()
        elif status:
            st.error(f"{service.upper()} durum hatası: {status}")
