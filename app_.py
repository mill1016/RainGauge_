import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import matplotlib.pyplot as plt
from datetime import date, timedelta
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import streamlit_js_eval

# --- Page Configuration ---
st.set_page_config(page_title="Local Rain Gauge", layout="centered", page_icon="☔️")
st.title("💧 Local Rainfall Tracker")

# --- Geocode from address ---
geolocator = Nominatim(user_agent="rain_gauge_app")
def geocode_address(address):
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except Exception as e:
        st.warning(f"Geocoding error: {e}")
    return None

# --- Location Section with Button ---
st.subheader("📍 Choose Your Location")

user_lat = None
user_lon = None

# Create button
use_location = st.button("🌏 Use Current Location")

if use_location:
    coords = streamlit_js_eval.get_geolocation()
else:
    coords = None

# Get coordinates from browser if allowed
if coords and coords.get("latitude") and coords.get("longitude"):
    user_lat = coords["latitude"]
    user_lon = coords["longitude"]
    st.success(f"Detected location: ({user_lat:.4f}, {user_lon:.4f})")

# If no location, fall back to manual input
if not user_lat or not user_lon:
    st.warning("Could not detect location automatically. Please allow access or enter your location manually.")
    user_input = st.text_input("Enter your city or address:")
    if user_input:
        geocoded = geocode_address(user_input)
        if geocoded:
            user_lat, user_lon = geocoded
            st.success(f"Location set to: ({user_lat:.4f}, {user_lon:.4f})")
        else:
            st.error("Could not geocode the provided address. Please try a different one.")
            st.stop()
    else:
        st.info("Waiting for location input...")
        st.stop()

# --- Number of days slider ---
num_days = st.slider("Number of past days to show", 1, 30, 7)

# --- Get Weather Underground PWS stations ---
def get_nearby_pws(lat, lon):
    API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
    url = f"https://api.weather.com/v3/location/near?geocode={lat},{lon}&product=pws&format=json&apiKey={API_KEY}"
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        stations = []
        for i in range(len(data['location']['stationId'])):
            station_lat = data['location']['latitude'][i]
            station_lon = data['location']['longitude'][i]
            dist_miles = geodesic((lat, lon), (station_lat, station_lon)).miles
            if dist_miles <= 1.0:
                stations.append({
                    'stationId': data['location']['stationId'][i],
                    'name': f"Station {i}",
                    'lat': station_lat,
                    'lon': station_lon,
                    'distance': dist_miles
                })
        stations_df = pd.DataFrame(stations)
        if not stations_df.empty:
            stations_df = stations_df.sort_values(by='distance').head(5)
        return stations_df
    except Exception as e:
        st.error(f"Error fetching weather stations: {e}")
        return pd.DataFrame()

stations = get_nearby_pws(user_lat, user_lon)

if stations.empty:
    st.warning("No weather stations found within 1 mile of your location.")
    st.stop()

# --- Precipitation Data ---
st.subheader("📊 Precipitation Trends")
end_date = date.today() - timedelta(days=1)
start_date = end_date - timedelta(days=num_days - 1)

@st.cache_data(show_spinner=False)
def get_precip_data(stations):
    BASE_URL = "https://api.weather.com/v2/pws/history/all"
    API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=29)
    records = []

    for day in pd.date_range(start_date, end_date):
        date_str = day.strftime("%Y%m%d")
        values = []
        for _, row in stations.iterrows():
            params = {
                "stationId": row['stationId'],
                "date": date_str,
                "format": "json",
                "units": "e",
                "apiKey": API_KEY
            }
            try:
                r = requests.get(BASE_URL, params=params)
                r.raise_for_status()

                if not r.content:
                    continue

                try:
                    data = r.json()
                except ValueError as ve:
                    st.warning(f"Invalid JSON for {row['stationId']} on {date_str}: {ve}")
                    continue
                observations = data.get("observations", [])
                if not observations:
                    continue
                precip_values = [
                    obs["imperial"].get("precipTotal")
                    for obs in observations
                    if "imperial" in obs and obs["imperial"].get("precipTotal") is not None
                ]
                if precip_values:
                    values.append(max(precip_values))
            except Exception as e:
                st.error(f"Error fetching data for {row['stationId']} on {date_str}: {e}")
                continue
        avg_precip = sum(values) / len(values) if values else 0.0
        records.append((day, avg_precip))
    return pd.DataFrame(records, columns=["Date", "Avg Precip [in]"])

precip_df_full = get_precip_data(stations)
precip_df = precip_df_full.tail(num_days).copy()
precip_df['7-Day Cumulative'] = precip_df['Avg Precip [in]'].rolling(7, min_periods=1).sum()

# --- Plot Precip Trends ---
fig, ax1 = plt.subplots(figsize=(10, 6))
ax1.bar(precip_df['Date'], precip_df['Avg Precip [in]'], color='skyblue', label='Daily Precipitation')
ax1.set_ylabel('Daily Precipitation [in]', color='black')
ax1.tick_params(axis='y', labelcolor='black')
ax1.tick_params(axis='x', rotation=45)
ax1.set_xticks(precip_df['Date'])
ax1.set_xticklabels(pd.to_datetime(precip_df['Date']).dt.strftime('%a\n%m-%d'))

ax2 = ax1.twinx()
ax2.plot(precip_df['Date'], precip_df['7-Day Cumulative'], color='darkblue', label='7-Day Cumulative')
ax2.set_ylabel('7-Day Cumulative Total [in]', color='black')
ax2.tick_params(axis='y', labelcolor='black')

y_min = 0
y_max = max(precip_df['Avg Precip [in]'].max(), precip_df['7-Day Cumulative'].max()) * 1.1
ax1.set_ylim(y_min, y_max)
ax2.set_ylim(y_min, y_max)

fig.suptitle('Average Daily Precipitation and 7-Day Cumulative')
fig.tight_layout()
st.pyplot(fig)

# --- Separator ---
st.markdown("---")

# --- Map Visualization ---
st.subheader("🌐 Map of Your Location and Nearby Stations")
map_data = pd.DataFrame({
    'lat': [user_lat] + stations['lat'].tolist(),
    'lon': [user_lon] + stations['lon'].tolist(),
    'label': ['You'] + stations['name'].tolist(),
    'color': [[0, 0, 255]] + [[255, 0, 0]] * len(stations)
})

layer = pdk.Layer(
    'ScatterplotLayer',
    data=map_data,
    get_position='[lon, lat]',
    get_color='color',
    get_radius=25,
    pickable=True
)

view_state = pdk.ViewState(latitude=user_lat, longitude=user_lon, zoom=14, pitch=0)

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={"text": "{label}"}
))
