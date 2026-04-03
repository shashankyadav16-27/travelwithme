import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("AIzaSyCPLl991RIiVkvs7EzIxUpBW4l4oNnv8h4"))

# ✅ FIXED MODEL
model = genai.GenerativeModel("gemini-flash-latest")

st.title("🌍 Travel With Me ✈️")

user_input = st.text_input("Ask about travel:")

if user_input:
    try:
        response = model.generate_content(user_input)
        st.write(response.text)
    except Exception as e:
        st.error(f"Error: {e}")