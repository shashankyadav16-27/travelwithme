import streamlit as st

st.title("Travel With Me ✈️")

place = st.text_input("Enter destination:")

if place:
    st.write("Planning trip to", place)