import streamlit as st
import requests
import time

# --- 1. Mobil Uyumluluk Ayarları ---
st.set_page_config(page_title="SMS Panel TR", layout="wide")

st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
    input, button { font-size: 16px !important; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #007bff; color: white; font-weight: bold; }
    .status-card { padding: 15px; border-radius: 12px; background-color: #e3f2fd; border-left: 6px solid #1565c0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Güvenlik ve Secrets ---
# Önceki konuşmalarımızdaki bilgileri buraya sabitledim
API_KEY = "6ce1bb5837f81db1f4cA0b341Ac58956"
PANEL_PASS = "asnaeb68%A"
TG_TOKEN = "8443974633:AAEErjkHLykfsNdbvaty_5Z02YUJ3oPQx0E"
TG_CHAT_ID = "1009360711"
BASE_URL = "https://hero-sms.com/stubs/handler_api.php"

# --- 3. Fonksiyonlar ---
def get_balance():
    url = f"{BASE_URL}?api_key={API_KEY}&action=getBalance"
    try:
        res = requests.get(url).text
        return res.split(":")[1] if "ACCESS_BALANCE" in res else "0.00"
    except: return "Hata"

def get_data_tr():
    # Türkiye fiyatlarını çekmek için parametreyi URL'e gömüyoruz
    url = f"{BASE_URL}?api_key={API_KEY}&action=getPrices&country=90"
    try:
        res = requests.get(url).json()
        tr_data = res.get("90", {}) # Doküman: Yanıt anahtarı ülke ID'sidir
        return {
            "ub": tr_data.get("ub", {"cost": 0, "count": 0}),
            "yi": tr_data.get("yi", {"cost": 0, "count": 0})
        }
    except: return None

# --- 4. Panel Girişi ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pw = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap") and pw == PANEL_PASS:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- 5. Ana Ekran ---
st.sidebar.metric("TR Bakiye", f"{get_balance()} ₽")
st.title("🇹🇷 Türkiye SMS Kiralama")

if "order" not in st.session_state: st.session_state.order = None

prices = get_data_tr()

if prices:
    c1, c2 = st.columns(2)
    services = [("Uber (ub)", prices["ub"], "ub"), ("Yemeksepeti (yi)", prices["yi"], "yi")]
    
    for idx, (label, data, srv_code) in enumerate(services):
        with (c1 if idx == 0 else c2):
            st.subheader(label)
            st.write(f"Fiyat: **{data['cost']} ₽**")
            st.write(f"Stok: **{data['count']}**")
            
            # NUMARA ALMA BUTONU
            if st.button(f"Numara Al", key=srv_code, disabled=st.session_state.order is not None):
                # Dokümana tam uyumlu kesin parametreli URL (country=90)
                order_url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={srv_code}&country=90"
                res = requests.get(order_url).text
                
                if "ACCESS_NUMBER" in res:
                    parts = res.split(":")
                    st.session_state.order = {"id": parts[1], "num": parts[2], "name": label}
                    # Durumu SMS bekliyor (1) olarak güncelle
                    requests.get(f"{BASE_URL}?api_key={API_KEY}&action=setStatus&id={parts[1]}&status=1")
                    st.rerun()
                else:
                    st.error(f"Hata: {res}")

# --- 6. Sipariş ve SMS Takibi ---
if st.session_state.order:
    ord = st.session_state.order
    st.divider()
    st.markdown(f"""<div class="status-card">
        <h3>⚡ Aktif Sipariş: {ord['name']}</h3>
        <p><b>Numara:</b> <span style='font-size:22px;'>+{ord['num']}</span></p>
        <p>ID: {ord['id']}</p>
    </div>""", unsafe_allow_html=True)

    # SMS Kodu Sorgulama
    if "code" not in ord:
        with st.spinner("Kod bekleniyor (Otomatik yenilenir)..."):
            status_url = f"{BASE_URL}?api_key={API_KEY}&action=getStatus&id={ord['id']}"
            check = requests.get(status_url).text
            
            if "STATUS_OK" in check:
                sms_code = check.split(":")[1]
                st.session_state.order["code"] = sms_code
                # Telegram Bildirimi
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              json={"chat_id": TG_CHAT_ID, "text": f"📩 KOD GELDİ!\nServis: {ord['name']}\nNo: {ord['num']}\nKod: {sms_code}"})
                st.rerun()
            else:
                time.sleep(5)
                st.rerun()

    if "code" in ord:
        st.success(f"📟 SMS KODU: **{ord['code']}**")
        if st.button("✅ İşlemi Onayla ve Kapat"):
            requests.get(f"{BASE_URL}?api_key={API_KEY}&action=setStatus&id={ord['id']}&status=6")
            st.session_state.order = None
            st.rerun()

    if st.button("❌ İptal Et (Ücret İadesi)"):
        requests.get(f"{BASE_URL}?api_key={API_KEY}&action=setStatus&id={ord['id']}&status=8")
        st.session_state.order = None
        st.rerun()
