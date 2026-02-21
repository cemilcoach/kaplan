import streamlit as st
import requests
import time
import json
import hashlib

# --- KONFİGÜRASYON (Secrets'tan Alıyoruz) ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    # Kodun içine şifreyi değil, MD5 özetini gömüyoruz
    # asnaeb68%A şifresinin MD5 özeti:
    MD5_SIFRE_OZETI = "898b9a12c019904790757279165b6f3c"
except KeyError:
    st.error("Lütfen .streamlit/secrets.toml dosyasını oluşturun!")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"

# MD5 Çevirici Fonksiyon
def md5_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

class TigerSMSBot:
    def __init__(self, api_key):
        self.api_key = api_key

    def call_api(self, action, **kwargs):
        params = {"api_key": self.api_key, "action": action}
        params.update(kwargs)
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def get_cheapest_country(self, service_code):
        res = self.call_api("getPrices", service=service_code)
        try:
            data = json.loads(res)
            if service_code in data:
                countries = data[service_code]
                available = {k: v for k, v in countries.items() if v.get('count', 0) > 0}
                if not available: return None
                cheapest_id = min(available, key=lambda x: available[x]['cost'])
                return {"id": cheapest_id, "cost": available[cheapest_id]['cost']}
            return None
        except:
            return None

# --- GİRİŞ KONTROLÜ (MD5) ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 Güvenli SMS Paneli")
        pwd_input = st.text_input("Giriş Şifresi:", type="password")
        if st.button("Giriş Yap"):
            # Girilen şifreyi MD5'e çevirip kontrol ediyoruz
            if md5_hash(pwd_input) == MD5_SIFRE_OZETI:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Hatalı şifre!")
        return False
    return True

# --- ANA UYGULAMA ---
if check_password():
    st.set_page_config(page_title="Tiger SMS Hunter", page_icon="🛒")
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state["authenticated"] = False
        st.rerun()

    bot = TigerSMSBot(API_KEY)
    
    # Bakiye ve Servis Bölümü
    balance_res = bot.call_api("getBalance")
    if "ACCESS_BALANCE" in balance_res:
        balance = balance_res.split(":")[1]
        st.sidebar.metric("Bakiyeniz", f"{balance} RUB")

    st.title("🎯 Yemeksepeti & Uber SMS Paneli")
    service_map = {"Yemeksepeti": "yi", "Uber": "ub"}
    selected_name = st.selectbox("Servis Seçin:", list(service_map.keys()))
    service_code = service_map[selected_name]

    if st.button(f"🚀 {selected_name} İçin En Ucuz Numarayı Al", use_container_width=True):
        with st.spinner("En ucuz stok taranıyor..."):
            cheapest = bot.get_cheapest_country(service_code)
            if cheapest:
                num_res = bot.call_api("getNumber", service=service_code, country=cheapest['id'])
                if "ACCESS_NUMBER" in num_res:
                    parts = num_res.split(":")
                    st.session_state['order_id'] = parts[1]
                    st.session_state['phone'] = parts[2]
                    st.success(f"✅ Numara Hazır: +{parts[2]} (Fiyat: {cheapest['cost']} RUB)")
                else:
                    st.error(f"Hata: {num_res}")
            else:
                st.error("Stok bulunamadı.")

    # Takip Mekanizması
    if 'order_id' in st.session_state:
        st.divider()
        st.markdown(f"### 📱 Numara: `+{st.session_state['phone']}`")
        col_auto, col_manual, col_cancel = st.columns(3)
        
        auto_on = col_auto.checkbox("🔄 Otomatik (3s)")
        manual_go = col_manual.button("🔍 Kontrol Et")
        
        if col_cancel.button("✖️ İptal / İade", type="secondary"):
            bot.call_api("setStatus", id=st.session_state['order_id'], status=8)
            del st.session_state['order_id']
            st.rerun()

        status_area = st.empty()

        if auto_on or manual_go:
            while True:
                check = bot.call_api("getStatus", id=st.session_state['order_id'])
                if "STATUS_OK" in check:
                    code = check.split(":")[1]
                    st.balloons()
                    st.success(f"🎉 KOD: **{code}**")
                    bot.call_api("setStatus", id=st.session_state['order_id'], status=6)
                    del st.session_state['order_id']
                    break
                elif "STATUS_WAIT_CODE" in check:
                    status_area.warning(f"⌛ Bekleniyor... ({time.strftime('%H:%M:%S')})")
                    if manual_go and not auto_on: break
                    time.sleep(3)
                    st.rerun()
                else:
                    status_area.info(f"Durum: {check}")
                    break
