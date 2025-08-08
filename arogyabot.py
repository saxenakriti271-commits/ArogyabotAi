# --- ArogyaBot: Full Version with Audio, Language Toggle, Profile & Doctor Finder ---

import streamlit as st
import pandas as pd
import requests
import geocoder
from groq import Groq
from gtts import gTTS
import os
import base64
from io import BytesIO
import speech_recognition as sr
import hashlib

# --- API KEYS ---
GROQ_API_KEY = "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"
WEATHER_API_KEY = "1042b9678ab6040423bb4f792e3d4ef6"
GOOGLE_MAPS_API_KEY = "AIzaSyAWDpyX1nouw4fA8ChkkNO5wol1GsxjgY8"

# --- UI Config ---
st.set_page_config(page_title="ArogyaBot", layout="wide")
st.title("ArogyaBot - Your AI Health Companion")

# --- Chat History & Reset ---
if "users" not in st.session_state:
    st.session_state.users = {}
if "active_user" not in st.session_state:
    st.session_state.active_user = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "username_val" not in st.session_state:
    st.session_state.username_val = ""
if "password_val" not in st.session_state:
    st.session_state.password_val = ""
if "user_input_text" not in st.session_state:
    st.session_state.user_input_text = ""
if "age" not in st.session_state:
    st.session_state.age = 0
if "gender" not in st.session_state:
    st.session_state.gender = "Female"
if "location" not in st.session_state:
    st.session_state.location = ""
if "language_select" not in st.session_state:
    st.session_state.language_select = "English"

# --- Hashing Function ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Sidebar: Chat History ---
with st.sidebar:
    st.header("Chat History")
    if st.session_state.logged_in:
        history = st.session_state.users[st.session_state.active_user]['history']
        for i, (q, _) in enumerate(history):
            with st.expander(f"{st.session_state.active_user} - Chat {i+1}"):
                pw_attempt = st.text_input(f"Enter password for chat {i+1}", type="password", key=f"pw_{i}")
                if hash_password(pw_attempt) == st.session_state.users[st.session_state.active_user]['password']:
                    st.write(f"**You:** {q}")
                    st.write(f"**ArogyaBot:** {st.session_state.users[st.session_state.active_user]['history'][i][1]}")

# --- Login or Register ---
with st.expander("🔐 Login / Register"):
    username_input = st.text_input("Enter your name", key="username")
    password_input = st.text_input("Enter a password", type="password", key="password")
    if st.button("Login/Register"):
        if username_input:
            hashed_pw = hash_password(password_input)
            if username_input in st.session_state.users:
                if st.session_state.users[username_input]['password'] == hashed_pw:
                    st.success("Welcome back, " + username_input + "!")
                    st.session_state.active_user = username_input
                    st.session_state.logged_in = True
                else:
                    st.error("Incorrect password.")
            else:
                st.session_state.users[username_input] = {"password": hashed_pw, "history": []}
                st.success("User registered successfully.")
                st.session_state.active_user = username_input
                st.session_state.logged_in = True
        else:
            st.error("Please enter a valid name.")

