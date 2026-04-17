import streamlit as st
from openai import OpenAI
import requests
import pandas as pd
import json
import re
import plotly.express as px

# ================== CURRENCY ==================
def convert_currency(amount, from_currency="INR", to_currency="USD"):
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = requests.get(url, timeout=5)
        data = response.json()

        rate = data["rates"].get(to_currency)
        if rate:
            return amount * rate
        return None
    except:
        return None

# ================== CONFIG ==================

from openai import OpenAI
import streamlit as st

client = OpenAI(
    api_key=st.secrets["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "travelwithme",
        "X-Title": "travelwithme app"
    }
)

st.set_page_config(page_title="Travel With Me Pro", layout="wide")

# ================== DARK MODE ==================
dark_mode = st.sidebar.toggle("🌙 Dark Mode")

if dark_mode:
    bg = "#0e1117"
    text = "white"
    card = "#161b22"
else:
    bg = "#f5f7fb"
    text = "black"
    card = "white"

st.markdown(f"""
<style>
body {{background-color: {bg}; color: {text};}}
.big-title {{font-size:42px; font-weight:800; text-align:center;}}
.subtitle {{text-align:center; color:gray; margin-bottom:20px;}}
.card {{
    padding:20px;
    border-radius:20px;
    background:{card};
    box-shadow:0 6px 20px rgba(0,0,0,0.1);
    margin-bottom:15px;
}}
</style>
""", unsafe_allow_html=True)

# ================== HEADER ==================
st.markdown('<div class="big-title">🌍 Travel With Me Pro ✈️</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Plan smarter. Travel better.</div>', unsafe_allow_html=True)

# ================== SESSION ==================
if "messages" not in st.session_state:
    st.session_state.messages = []

# ================== SIDEBAR ==================
st.sidebar.title("✨ Explore")
option = st.sidebar.radio("Navigation", [
    "🏠 Explore",
    "🗺 Map",
    "🗓 Itinerary",
    "💰 Budget",
    "💬 Chat"
])

# ================== AI ==================
def generate_response(prompt):
    try:
        with st.spinner("✨ Thinking..."):
            response = client.chat.completions.create(
                model="meta-llama/llama-3-70b-instruct",
                messages=[{"role": "user", "content": prompt}]
            )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI Error: {e}"

# ================== LOCATION ==================
def get_location(place):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": place, "format": "json"}
        headers = {"User-Agent": "travel-app"}

        res = requests.get(url, params=params, headers=headers, timeout=10)
        data = res.json()

        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        pass

    return None, None

# ================== WEATHER ==================
def get_weather(place):
    API_KEY = "0c6aea14cd570a572317825ddf3665ff"

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": place, "appid": API_KEY, "units": "metric"}

        res = requests.get(url, params=params, timeout=5)
        data = res.json()

        if res.status_code != 200:
            return None

        return {
            "temp": data["main"]["temp"],
            "feels": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "desc": data["weather"][0]["description"].title()
        }
    except:
        return None

# ================== EXPLORE ==================
if option == "🏠 Explore":
    place = st.text_input("Enter destination")

    if st.button("Explore", key="explore_btn") and place:
        result = generate_response(f"Travel guide for {place}")
        st.markdown(f'<div class="card">{result}</div>', unsafe_allow_html=True)
        st.image(f"https://source.unsplash.com/900x400/?{place}")

        weather = get_weather(place)

        if weather:
            st.markdown("### 🌦 Current Weather")
            col1, col2, col3 = st.columns(3)
            col1.metric("🌡 Temp", f"{weather['temp']}°C")
            col2.metric("🤒 Feels", f"{weather['feels']}°C")
            col3.metric("💧 Humidity", f"{weather['humidity']}%")
            st.info(weather["desc"])

# ================== MAP ==================
elif option == "🗺 Map":
    place = st.text_input("Enter place")

    if st.button("Show Map", key="map_btn") and place:
        lat, lon = get_location(place)
        if lat and lon:
            st.map({"lat": [lat], "lon": [lon]})
        else:
            st.error("Location not found")

# ================== ITINERARY ==================
elif option == "🗓 Itinerary":
    place = st.text_input("Destination")
    days = st.slider("Days", 1, 10, 3)

    if st.button("Generate", key="itinerary_btn"):
        if not place:
            st.warning("Please enter a destination")
        else:
            with st.spinner("Generating itinerary..."):
                result = generate_response(f"{days} day itinerary for {place}")
                st.markdown(f'<div class="card">{result}</div>', unsafe_allow_html=True)
# ================== BUDGET ==================
elif option == "💰 Budget":
    place = st.text_input("Destination")
    days = st.slider("Days", 1, 15, 5)
    style = st.selectbox("Style", ["Budget","Mid-range","Luxury"])
    currency = st.selectbox("💱 Convert to currency", ["INR", "USD", "EUR"])

    if st.button("Calculate Cost", key="budget_btn") and place:

        multiplier = 1.5
        if "goa" in place.lower():
            multiplier = 1
        elif "paris" in place.lower():
            multiplier = 3

        if style == "Budget":
            stay, food, transport, activities = 1000, 500, 300, 400
        elif style == "Mid-range":
            stay, food, transport, activities = 3000, 1200, 800, 1000
        else:
            stay, food, transport, activities = 8000, 3000, 2000, 3000

        data = {
            "Stay": stay * days * multiplier,
            "Food": food * days * multiplier,
            "Transport": transport * days * multiplier,
            "Activities": activities * days * multiplier
        }
        data["Total"] = sum(data.values())

        col1, col2, col3 = st.columns(3)
        col1.metric("Stay", f"₹{int(data['Stay'])}")
        col2.metric("Food", f"₹{int(data['Food'])}")
        col3.metric("Transport", f"₹{int(data['Transport'])}")

        st.metric("Total", f"₹{int(data['Total'])}")

        df = pd.DataFrame({
            "Category": list(data.keys())[:-1],
            "Cost": list(data.values())[:-1]
        }).set_index("Category")

        st.bar_chart(df)

        fig = px.pie(df, values="Cost", names=df.index)
        st.plotly_chart(fig)

        converted = convert_currency(data["Total"], "INR", currency)
        if converted:
            st.success(f"{currency}: {round(converted, 2)}")

# ================== CHAT ==================
elif option == "💬 Chat":
    user_input = st.chat_input("Ask anything...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        reply = generate_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# ================== FOOTER ==================
st.markdown("---")
st.caption("🚀 Travel With Me Pro")