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

# --- Wikipedia Kimlik Tanımlama (Erişim Engeli İçin) ---
wikipedia.set_user_agent("FutbolTahminOyunu/1.0 (iletisim@ornek.com)")

# --- Sayfa Ayarları ---
st.set_page_config(page_title="⚽ Futbolcu Tahmin Maratonu", layout="centered")

# --- Ses Çalma Fonksiyonu ---
def play_sound(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            md = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
            st.components.v1.html(md, height=0)

# --- Wikipedia'dan Resim Çekme ---
@st.cache_data(ttl=86400)
def get_wiki_image(player_name):
    try:
        search_results = wikipedia.search(player_name + " footballer")
        if not search_results:
            return None
        
        page = wikipedia.page(search_results[0], auto_suggest=False)
        
        # Sadece gerçek resim formatlarını al
        valid_images = [img for img in page.images if img.lower().endswith(('.jpg', '.jpeg', '.png')) 
                        and "logo" not in img.lower() 
                        and "flag" not in img.lower()
                        and "icon" not in img.lower()]
        
        return valid_images[0] if valid_images else None
    except:
        return None

# --- Resim İndirme (Tarayıcı Taklidi İle) ---
@st.cache_data
def fetch_image(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            return img.convert("RGB")
        return None
    except:
        return None

# --- Veri Yükleme ---
def load_data():
    if os.path.exists('players.json'):
        with open('players.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

players_by_diff = load_data()

# --- Session State Başlatma ---
if "game_init" not in st.session_state:
    st.session_state.update({
        "game_init": False,
        "total_score": 0,
        "current_question": 1,
        "played_names": [],
        "target_player": None,
        "attempts": 0,
        "game_finished": False
    })

# --- BAŞLANGIÇ EKRANI ---
if not st.session_state.game_init:
    st.title("⚽ Futbolcu Tahmin Maratonu")
    
    if players_by_diff:
        diff = st.selectbox("Zorluk Seviyesi Seçin:", list(players_by_diff.keys()))
        if st.button("Oyuna Başla"):
            st.session_state.difficulty = diff
            if diff == "Kolay":
                st.session_state.blur_levels, st.session_state.multiplier = [15, 10, 5, 2, 0], 1
            elif diff == "Orta":
                st.session_state.blur_levels, st.session_state.multiplier = [30, 20, 10, 5, 0], 2
            else:
                st.session_state.blur_levels, st.session_state.multiplier = [50, 35, 20, 8, 0], 3
            st.session_state.game_init = True
            st.rerun()
    else:
        st.error("players.json dosyası bulunamadı!")
    st.stop()

# --- Soru Seçme ---
def pick_new_player():
    pool = players_by_diff[st.session_state.difficulty]
    available = [p for p in pool if p['name'] not in st.session_state.played_names]
    
    if available and st.session_state.current_question <= 5:
        target = random.choice(available)
        st.session_state.target_player = target
        st.session_state.played_names.append(target['name'])
        st.session_state.attempts = 0
    else:
        st.session_state.game_finished = True

if st.session_state.target_player is None and not st.session_state.game_finished:
    pick_new_player()

# --- OYUN BİTİŞ ---
if st.session_state.game_finished:
    st.balloons()
    st.header("🏆 Tur Tamamlandı!")
    st.metric("Toplam Puan", st.session_state.total_score)
    if st.button("🔄 Tekrar Oyna"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.stop()

# --- ANA OYUN EKRANI ---
st.title(f"Soru {st.session_state.current_question}/5")
player = st.session_state.target_player
image_placeholder = st.empty()

# Resim Süreci
image_url = get_wiki_image(player['name'])
if image_url:
    raw_img = fetch_image(image_url)
    if raw_img:
        idx = min(st.session_state.attempts, 4)
        blur_val = st.session_state.blur_levels[idx]
        display_img = raw_img.filter(ImageFilter.GaussianBlur(blur_val)) if blur_val > 0 else raw_img
        image_placeholder.image(display_img, use_container_width=True)
    else:
        st.warning("Resim indirilemedi, yeni oyuncu seçiliyor...")
        time.sleep(1)
        st.session_state.target_player = None
        st.rerun()
else:
    st.warning("Resim bulunamadı, yeni oyuncu seçiliyor...")
    st.session_state.target_player = None
    st.rerun()

# İpuçları
with st.expander("💡 İpucu Al", expanded=True):
    if st.session_state.attempts > 0: st.info(f"🌍 Milliyet: {player['nationality']}")
    if st.session_state.attempts > 1: st.info(f"✨ İkonik An: {player['moment']}")

# Tahmin Girişi
with st.form("guess_form", clear_on_submit=True):
    user_guess = st.text_input("Bu futbolcu kim?").lower().strip()
    col1, col2 = st.columns(2)
    submit = col1.form_submit_button("Tahmin Et", use_container_width=True)
    pass_btn = col2.form_submit_button("Pas Geç", use_container_width=True)

if submit:
    correct_name = player['name'].lower()
    if user_guess and (user_guess in correct_name and len(user_guess) > 3):
        play_sound("sounds/goal.mp3")
        image_placeholder.image(raw_img, use_container_width=True, caption=f"TEBRİKLER! {player['name']}")
        puan = (5 - st.session_state.attempts) * 20 * st.session_state.multiplier
        st.session_state.total_score += puan
        st.success(f"✅ DOĞRU! +{puan} Puan")
        time.sleep(3)
        st.session_state.target_player = None
        st.session_state.current_question += 1
        st.rerun()
    else:
        st.session_state.attempts += 1
        if st.session_state.attempts >= 5:
            play_sound("sounds/whistle.mp3")
            image_placeholder.image(raw_img, use_container_width=True, caption=f"Cevap: {player['name']}")
            st.error(f"❌ Hak bitti! Cevap: {player['name']}")
            time.sleep(3)
            st.session_state.target_player = None
            st.session_state.current_question += 1
            st.rerun()
        else:
            st.warning(f"❌ Yanlış! {5 - st.session_state.attempts} hakkınız kaldı.")
            st.rerun()

# --- PAS GEÇME MANTIĞI (GÜNCELLENDİ) ---
if pass_btn:
    # Resmi netleştir ve ismi göster
    image_placeholder.image(raw_img, use_container_width=True, caption=f"Pas Geçildi. Cevap: {player['name']}")
    st.info(f"⏭️ Pas geçtiniz. Doğru cevap: **{player['name']}**")
    
    # 3 saniye bekle
    time.sleep(3)
    
    # Sonraki soruya geç
    st.session_state.target_player = None
    st.session_state.current_question += 1
    st.rerun()
