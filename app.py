import streamlit as st
from streamlit_js_eval import streamlit_js_eval

# Page setup
st.set_page_config(page_title="Geolocation Test", page_icon="📍", layout="centered")
st.title("📍 Test Geolocation Access")

# Button to request location
use_location = st.button("📍 Use Current Location")

# Request geolocation if button is clicked
if use_location:
    coords = streamlit_js_eval(js_expressions="getGeolocation()", key="get_location")
else:
    coords = None

# Display results
if coords and coords.get("latitude") and coords.get("longitude"):
    st.success(f"Location: ({coords['latitude']:.5f}, {coords['longitude']:.5f})")
else:
    st.info("Click the button to retrieve your current location.")
