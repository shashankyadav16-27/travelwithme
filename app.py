import streamlit as st
from openai import OpenAI
import requests
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime

# ================== DATABASE SETUP ==================
def init_db():
    conn = sqlite3.connect("travel.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place TEXT, result TEXT, timestamp TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS itineraries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place TEXT, days INTEGER, content TEXT, timestamp TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place TEXT, days INTEGER, style TEXT,
        total_inr REAL, currency TEXT, converted REAL, timestamp TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT, content TEXT, timestamp TEXT)""")
    conn.commit()
    conn.close()

def save_search(place, result):
    conn = sqlite3.connect("travel.db")
    conn.execute("INSERT INTO searches (place, result, timestamp) VALUES (?, ?, ?)",
                 (place, result, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def save_itinerary(place, days, content):
    conn = sqlite3.connect("travel.db")
    conn.execute("INSERT INTO itineraries (place, days, content, timestamp) VALUES (?, ?, ?, ?)",
                 (place, days, content, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def save_budget(place, days, style, total_inr, currency, converted):
    conn = sqlite3.connect("travel.db")
    conn.execute("INSERT INTO budgets (place, days, style, total_inr, currency, converted, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (place, days, style, total_inr, currency, converted, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def save_chat(role, content):
    conn = sqlite3.connect("travel.db")
    conn.execute("INSERT INTO chats (role, content, timestamp) VALUES (?, ?, ?)",
                 (role, content, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def load_searches():
    conn = sqlite3.connect("travel.db")
    df = pd.read_sql_query("SELECT place, timestamp FROM searches ORDER BY id DESC LIMIT 20", conn)
    conn.close(); return df

def load_itineraries():
    conn = sqlite3.connect("travel.db")
    df = pd.read_sql_query("SELECT place, days, timestamp FROM itineraries ORDER BY id DESC LIMIT 20", conn)
    conn.close(); return df

def load_budgets():
    conn = sqlite3.connect("travel.db")
    df = pd.read_sql_query("SELECT place, days, style, total_inr, currency, converted, timestamp FROM budgets ORDER BY id DESC LIMIT 20", conn)
    conn.close(); return df

def load_chats():
    conn = sqlite3.connect("travel.db")
    rows = conn.execute("SELECT role, content FROM chats ORDER BY id ASC").fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

init_db()

# ================== CONFIG ==================
client = OpenAI(
    api_key=st.secrets["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "travelwithme",
        "X-Title": "travelwithme app"
    }
)


GEOAPIFY_KEY = st.secrets["GEOAPIFY_KEY"]

st.set_page_config(page_title="Travel With Me", layout="wide")

# ================== DARK MODE ==================
dark_mode = st.sidebar.toggle("🌙 Dark Mode")
if dark_mode:
    bg, text, card = "#0e1117", "white", "#161b22"
else:
    bg, text, card = "#f5f7fb", "black", "white"

st.markdown(f"""
<style>
body {{background-color:{bg}; color:{text};}}
.big-title {{font-size:42px; font-weight:800; text-align:center;}}
.subtitle {{text-align:center; color:gray; margin-bottom:20px;}}
.card {{padding:20px; border-radius:20px; background:{card};
        box-shadow:0 6px 20px rgba(0,0,0,0.1); margin-bottom:15px;}}
.poi-card {{padding:14px; border-radius:14px; background:{card};
            box-shadow:0 2px 10px rgba(0,0,0,0.08); margin-bottom:12px;}}
