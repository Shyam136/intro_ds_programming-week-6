# Minimal Streamlit harness to try the class interactively (optional).
import os
import streamlit as st
from apputil import Genius

st.set_page_config(page_title="Week 6 • Genius API Demo", layout="centered")
st.title("Genius Artist Lookup (Week 6)")

token = st.text_input(
    "Genius Access Token (optional if you use local fallback)",
    type="password",
    value=os.getenv("GENIUS_ACCESS_TOKEN", ""),
)

search = st.text_input("Search for an artist", value="Radiohead")
if st.button("Get artist"):
    g = Genius(access_token=token or None)
    artist = g.get_artist(search)
    if artist:
        st.success(f"Matched: {artist.get('name')} (id={artist.get('id')})")
        st.json(artist)
    else:
        st.warning("No result found.")

st.divider()
terms = st.text_area("Batch search (one per line)", "Rihanna\nTycho\nSeal\nU2").splitlines()
if st.button("Get artists list"):
    g = Genius(access_token=token or None)
    df = g.get_artists([t for t in terms if t.strip()])
    st.dataframe(df)