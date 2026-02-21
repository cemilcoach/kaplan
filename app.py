import streamlit as st
import requests
import time
import json

# 1. SAYFA AYARLARI (En üstte olmak zorundadır)
st.set_page_config(page_title="Multi-SMS Hunter", layout="wide", page_icon="🚀")

# --- KONFİGÜRASYON VE GÜVENLİK ---
try:
    API_KEY = st.secrets["TIGER_API_KEY"]
    PANEL_SIFRESI = st.secrets["PANEL_SIFRESI"]
except KeyError:
    st.error("🚨 Lütfen .streamlit/secrets.toml dosyasını oluşturun ve bilgileri girin!")
    st.stop()

BASE_URL = "https://api.tiger-sms.com/stubs/handler_api.php"

# --- API SINIFI ---
class TigerSMSBot:
    def __init__(self, api_key):
        self.api_key = api_key

    def call_api(self, action, **kwargs):
        params = {"api_key": self.api_key, "action": action}
        params.update(kwargs)
        try:
            r = requests.get(BASE_URL, params=params, timeout=10)
            return r.text
        except:
            return "ERROR"

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
        except: return None

# --- GİRİŞ EKRANI (Şifre Kontrolü) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Güvenli SMS Paneli")
    pwd_input = st.text_input("Şifrenizi Girin:", type="password")
    
    if st.button("Giriş Yap"):
        # Boşlukları temizleyip direkt secrets'taki şifre ile karşılaştırıyoruz
        if pwd_input.strip() == PANEL_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: 
            st.error("❌ Hatalı şifre! Lütfen tekrar deneyin.")
    st.stop() # Doğru şifre girilene kadar alttaki kodlar çalışmaz

# --- SİSTEM BAŞLANGICI ---
bot = TigerSMSBot(API_KEY)

# Önbellek (Cache) Listesi
if 'active_orders' not in st.session_state:
    st.session_state['active_orders'] = []

# --- SOL MENÜ (SIDEBAR) ---
balance_res = bot.call_api("getBalance")
balance = balance_res.split(":")[1] if "ACCESS_BALANCE" in balance_res else "0"
st.sidebar.metric("💰 Güncel Bakiyeniz", f"{balance} RUB")

st.sidebar.divider()
canli_takip = st.sidebar.toggle("🟢 Canlı Takip (2s Yenileme)", value=True)

if st.sidebar.button("🚪 Güvenli Çıkış"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- ANA EKRAN: NUMARA ALMA BUTONLARI ---
st.title("🚀 Çoklu Numara Paneli")
col_yem, col_ub = st.columns(2)

def buy_number(s_name, s_code):
    with st.spinner(f"{s_name} için en uygun numara aranıyor..."):
        cheapest = bot.get_cheapest_country(s_code)
        if cheapest:
            num_res = bot.call_api("getNumber", service=s_code, country=cheapest['id'])
            if "ACCESS_NUMBER" in num_res:
                parts = num_res.split(":")
                new_order = {
                    "id": parts[1],
                    "phone": parts[2],
                    "service": s_name,
                    "time": time.time(),
                    "status": "SMS Bekleniyor",
                    "code": None
                }
                st.session_state['active_orders'].append(new_order)
                st.success(f"✅ Yeni {s_name} numarası eklendi: +{parts[2]} (Fiyat: {cheapest['cost']} RUB)")
            else: 
                st.error(f"Hata: {num_res}")
        else: 
            st.error(f"{s_name} için şu an uygun stok bulunamadı!")

if col_yem.button("🍔 YEMEKSEPETİ AL", use_container_width=True):
    buy_number("Yemeksepeti", "yi")

if col_ub.button("🚗 UBER AL", use_container_width=True):
    buy_number("Uber", "ub")

st.divider()

# --- AKTİF NUMARALAR VE TAKİP LİSTESİ ---
st.subheader("📋 Aktif İşlemler")

if not st.session_state['active_orders']:
    st.info("Henüz aktif bir işlem yok. Yukarıdaki butonlardan numara alabilirsiniz.")

for order in st.session_state['active_orders']:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        
        c1.write(f"**Servis:** {order['service']}")
        c1.write(f"**Numara:** `+{order['phone']}`")
        
        # API'den Durum Sorgulama
        if order['code'] is None:
            check = bot.call_api("getStatus", id=order['id'])
            if "STATUS_OK" in check:
                order['code'] = check.split(":")[1]
                order['status'] = "✅ TAMAMLANDI"
                bot.call_api("setStatus", id=order['id'], status=6) # İşlemi başarılı kapat
            elif "STATUS_WAIT_CODE" in check:
                gecen_sure_gorsel = int(time.time() - order['time'])
                dakika, saniye = divmod(gecen_sure_gorsel, 60)
                order['status'] = f"⌛ Bekliyor ({dakika:02d}:{saniye:02d})"
            elif "STATUS_CANCEL" in check:
                order['status'] = "❌ İptal Edildi"
        
        # Durum ve Kod Gösterimi
        c2.write(f"**Durum:** {order['status']}")
        if order['code']:
            c2.success(f"**KOD: {order['code']}**")

        # 2 Dakikalık İptal Butonu Mantığı
        gecen_sure = time.time() - order['time']
        kalan_sure = max(0, 120 - int(gecen_sure))
        
        if order['code'] is None and "İptal" not in order['status']:
            if kalan_sure > 0:
                # 2 dakika dolana kadar buton pasif kalır ve saniye sayar
                c3.button(f"İptal ({kalan_sure}s)", key=f"wait_{order['id']}", disabled=True)
            else:
                # Süre dolunca iptal butonu aktifleşir
                if c3.button("✖️ İptal Et & İade Al", key=f"can_{order['id']}"):
                    bot.call_api("setStatus", id=order['id'], status=8)
                    st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
                    st.rerun()
        
        # Sil Butonu
        if c4.button("🗑️ Sil", key=f"del_{order['id']}"):
            st.session_state['active_orders'] = [o for o in st.session_state['active_orders'] if o['id'] != order['id']]
            st.rerun()

# --- OTOMATİK YENİLEME ---
if canli_takip and len(st.session_state['active_orders']) > 0:
    time.sleep(2)
    st.rerun()