</style>
""", unsafe_allow_html=True)

# ================== HEADER ==================
st.markdown('<div class="big-title">🌍 Travel With Me ✈️</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Plan smarter. Travel better.</div>', unsafe_allow_html=True)

# ================== SESSION ==================
if "messages" not in st.session_state:
    st.session_state.messages = load_chats()

# ================== SIDEBAR ==================
st.sidebar.title("✨ Explore")
option = st.sidebar.radio("Navigation", [
    "🏠 Explore", "🗺 Map", "🗓 Itinerary", "💰 Budget", "💬 Chat", "📂 History"
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

# ================== GEOAPIFY ==================

CATEGORY_MAP = {
    "All Attractions":    "tourism",
    "Food & Drink":       "catering",
    "Museums & Arts":     "entertainment.museum",
    "Outdoors & Nature":  "natural",
    "Hotels":             "accommodation.hotel",
    "Shopping":           "commercial.shopping_mall",
    "Nightlife":          "entertainment.nightclub",
    "Historic Sites":     "tourism.sights.place_of_worship",
    "Parks":              "leisure.park",
}

def geoapify_geocode(place):
    """Convert place name to lat/lon using Geoapify Geocoding API (free)."""
    try:
        url = "https://api.geoapify.com/v1/geocode/search"
        res = requests.get(url, params={"text": place, "apiKey": GEOAPIFY_KEY, "limit": 1}, timeout=8)
        data = res.json()
        features = data.get("features", [])
        if features:
            coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
            return coords[1], coords[0]  # lat, lon
    except:
        pass
    return None, None

def geoapify_places(lat, lon, category="tourism", radius=5000, limit=9):
    """Fetch POIs from Geoapify Places API (free, no credit card)."""
    try:
        url = "https://api.geoapify.com/v2/places"
        params = {
            "categories": category,
            "filter": f"circle:{lon},{lat},{radius}",
            "limit": limit,
            "apiKey": GEOAPIFY_KEY,
            "lang": "en"
        }
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json().get("features", [])
        st.warning(f"Geoapify error {res.status_code}")
        return []
    except Exception as e:
        st.warning(f"Geoapify failed: {e}")
        return []

def show_pois(place, category="tourism", label="🏛 Top Attractions"):
    lat, lon = geoapify_geocode(place)
    if not lat:
        st.warning("Could not locate this destination.")
        return

    features = geoapify_places(lat, lon, category=category)
    if not features:
        st.info("No places found for this destination/category.")
        return

    st.markdown(f"### {label} near {place.title()}")
    cols = st.columns(3)

    for i, feat in enumerate(features):
        props   = feat.get("properties", {})
        name    = props.get("name") or props.get("address_line1", "Unnamed Place")
        address = props.get("formatted", "")
        cats    = props.get("categories", [])
        cat_str = " · ".join(cats[:2]).replace(".", " › ").title() if cats else ""
        dist    = props.get("distance", "")
        dist_str = f"📍 {dist}m away" if dist else ""
        wiki    = props.get("wiki_and_media", {})
        img_url = wiki.get("image", "") if isinstance(wiki, dict) else ""

        with cols[i % 3]:
            img_html = f'<img src="{img_url}" width="100%" style="border-radius:8px;margin-bottom:6px;max-height:140px;object-fit:cover">' if img_url else ""
            st.markdown(f"""
            <div class="poi-card">
                {img_html}
                <b>{name}</b><br>
                <small style="color:#888">{cat_str}</small><br>
                <small>{address[:60]}{"..." if len(address)>60 else ""}</small><br>
                <small style="color:#aaa">{dist_str}</small>
            </div>
            """, unsafe_allow_html=True)

# ================== CURRENCY ==================
def convert_currency(amount, from_currency="INR", to_currency="USD"):
    try:
        res = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}", timeout=5)
        rate = res.json()["rates"].get(to_currency)
        return amount * rate if rate else None
    except:
        return None

# ================== WEATHER ==================
def get_weather(place):
    try:
        res = requests.get("https://api.openweathermap.org/data/2.5/weather",
                           params={"q": place, "appid": "0c6aea14cd570a572317825ddf3665ff", "units": "metric"},
                           timeout=5)
        data = res.json()
        if res.status_code != 200:
            return None
        return {
            "temp":     data["main"]["temp"],
            "feels":    data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "desc":     data["weather"][0]["description"].title()
        }
    except:
        return None

# ================== EXPLORE ==================
if option == "🏠 Explore":
    place    = st.text_input("Enter destination")
    cat_name = st.selectbox("🎯 Filter attractions by type", list(CATEGORY_MAP.keys()))
    cat_id   = CATEGORY_MAP[cat_name]

    if st.button("Explore", key="explore_btn") and place:
        result = generate_response(f"Travel guide for {place}")
        st.markdown(f'<div class="card">{result}</div>', unsafe_allow_html=True)
        save_search(place, result)
        st.image(f"https://source.unsplash.com/900x400/?{place},travel")

        weather = get_weather(place)
        if weather:
            st.markdown("### 🌦 Current Weather")
            c1, c2, c3 = st.columns(3)
            c1.metric("🌡 Temp",     f"{weather['temp']}°C")
            c2.metric("🤒 Feels",    f"{weather['feels']}°C")
            c3.metric("💧 Humidity", f"{weather['humidity']}%")
            st.info(weather["desc"])

        show_pois(place, category=cat_id, label=f"🏛 {cat_name}")

# ================== MAP ==================
elif option == "🗺 Map":
    place = st.text_input("Enter place")
    if st.button("Show Map", key="map_btn") and place:
        lat, lon = geoapify_geocode(place)
        if lat and lon:
            st.map({"lat": [lat], "lon": [lon]})
            features = geoapify_places(lat, lon, limit=15)
            rows = []
            for f in features:
                coords = f.get("geometry", {}).get("coordinates", [])
                name   = f.get("properties", {}).get("name", "?")
                if len(coords) == 2:
                    rows.append({"lat": coords[1], "lon": coords[0], "name": name})
            if rows:
                poi_df = pd.DataFrame(rows)
                st.markdown("#### 📍 Nearby Attractions")
                st.map(poi_df[["lat", "lon"]])
                st.dataframe(poi_df[["name", "lat", "lon"]], use_container_width=True)
        else:
            st.error("Location not found")

# ================== ITINERARY ==================
elif option == "🗓 Itinerary":
    place = st.text_input("Destination")
    days  = st.slider("Days", 1, 10, 3)
    if st.button("Generate", key="itinerary_btn"):
        if not place:
            st.warning("Please enter a destination")
        else:
            with st.spinner("Generating itinerary..."):
                result = generate_response(
                    f"{days} day detailed itinerary for {place} with morning, afternoon and evening plans")
                st.markdown(f'<div class="card">{result}</div>', unsafe_allow_html=True)
                save_itinerary(place, days, result)
                st.success("✅ Itinerary saved to history!")
            show_pois(place, label="📍 Places to Visit")

# ================== BUDGET ==================
elif option == "💰 Budget":
    place    = st.text_input("Destination")
    days     = st.slider("Days", 1, 15, 5)
    style    = st.selectbox("Style", ["Budget", "Mid-range", "Luxury"])
    currency = st.selectbox("💱 Convert to", ["INR", "USD", "EUR", "GBP", "AED", "SGD"])

    if st.button("Calculate Cost", key="budget_btn") and place:
        multiplier = 1.5
        if "goa"   in place.lower(): multiplier = 1
        elif "paris" in place.lower(): multiplier = 3

        if style == "Budget":
            stay, food, transport, activities = 1000, 500, 300, 400
        elif style == "Mid-range":
            stay, food, transport, activities = 3000, 1200, 800, 1000
        else:
            stay, food, transport, activities = 8000, 3000, 2000, 3000

        data = {
            "Stay":       stay       * days * multiplier,
            "Food":       food       * days * multiplier,
            "Transport":  transport  * days * multiplier,
            "Activities": activities * days * multiplier,
        }
        data["Total"] = sum(data.values())

        c1, c2, c3 = st.columns(3)
        c1.metric("Stay",      f"₹{int(data['Stay'])}")
        c2.metric("Food",      f"₹{int(data['Food'])}")
        c3.metric("Transport", f"₹{int(data['Transport'])}")
        st.metric("Total",     f"₹{int(data['Total'])}")

        df = pd.DataFrame({
            "Category": list(data.keys())[:-1],
            "Cost":     list(data.values())[:-1]
        }).set_index("Category")
        st.bar_chart(df)
        fig = px.pie(df, values="Cost", names=df.index, title="Budget Breakdown")
        st.plotly_chart(fig)

        converted = convert_currency(data["Total"], "INR", currency)
        if converted:
            st.success(f"💱 {currency}: {round(converted, 2)}")

        save_budget(place, days, style, data["Total"], currency, converted or 0)
        st.success("✅ Budget saved to history!")

# ================== CHAT ==================
elif option == "💬 Chat":
    user_input = st.chat_input("Ask anything about travel...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_chat("user", user_input)
        reply = generate_response(user_input)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        save_chat("assistant", reply)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# ================== HISTORY ==================
elif option == "📂 History":
    st.markdown("## 📂 Your Saved History")
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Searches", "🗓 Itineraries", "💰 Budgets", "💬 Chats"])

    with tab1:
        df = load_searches()
        st.dataframe(df, use_container_width=True) if not df.empty else st.info("No searches yet.")

    with tab2:
        df = load_itineraries()
        st.dataframe(df, use_container_width=True) if not df.empty else st.info("No itineraries yet.")

    with tab3:
        df = load_budgets()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            if len(df) > 1:
                fig = px.bar(df, x="place", y="total_inr", color="style",
                             title="💰 Budget History by Destination")
                st.plotly_chart(fig)
        else:
            st.info("No budgets yet.")

    with tab4:
        chats = load_chats()
        if chats:
            for msg in chats[-30:]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
        else:
            st.info("No chat history yet.")

# ================== FOOTER ==================
st.markdown("---")
st.caption("🚀 Travel With Me | Powered by Geoapify · OpenWeather · OpenRouter | Powered by Geoapify")
