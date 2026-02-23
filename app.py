import streamlit as st
from PIL import Image, ImageFilter
import wikipedia
import requests
from io import BytesIO
import random
import time
import json
import os
import base64

# --- Sayfa Ayarları ---
st.set_page_config(page_title="⚽ Profesyonel Futbolcu Tahmin", layout="centered")

# --- Ses Çalma Fonksiyonu ---
def play_sound(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
            st.components.v1.html(md, height=0)

# --- Wikipedia'dan Resim Çekme (Otomatik) ---
@st.cache_data(ttl=86400)
def get_wiki_image(player_name):
    try:
        # Wikipedia'da arama yap (Doğru kişiyi bulmak için 'footballer' ekliyoruz)
        search_results = wikipedia.search(player_name + " (footballer)")
        if not search_results:
            return None
        
        page = wikipedia.page(search_results[0], auto_suggest=False)
        # Sadece .jpg veya .png olanları al, logoları (.svg) ele
        images = [img for img in page.images if img.lower().endswith(('.jpg', '.png', '.jpeg')) and "logo" not in img.lower()]
        return images[0] if images else None
    except:
        return None

@st.cache_data
def fetch_image(url):
    response = requests.get(url, timeout=10)
    return Image.open(BytesIO(response.content)).convert("RGB")

# --- Veri Yükleme ---
def load_data():
    if os.path.exists('players.json'):
        with open('players.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

players_by_diff = load_data()

# --- Session State Başlatma ---
if "game_init" not in st.session_state:
    st.session_state.game_init = False
    st.session_state.total_score = 0
    st.session_state.current_question = 1
    st.session_state.played_names = []
    st.session_state.target_player = None

# --- BAŞLANGIÇ EKRANI ---
if not st.session_state.game_init:
    st.title("⚽ Profesyonel Futbolcu Tahmin")
    st.subheader("Hoş geldin! Bir zorluk seç ve maratona başla.")
    
    diff = st.selectbox("Zorluk Seviyesi (Futbolcular buna göre filtrelenir):", ["Kolay", "Orta", "Zor"])
    
    if st.button("Oyunu Başlat"):
        st.session_state.difficulty = diff
        # Zorluğa göre bulanıklık ayarları
        if diff == "Kolay":
            st.session_state.blur_levels, st.session_state.multiplier = [12, 8, 5, 2, 0], 1
        elif diff == "Orta":
            st.session_state.blur_levels, st.session_state.multiplier = [25, 15, 8, 3, 0], 2
        else:
            st.session_state.blur_levels, st.session_state.multiplier = [45, 30, 15, 5, 0], 3
            
        st.session_state.game_init = True
        st.rerun()
    st.stop()

# --- Soru Seçme Fonksiyonu ---
def pick_new_player():
    if players_by_diff is None: return
    
    # Sadece seçilen zorluktaki listeyi al
    pool = players_by_diff[st.session_state.difficulty]
    # Oynanmamış olanları filtrele
    available = [p for p in pool if p['name'] not in st.session_state.played_names]
    
    if available and st.session_state.current_question <= 5: # 5 Soru Sınırı
        target = random.choice(available)
        st.session_state.target_player = target
        st.session_state.played_names.append(target['name'])
        st.session_state.attempts = 0
    else:
        st.session_state.game_finished = True

# İlk soru seçimi
if st.session_state.target_player is None and not getattr(st.session_state, 'game_finished', False):
    pick_new_player()

# --- OYUN BİTİŞ EKRANI ---
if getattr(st.session_state, 'game_finished', False):
    st.balloons()
    st.header("🏆 Tur Tamamlandı!")
    st.metric("Toplam Puan", st.session_state.total_score)
    if st.button("🔄 Tekrar Oyna"):
        # Resetle
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.stop()

# --- OYUN ARAYÜZÜ ---
st.title(f"Soru {st.session_state.current_question}/5")
player = st.session_state.target_player

# Resim Çekme ve İşleme
image_url = get_wiki_image(player['name'])
image_placeholder = st.empty()

if image_url:
    raw_img = fetch_image(image_url)
    blur_val = st.session_state.blur_levels[min(st.session_state.attempts, 4)]
    blurred_img = raw_img.filter(ImageFilter.GaussianBlur(blur_val))
    image_placeholder.image(blurred_img, use_container_width=True)
else:
    st.warning("Resim bulunamadı, bu soru atlanıyor...")
    st.session_state.target_player = None
    st.rerun()

# İpucu Paneli
with st.expander("💡 İpuçları", expanded=True):
    if st.session_state.attempts > 0: st.info(f"🌍 Milliyet: {player['nationality']}")
    if st.session_state.attempts > 1: st.info(f"✨ İkonik An: {player['moment']}")

# Tahmin Formu
with st.form("guess_form", clear_on_submit=True):
    user_guess = st.text_input("Bu futbolcu kim?").lower().strip()
    c1, c2 = st.columns(2)
    submit = c1.form_submit_button("Tahmin Et", use_container_width=True)
    pass_btn = c2.form_submit_button("Pas Geç", use_container_width=True)

# --- MANTIK ---
correct_name = player['name'].lower()

if submit:
    if user_guess != "" and (user_guess in correct_name and len(user_guess) > 3):
        # DOĞRU
        play_sound("sounds/goal.mp3")
        image_placeholder.image(raw_img, use_container_width=True, caption=f"DOĞRU! Cevap: {player['name']}")
        gain = (5 - st.session_state.attempts) * 20 * st.session_state.multiplier
        st.session_state.total_score += gain
        st.success(f"✅ Harika! +{gain} puan.")
        time.sleep(3)
        st.session_state.target_player = None
        st.session_state.current_question += 1
        pick_new_player()
        st.rerun()
    else:
        # YANLIŞ
        st.session_state.attempts += 1
        if st.session_state.attempts >= 5:
            play_sound("sounds/whistle.mp3")
            image_placeholder.image(raw_img, use_container_width=True, caption=f"Cevap: {player['name']}")
            st.error(f"❌ Hak bitti! Doğru cevap: {player['name']}")
            time.sleep(3)
            st.session_state.target_player = None
            st.session_state.current_question += 1
            pick_new_player()
            st.rerun()
        else:
            st.rerun()

if pass_btn:
    image_placeholder.image(raw_img, use_container_width=True, caption=f"Cevap: {player['name']}")
    st.info(f"⏭️ Pas geçildi. Cevap: {player['name']}")
    time.sleep(3)
    st.session_state.target_player = None
    st.session_state.current_question += 1
    pick_new_player()
    st.rerun()