# --- Start New Chat ---
if st.session_state.active_user and st.session_state.logged_in:
    if st.button("🧹 Start New Chat"):
        user = st.session_state.active_user
        preserved_users = st.session_state.users
        password = preserved_users[user]['password']
        history = preserved_users[user]['history']
        st.session_state.clear()
        st.session_state.users = preserved_users
        st.session_state.users[user]['password'] = password
        st.session_state.users[user]['history'] = history
        st.session_state.active_user = user
        st.session_state.logged_in = True
        st.session_state.language_select = "English"
        st.session_state.user_input_text = ""
        st.session_state.age = 0
        st.session_state.gender = "Female"
        st.session_state.location = ""

    language = st.selectbox("Choose language / भाषा चुनें:", ["English", "Hindi", "Marwari"], key="language_select")
    user_input = st.text_input("Describe your symptoms:", key="user_input_text")
    uploaded_audio = st.file_uploader("Or upload audio:", type=["wav", "mp3", "m4a"])
    if uploaded_audio:
        recognizer = sr.Recognizer()
        with sr.AudioFile(uploaded_audio) as source:
            audio = recognizer.record(source)
        try:
            st.session_state.user_input_text = recognizer.recognize_google(audio, language="hi-IN")
            st.success("Transcribed Audio: " + st.session_state.user_input_text)
        except:
            st.error("Could not recognize speech.")

    st.file_uploader("(Optional) Upload symptom image:", type=['png', 'jpg', 'jpeg'])

    with st.expander("User Profile"):
        st.number_input("Age", min_value=0, max_value=120, key="age")
        st.selectbox("Gender", ["Female", "Male", "Other"], key="gender")
        st.text_input("City or Village", key="location")

    data = [
        ["Common Cold", "cough,runny nose,sneezing", "cold", "Drink warm fluids, rest, and use steam inhalation"],
        ["Heatstroke", "headache,dizziness", "hot", "Move to a cooler place, hydrate with electrolytes"],
        ["Dengue", "fever,body pain,mosquito bites", "", "Avoid mosquito bites, consult a doctor"],
        ["Flu", "fever,cough,body ache", "cold", "Stay in bed, drink fluids, and monitor symptoms"],
        ["Allergy", "sneezing,itchy eyes", "dry", "Use antihistamines and avoid allergens"]
    ]
    df = pd.DataFrame(data, columns=["disease", "symptoms", "weather_trigger", "advice"])
    df.to_csv("disease_db.csv", index=False)

    def get_weather():
        g = geocoder.ip('me')
        latlng = g.latlng
        if not latlng:
            return None, None, ""
        lat, lon = latlng
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url).json()
        try:
            return lat, lon, res['weather'][0]['description']
        except:
            return lat, lon, ""

    def find_doctors(lat, lon):
        maps_url = f"https://www.google.com/maps/search/doctors/@{lat},{lon},14z"
        return maps_url

    def rule_based_diagnosis(user_input, weather_desc):
        df = pd.read_csv("disease_db.csv", dtype=str)
        df.fillna("", inplace=True)
        matches = []
        for _, row in df.iterrows():
            symptoms = row['symptoms'].lower().split(',')
            if any(sym in user_input.lower() for sym in symptoms):
                if row['weather_trigger'].lower() in weather_desc.lower() or row['weather_trigger'] == "":
                    matches.append((row['disease'], row['advice']))
        return matches

    def ai_diagnosis(user_input, age, gender, location, weather_desc, language):
        client = Groq(api_key=GROQ_API_KEY)

        if language == "Marwari":
            prompt = (
                f"यूजर (उम्र {age}, लिंग {gender}, स्थान {location}) कह रियो है: {user_input}। मौसम: {weather_desc}। "
                "डॉक्टर साहब, पूरा जवाब केवल शुद्ध मारवाड़ी भाषा में देवनागरी लिपि में दो। अंग्रेज़ी या हिंदी बिलकुल मत लिखो।"
            )
        elif language == "Hindi":
            prompt = f"उपयोगकर्ता (उम्र {age}, लिंग {gender}, स्थान {location}) कह रहा है: {user_input}. मौसम: {weather_desc}. कृपया हिंदी में मेडिकल सलाह दें।"
        else:
            prompt = f"User (age {age}, gender {gender}, location {location}) reports: {user_input}. Weather: {weather_desc}. Provide medical advice in English."

        chat = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return chat.choices[0].message.content

    def speak_text(text):
        tts = gTTS(text=text, lang='hi')
        b = BytesIO()
        tts.write_to_fp(b)
        audio_bytes = b.getvalue()
        st.audio(audio_bytes, format='audio/mp3')

    if st.button("Diagnose") and st.session_state.user_input_text:
        lat, lon, weather = get_weather()
        if not weather:
            st.warning("Could not fetch weather data.")
        else:
            st.success(f"Weather: {weather}")

        rule_matches = rule_based_diagnosis(st.session_state.user_input_text, weather)
        if rule_matches:
            st.subheader("📘 Rule-Based Suggestions")
            for disease, advice in rule_matches:
                st.markdown(f"**{disease}**: {advice}")

        with st.spinner("Consulting AI doctor..."):
            ai_reply = ai_diagnosis(
                st.session_state.user_input_text,
                st.session_state.age,
                st.session_state.gender,
                st.session_state.location,
                weather,
                st.session_state.language_select
            )
            st.session_state.users[st.session_state.active_user]['history'].append((st.session_state.user_input_text, ai_reply))

            st.subheader("🧠 AI Doctor Advice")
            if st.session_state.language_select == "Marwari":
                st.markdown(f"<div style='font-size: 18px;'>{ai_reply}</div>", unsafe_allow_html=True)
                speak_text(ai_reply.split("Translation:")[0])
            else:
                st.markdown(ai_reply)
                speak_text(ai_reply)

        if lat and lon:
            doc_url = find_doctors(lat, lon)
            st.markdown(f"[Find Nearby Doctors]({doc_url})")

    if st.session_state.logged_in:
        history = st.session_state.users[st.session_state.active_user]['history']
        if history:
            st.markdown("---")
            st.subheader(f"Previous Conversations for {st.session_state.active_user}")
            for i, (question, answer) in enumerate(reversed(history)):
                st.markdown(f"**You:** {question}")
                st.markdown(f"**ArogyaBot:** {answer}")
                st.markdown("---")
else:
    st.warning("Please log in to use ArogyaBot.")

# --- Footer ---
st.markdown("---")
st.caption("ArogyaBot: For preliminary support only. Always consult a certified doctor.")
