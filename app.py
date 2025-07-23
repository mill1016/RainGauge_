import streamlit as st
from streamlit_geolocation import streamlit_geolocation

st.title("Geolocation Example")

location_data = streamlit_geolocation()

if location_data:
   st.write(f"Latitude: {location_data['latitude']}")
   st.write(f"Longitude: {location_data['longitude']}")
else:
   st.write("No location info yet. Click the button to get location.")

if st.button("Get Location"):
   if location_data:
       st.write(f"Latitude: {location_data['latitude']}")
       st.write(f"Longitude: {location_data['longitude']}")
   else:
       st.write("Location data is still being fetched. Please wait and try again.")