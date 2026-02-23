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
st.set_page_config(page_title="⚽ Futbolcu Tahmin Oyunu", layout="centered")

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
        search_results = wikipedia.search(player_name + " (footballer)")
        if not search_results:
            return None
        
        page = wikipedia.page(search_results[0], auto_suggest=False)
        # Sadece .jpg ve .png al, logoları ve .svg dosyalarını ele (Hata kaynağı budur)
        images = [img for img in page.images if img.lower().endswith(('.jpg', '.png', '.jpeg')) 
                  and "logo" not in img.lower() 
                  and "icon" not in img.lower()]
        return images[0] if images else None
    except:
        return None

# --- Gelişmiş Resim İndirme (Hata Korumalı) ---
@st.cache_data
def fetch_image(url):
    try:
        response = requests.get(url, timeout=10)
        # Gelen veriyi açmayı dene
        img = Image.open(BytesIO(response.content))
        # RGB'ye çevirerek format uyumsuzluğunu (RGBA vb.) engelle
        return img.convert("RGB")
    except Exception:
        # Resim okunamıyorsa (UnidentifiedImageError) None döndür
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
    diff = st.selectbox("Zorluk Seviyesi Seçin:", ["Kolay", "Orta", "Zor"])
    
    if st.button("Oyuna Başla"):
        st.session_state.difficulty = diff
        if diff == "Kolay":
            st.session_state.blur_levels, st.session_state.multiplier = [12, 8, 5, 2, 0], 1
        elif diff == "Orta":
            st.session_state.blur_levels, st.session_state.multiplier = [25, 15, 8, 3, 0], 2
        else:
            st.session_state.blur_levels, st.session_state.multiplier = [45, 30, 15, 5, 0], 3
            
        st.session_state.game_init = True
        st.rerun()
    st.stop()

# --- Soru Seçme ---
def pick_new_player():
    if not players_by_diff: return
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

# --- ARAYÜZ ---
st.title(f"Soru {st.session_state.current_question}/5")
player = st.session_state.target_player
image_url = get_wiki_image(player['name'])
image_placeholder = st.empty()

if image_url:
    raw_img = fetch_image(image_url)
    
    if raw_img: # Resim sağlamsa göster
        blur_val = st.session_state.blur_levels[min(st.session_state.attempts, 4)]
        blurred_img = raw_img.filter(ImageFilter.GaussianBlur(blur_val))
        image_placeholder.image(blurred_img, use_container_width=True)
    else: # Resim bozuksa (UnidentifiedImageError buraya düşer)
        st.warning(f"Resim yüklenemedi: {player['name']}. Atlanıyor...")
        time.sleep(1.5)
        st.session_state.target_player = None
        st.rerun()
else:
    st.session_state.target_player = None
    st.rerun()

with st.expander("💡 İpucu Al", expanded=True):
    if st.session_state.attempts > 0: st.info(f"🌍 Milliyet: {player['nationality']}")
    if st.session_state.attempts > 1: st.info(f"✨ İkonik An: {player['moment']}")

# Tahmin Formu
with st.form("guess_form", clear_on_submit=True):
    user_guess = st.text_input("Tahmininiz:").lower().strip()
    c1, c2 = st.columns(2)
    submit = c1.form_submit_button("Tahmin Et")
    pass_btn = c2.form_submit_button("Pas Geç")

if submit:
    correct_name = player['name'].lower()
    if user_guess and (user_guess in correct_name and len(user_guess) > 3):
        play_sound("sounds/goal.mp3")
        image_placeholder.image(raw_img, use_container_width=True, caption=f"TEBRİKLER! {player['name']}")
        st.session_state.total_score += (5 - st.session_state.attempts) * 20 * st.session_state.multiplier
        st.success("DOĞRU!")
        time.sleep(3)
        st.session_state.target_player = None
        st.session_state.current_question += 1
        st.rerun()
    else:
        st.session_state.attempts += 1
        if st.session_state.attempts >= 5:
            play_sound("sounds/whistle.mp3")
            image_placeholder.image(raw_img, use_container_width=True, caption=f"Cevap: {player['name']}")
            st.error(f"HAKKINIZ BİTTİ! Doğru cevap: {player['name']}")
            time.sleep(3)
            st.session_state.target_player = None
            st.session_state.current_question += 1
            st.rerun()
        else:
            st.rerun()

if pass_btn:
    st.session_state.target_player = None
    st.session_state.current_question += 1
    st.rerun()
