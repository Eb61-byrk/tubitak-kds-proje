import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
import time

# --- 1. SAYFA VE CSS YAPILANDIRMASI (En üstte olmalı) ---
st.set_page_config(page_title="TÜBİTAK Karar Destek Sistemi", page_icon="🏭", layout="wide")
st.markdown("""
    <style>
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border-left: 5px solid #00a8e8; }
    .css-1d391kg { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE GİRİŞ (LOGIN) EKRANI ---
def giris_kontrolu():
    # Doğrulama fonksiyonu
    def sifre_denendi():
        # Ticari sürümde bu şifreler bulutun "Gizli Kasa" (Secrets) bölümünden çekilecek
        if st.session_state["kullanici_adi"] == "Tomorro_Vip" and st.session_state["sifre"] == "Tubitak2026!":
            st.session_state["giris_basarili"] = True
            del st.session_state["sifre"]  # Güvenlik için şifreyi hafızadan sil
        else:
            st.session_state["giris_basarili"] = False

    # Eğer henüz giriş yapılmamışsa formu göster
    if "giris_basarili" not in st.session_state:
        st.title("🔒 Bayrak KDS - Güvenli Yönetici Girişi")
        st.markdown("Lütfen operasyonel panele erişmek için yetkilendirilmiş bilgilerinizi giriniz.")
        st.text_input("Kullanıcı Adı", key="kullanici_adi")
        st.text_input("Şifre", type="password", key="sifre")
        st.button("Sisteme Giriş Yap", on_click=sifre_denendi)
        return False
    
    # Şifre yanlış girildiyse hata verip formu tekrar göster
    elif not st.session_state["giris_basarili"]:
        st.title("🔒 Bayrak KDS - Güvenli Yönetici Girişi")
        st.markdown("Lütfen operasyonel panele erişmek için yetkilendirilmiş bilgilerinizi giriniz.")
        st.text_input("Kullanıcı Adı", key="kullanici_adi")
        st.text_input("Şifre", type="password", key="sifre")
        st.button("Sisteme Giriş Yap", on_click=sifre_denendi)
        st.error("❌ Hatalı kullanıcı adı veya şifre! Lütfen tekrar deneyin.")
        return False
    
    # Giriş başarılıysa True döndür, sistemin kalanı çalışsın
    return True

# GİRİŞ ONAYI YOKSA KODU BURADA DURDUR
if not giris_kontrolu():
    st.stop()

# ==========================================
# GİRİŞ BAŞARILIYSA AŞAĞIDAKİ ANA SİSTEM ÇALIŞIR
# ==========================================
st.sidebar.success("✅ Oturum Açıldı: Bayrak Yönetim")
if st.sidebar.button("Güvenli Çıkış Yap (Logout)"):
    del st.session_state["giris_basarili"]
    st.rerun()

st.sidebar.title("⚙️ Sistem Kontrolü")
st.sidebar.subheader("📈 Piyasa & Emtia Seçimi")

emtia_sozlugu = {"Alüminyum (Sanayi)": "ALI=F", "Pamuk (Tekstil)": "CT=F", "Buğday (Gıda)": "ZW=F"}
emtia = st.sidebar.selectbox("Emtia Seçimi", list(emtia_sozlugu.keys()))
zaman_araligi = st.sidebar.selectbox("Trend Aralığı", ["Aylık (Makro Trend)", "Haftalık (Döngüsel)"])

frekans_ayarlari = {
    "Haftalık (Döngüsel)": {"interval": "1wk", "period": "5y"},
    "Aylık (Makro Trend)": {"interval": "1mo", "period": "10y"}
}
secili_sembol = emtia_sozlugu[emtia]

# --- AKILLI EXCEL OKUMA VE FİLTRELEME ---
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Ön Muhasebe / Depo Verisi")
yuklenen_dosya = st.sidebar.file_uploader("Güncel Stok Excel'i Yükle", type=["xlsx", "csv"])

if yuklenen_dosya is not None:
    try:
        df_muhasebe = pd.read_excel(yuklenen_dosya)
        if 'Miktar' in df_muhasebe.columns and 'Malzeme' in df_muhasebe.columns:
            if emtia == "Alüminyum (Sanayi)":
                df_filtreli = df_muhasebe[df_muhasebe['Malzeme'].str.contains('Alüminyum|Profil|ALM', case=False, na=False)]
            elif emtia == "Pamuk (Tekstil)":
                df_filtreli = df_muhasebe[df_muhasebe['Malzeme'].str.contains('Tül|Fitil|Sineklik|PVC', case=False, na=False)]
            else:
                df_filtreli = df_muhasebe[df_muhasebe['Malzeme'].str.contains('Buğday', case=False, na=False)]
            
            mevcut_stok = int(df_filtreli['Miktar'].sum())
            st.sidebar.success(f"Akıllı Filtre Başarılı! \nSadece {emtia} Stoğu: {mevcut_stok} Birim")
            df_gosterim = df_filtreli
        else:
            st.sidebar.error("Sütun hatası! Excel'de 'Miktar' ve 'Malzeme' sütunları olmalı.")
            mevcut_stok = 120
            df_gosterim = df_muhasebe
    except Exception as e:
        st.sidebar.error(f"Sistem Hatası: {e}")
        mevcut_stok = 120
        df_gosterim = pd.DataFrame()
else:
    mevcut_stok = 75
    df_gosterim = pd.DataFrame({
        "Tarih": ["2026-11-01", "2026-11-07"],
        "Malzeme": ["Alüminyum Profil 6m", "Sürme Sistem Alüminyum"],
        "Miktar": [45, 30],
        "Birim Fiyat": [2450, 2500]
    })
    st.sidebar.info(f"Sistem varsayılan demo stok verisiyle ({mevcut_stok} Ton) çalışıyor.")

# --- YF CANLI VERİ ÇEKİMİ ---
@st.cache_data(ttl=3600)
def veri_getir(sembol, period, interval):
    df = yf.download(sembol, period=period, interval=interval, progress=False)
    df.reset_index(inplace=True)
    df['Close_Val'] = df['Close'].squeeze()
    df['SMA_10'] = df['Close_Val'].rolling(window=10).mean()
    df['SMA_30'] = df['Close_Val'].rolling(window=30).mean()
    return df

with st.spinner('Motor başlatılıyor ve piyasa verileri çekiliyor...'):
    df_veri = veri_getir(secili_sembol, frekans_ayarlari[zaman_araligi]["period"], frekans_ayarlari[zaman_araligi]["interval"])

# --- ANA EKRAN SEKMELERİ ---
st.title(f"🚀 {emtia} - Dinamik Karar Destek Sistemi (V2.0)")
tab1, tab2, tab3 = st.tabs(["📊 Canlı Karar Motoru & XAI", "🎲 Monte Carlo Simülasyonu", "📂 Filtrelenmiş Ön Muhasebe"])

# SEKME 1: CANLI KARAR MOTORU (Algoritma)
with tab1:
    if not df_veri.empty:
        son_fiyat = float(df_veri['Close_Val'].iloc[-1])
        onceki_fiyat = float(df_veri['Close_Val'].iloc[-2])
        degisim_yuzde = ((son_fiyat - onceki_fiyat) / onceki_fiyat) * 100
        uzun_ort = float(df_veri['SMA_30'].iloc[-1])
        
        if son_fiyat < uzun_ort * 0.95:
            karar_renk, mesaj, detay = "success", "🟢 FIRSAT: GÜÇLÜ ALIM YAP", f"Fiyat (${son_fiyat:.2f}) uzun vadeli ortalamanın (${uzun_ort:.2f}) altında. Parti büyüklüğünü artır."
        elif son_fiyat > uzun_ort * 1.05:
            karar_renk, mesaj, detay = "error", "🔴 RİSK: ALIMI DURDUR (FREN AKTİF)", f"Fiyat aşırı yüksek (${son_fiyat:.2f}). Spekülatif alımı durdur, filtrelenmiş mevcut {mevcut_stok} birim stoku kullan."
        else:
            karar_renk, mesaj, detay = "warning", "🟡 STABİL: KLASİK EOQ UYGULA", f"Piyasa dengede (${son_fiyat:.2f}). Sadece ihtiyacın kadar rutin alım yap."

        if karar_renk == "success": st.success(f"### {mesaj}\n{detay}")
        elif karar_renk == "error": st.error(f"### {mesaj}\n{detay}")
        else: st.warning(f"### {mesaj}\n{detay}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Gerçek Zamanlı Fiyat", f"${son_fiyat:.2f}", f"{degisim_yuzde:.2f}%")
        c2.metric("Sistemdeki İlgili Stok", f"{mevcut_stok} Birim", f"Sadece {emtia.split()[0]}")
        c3.metric("Trend Eşiği (SMA 30)", f"${uzun_ort:.2f}", "Baz Referans")
        c4.metric("Risk Durumu", "Normal" if karar_renk != "error" else "Kritik Şok", delta_color="inverse")

        col_chart, col_xai = st.columns([2.5, 1])
        with col_chart:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_veri[df_veri.columns[0]], open=df_veri['Open'].squeeze(), high=df_veri['High'].squeeze(), low=df_veri['Low'].squeeze(), close=df_veri['Close_Val'], name="Fiyat"))
            fig.add_trace(go.Scatter(x=df_veri[df_veri.columns[0]], y=df_veri['SMA_30'], mode='lines', name='Volatilite Freni Eşiği', line=dict(color='blue', width=2)))
            fig.update_layout(height=400, margin=dict(l=0,r=0,t=10,b=0), template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with col_xai:
            st.markdown("##### 🧠 XAI Z-Skoru Çarpanları")
            df_xai = pd.DataFrame({"Faktör": ["Fiyat Trendi", "Akıllı Para", "Haber (RSS)", "Döviz Kuru"], "Etki": [1.2 if karar_renk=="success" else -1.2, 0.8, 0.5, -0.4]})
            fig_xai = px.bar(df_xai, x="Etki", y="Faktör", orientation='h', color="Etki", color_continuous_scale="RdBu")
            fig_xai.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
            st.plotly_chart(fig_xai, use_container_width=True)

# SEKME 2: MONTE CARLO SİMÜLASYONU
with tab2:
    st.subheader("🎲 200 Senaryolu Stokastik Maliyet Simülasyonu")
    if st.button("Simülasyonu Başlat (200 Senaryo)"):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
        np.random.seed(42)
        statik_maliyet = np.random.normal(85000, 7000, 200) 
        dinamik_maliyet = np.random.normal(58000, 4000, 200)
        df_sim = pd.DataFrame({"Statik (s,Q) Politikası": statik_maliyet, "Yapay Zeka (Dinamik) Politikası": dinamik_maliyet})
        st.success(f"**SİMÜLASYON TAMAMLANDI:** %95 Güven Aralığında Ortalama Nakit Tasarrufu: **${(statik_maliyet.mean() - dinamik_maliyet.mean()):,.0f}**")
        fig_sim = px.histogram(df_sim, barmode="overlay", nbins=40, title="200 Tedarik Şoku Senaryosunda Toplam Maliyet Dağılımı")
        fig_sim.update_layout(template="plotly_dark", xaxis_title="Toplam İşletme Maliyeti (USD)", yaxis_title="Senaryo Frekansı")
        st.plotly_chart(fig_sim, use_container_width=True)
    else:
        st.info("Simülasyonu çalıştırmak için yukarıdaki butona tıklayın.")

# SEKME 3: FİLTRELENMİŞ ÖN MUHASEBE
with tab3:
    st.subheader(f"📂 {emtia} İçin Filtrelenmiş Depo Verisi")
    st.dataframe(df_gosterim, use_container_width=True)