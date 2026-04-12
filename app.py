import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import requests
import pandas as pd

# ================== CONFIG ==================
load_dotenv()

client = OpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1"
)

st.set_page_config(page_title="Travel With Me Pro", layout="wide")

# ================== DARK MODE ==================
dark_mode = st.sidebar.toggle("🌙 Dark Mode")

bg = "#0e1117" if dark_mode else "#f5f7fb"
card = "#1e1e1e" if dark_mode else "white"
text = "white" if dark_mode else "black"

# ================== PREMIUM CSS ==================
st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
    background: {bg};
    color: {text};
}}

.big-title {{
    font-size:48px;
    font-weight:800;
    text-align:center;
    background: linear-gradient(90deg,#00C9FF,#92FE9D);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.subtitle {{
    text-align:center;
    color:gray;
    margin-bottom:30px;
}}

.card {{
    padding:25px;
    border-radius:20px;
    background: {card};
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.2);
    transition: 0.3s;
}}

.card:hover {{
    transform: scale(1.02);
}}

button {{
    border-radius:10px !important;
}}
</style>
""", unsafe_allow_html=True)

# ================== HEADER ==================
st.markdown('<div class="big-title">🌍 Travel With Me ✈️</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-powered smart travel planner</div>', unsafe_allow_html=True)

# ================== SESSION ==================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "saved_trips" not in st.session_state:
    st.session_state.saved_trips = []

# ================== NAV ==================
option = st.sidebar.radio("✨ Navigation", [
    "🏠 Explore",
    "🗺 Map",
    "🗓 Itinerary",
    "💰 Budget",
    "💬 Chat",
    "❤️ Saved"
])

# ================== AI ==================
def generate_response(prompt):
    with st.spinner("✨ Planning your trip..."):
        response = client.chat.completions.create(
            model="meta-llama/llama-3-70b-instruct",
            messages=[
                {"role": "system", "content": "You are a professional travel planner. Give structured, engaging travel advice."},
                {"role": "user", "content": prompt}
            ]
        )
    return response.choices[0].message.content

# ================== GEO ==================
@st.cache_data
def get_location(place):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "travelwithme-app (nikhil@email.com)"  # IMPORTANT
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        print("STATUS:", response.status_code)
        print("TEXT:", response.text[:200])

        if response.status_code != 200:
            return None, None

        data = response.json()

        if not data:
            return None, None

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])

        return lat, lon

    except Exception as e:
        print("ERROR:", e)
        return None, None

# ================== EXPLORE ==================
if option == "🏠 Explore":
    place = st.text_input("🌍 Enter destination")

    col1, col2 = st.columns(2)

    if col1.button("🚀 Explore") and place:
        result = generate_response(f"Travel guide for {place}")
        st.markdown(f'<div class="card">{result}</div>', unsafe_allow_html=True)

        st.image(f"https://source.unsplash.com/1200x500/?{place}", use_container_width=True)

    if col2.button("❤️ Save Trip") and place:
        st.session_state.saved_trips.append(place)
        st.success("Trip saved!")

# ================== MAP ==================
elif option == "🗺 Map":
    st.markdown("### 📍 Interactive Map")

    place = st.text_input("Enter place")

    if st.button("Show Map") and place:
        lat, lon = get_location(place)

        if lat and lon:
            # Google Maps Embed
            map_url = f"https://www.google.com/maps?q={lat},{lon}&output=embed"

            st.components.v1.iframe(map_url, height=500)

            df = pd.DataFrame({"lat": [lat], "lon": [lon]})
            st.map(df, zoom=10)

        else:
            st.error("Location not found")

# ================== ITINERARY ==================
elif option == "🗓 Itinerary":
    place = st.text_input("Destination")
    days = st.slider("Days", 1, 10, 3)

    if st.button("Generate Itinerary") and place:
        result = generate_response(f"{days}-day itinerary for {place}")
        st.markdown(f'<div class="card">{result}</div>', unsafe_allow_html=True)

# ================== BUDGET ==================
elif option == "💰 Budget":
    place = st.text_input("Destination")
    days = st.slider("Days", 1, 15, 5)
    style = st.selectbox("Style", ["Budget", "Mid-range", "Luxury"])

    if st.button("Calculate Budget") and place:
        result = generate_response(f"Estimate cost for {days} days in {place} for a {style} traveler")
        st.markdown(f'<div class="card">{result}</div>', unsafe_allow_html=True)

# ================== CHAT ==================
elif option == "💬 Chat":
    user_input = st.chat_input("Ask anything about travel...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        reply = generate_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# ================== SAVED ==================
elif option == "❤️ Saved":
    st.markdown("### ❤️ Saved Trips")

    if st.session_state.saved_trips:
        for trip in st.session_state.saved_trips:
            st.markdown(f'<div class="card">🌍 {trip}</div>', unsafe_allow_html=True)
    else:
        st.info("No saved trips yet")

# ================== FOOTER ==================
st.markdown("---")


