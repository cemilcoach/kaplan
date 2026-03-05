import streamlit as st
import requests

# --- 1. GÖRSEL VE MOBİL AYARLAR ---
st.set_page_config(page_title="Hero SMS Panel", layout="wide", page_icon="🦸")

# Mobil Zoom Engelleyici ve Şık Butonlar
st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0">
    </head>
    <style>
        input, select, textarea { font-size: 16px !important; }
        .stButton>button { width: 100%; border-radius: 12px; height: 4em; font-weight: bold; background-color: #FF4B4B; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SECRETS KONTROLÜ ---
try:
    S = st.secrets
    KEYS = {
        "h": S["HERO_API_KEY"],
        "p": S["PANEL_SIFRESI"]
    }
except Exception as e:
    st.error("Secrets (HERO_API_KEY veya PANEL_SIFRESI) bulunamadı!"); st.stop()

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'order' not in st.session_state: st.session_state.order = None

# --- 4. GİRİŞ KONTROLÜ ---
if not st.session_state.auth:
    st.title("🔐 Hero SMS Giriş")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap") and pwd == KEYS["p"]:
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 5. YAN PANEL (BAKİYE VE FİYATLAR) ---
with st.sidebar:
    st.title("🦸 Hero Kontrol")
    
    # Bakiye Çekme
    try:
        h_b_res = requests.get(f"https://hero-sms.com/stubs/handler_api.php?api_key={KEYS['h']}&action=getBalance", timeout=10).text
        h_bal = h_b_res.split(':')[1] if 'ACCESS' in h_b_res else "0"
        
        # Türkiye (90) Fiyatlarını Çekme
        prices_res = requests.get(f"https://hero-sms.com/stubs/handler_api.php?api_key={KEYS['h']}&action=getPrices&country=90", timeout=10).json()
        tr_prices = prices_res.get("90", {})
        
        uber_price = tr_prices.get("ub", {}).get("cost", "N/A")
        yemek_price = tr_prices.get("yi", {}).get("cost", "N/A")
    except:
        h_bal, uber_price, yemek_price = "Hata", "-", "-"

    st.metric("💰 Mevcut Bakiye", f"{h_bal} $")
    st.divider()
    st.write("🇹🇷 **Türkiye Anlık Fiyatlar:**")
    st.write(f"🚗 Uber: **{uber_price} $**")
    st.write(f"🍔 Yemeksepeti: **{yemek_price} $**")
    
    if st.button("🔄 Verileri Yenile"): st.rerun()

# --- 6. ANA PANEL ---
st.title("🦸 Hero SMS Türkiye Paneli")
st.info("Sistem Türkiye (90) üzerinden en uygun fiyatlı numarayı otomatik olarak talep eder.")

def buy_hero_tr(svc, name):
    with st.spinner(f"{name} numarası alınıyor..."):
        # Action: getNumber, Country: 90 (Türkiye)
        url = f"https://hero-sms.com/stubs/handler_api.php?api_key={KEYS['h']}&action=getNumber&service={svc}&country=90"
        try:
            res = requests.get(url, timeout=15).text
            if "ACCESS" in res:
                p = res.split(":")
                st.session_state.order = {"id": p[1], "num": p[2], "name": name}
                st.toast(f"✅ {name} numarası başarıyla alındı!")
            else:
                st.error(f"Hata: {res} (Stok bitmiş veya bakiye yetersiz olabilir)")
        except:
            st.error("Bağlantı hatası oluştu.")

c1, c2 = st.columns(2)

with c1:
    st.subheader("🚗 Uber")
    if st.button("UBER NUMARA AL"):
        buy_hero_tr("ub", "Uber")

with c2:
    st.subheader("🍔 Yemeksepeti")
    if st.button("YEMEKSEPETİ NUMARA AL"):
        buy_hero_tr("yi", "Yemeksepeti")

# --- 7. SİPARİŞ TAKİP ---
if st.session_state.order:
    ord = st.session_state.order
    st.divider()
    st.success(f"✅ **Aktif {ord['name']} Numarası:** `+{ord['num']}`")
    st.warning("⚠️ Kod geldiğinde Telegram botunuza bildirim düşecektir.")
    
    if st.button("🗑️ İşlemi Kapat / Yeni Numara"):
        st.session_state.order = None; st.rerun()
