# Optional Streamlit demo app
import streamlit as st
import pandas as pd

from apputil import Genius

st.set_page_config(page_title="Genius Artist Lookup", layout="centered")
st.title("Genius Artist Lookup (Week 6)")

token = st.text_input("Paste your Genius access token", type="password")
names = st.text_input("Artists (comma-separated)", value="Rihanna, Tycho, Seal, U2")

if st.button("Lookup") and token and names.strip():
    g = Genius(access_token=token)
    terms = [n.strip() for n in names.split(",") if n.strip()]
    df: pd.DataFrame = g.get_artists(terms)
    st.dataframe(df)
    st.caption("Tip: store a small sample response in data/genius_search_sample.json for offline testing.")