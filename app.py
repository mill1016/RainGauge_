import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import matplotlib.pyplot as plt
from datetime import date, timedelta
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import streamlit_js_eval
from streamlit_geolocation import streamlit_geolocation

# --- Page Configuration ---
st.set_page_config(page_title="Local Rain Gauge", layout="centered", page_icon="☔️")
st.title("⛆ Weekly Rainfall Tracker")

# --- Geocode from address ---
geolocator = Nominatim(user_agent="rain_gauge_app_unique")
def geocode_address(address):
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except Exception as e:
        st.warning(f"Geocoding error: {e}")
    return None
    
def reverse_geocode(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), timeout=10)
        if location and location.raw and "address" in location.raw:
            addr = location.raw["address"]
            street = addr.get("house_number", "") + " " + addr.get("road", "")
            city = addr.get("city", "") or addr.get("town", "") or addr.get("village", "")
            state = addr.get("state", "")
            postcode = addr.get("postcode", "")
            return f"{street.strip()}, {city}, {state} {postcode}".strip(", ")
        elif location and location.address:
            return location.address  # fallback
    except Exception as e:
        st.warning(f"Reverse geocoding error: {e}")
    return ""
    
def handle_address_submit():
    address_input = st.session_state["address_input"]
    if address_input:
        geocoded = geocode_address(address_input)
        if geocoded:
            st.session_state["user_lat"], st.session_state["user_lon"] = geocoded
            st.session_state["location_source"] = "address"
            st.session_state["last_address"] = address_input
            st.session_state["last_input_mode"] = "address"
            st.session_state["clear_address_next_run"] = True  # ✅ Clear on next run
            st.rerun()
        else:
            st.error("Could not geocode the provided address. Please try a different one.")
            st.stop()

# --- Location Section with Button and Input ---
#st.subheader("📍 Choose Your Location")

# --- Initialize session state ---
# --- Initialize session state ---
# --- Initialization ---
for key, val in {
    "user_lat": None,
    "user_lon": None,
    "location_source": None,
    "last_input_mode": None,
    "last_address": "",
    "geocode_trigger": "",  # 🔑 trigger for geocoding
    "gps_address": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- GPS Button ---
col1, col2 = st.columns([6.5, 1])

# ----- ADDRESS INPUT -----
with col1:
    default_value = st.session_state["gps_address"] if (
        st.session_state["last_input_mode"] == "gps"
        and st.session_state["last_address"] != st.session_state["gps_address"]
    ) else st.session_state["last_address"]

    address_input = st.text_input(
        label="Enter Address",
        key="address_input",
        value=default_value,
        placeholder="Enter address and press Enter",
        label_visibility="collapsed",
    )

    if address_input:
        # Geocode if:
        # - Address has changed
        # - Input mode is switching from GPS to address
        if (
            address_input != st.session_state["last_address"]
            or st.session_state["last_input_mode"] != "address"
        ):
            geocoded = geocode_address(address_input)
            if geocoded:
                st.session_state["user_lat"], st.session_state["user_lon"] = geocoded
                st.session_state["location_source"] = "address"
                st.session_state["last_input_mode"] = "address"
                st.session_state["last_address"] = address_input
                st.rerun()
            else:
                st.error("Could not geocode the provided address. Please try a different one.")
                st.stop()

# ----- GPS BUTTON -----
with col2:
    gps_coords = streamlit_geolocation()
    if gps_coords and gps_coords.get("latitude") and gps_coords.get("longitude"):
        gps_lat = gps_coords["latitude"]
        gps_lon = gps_coords["longitude"]

        # Reverse geocode GPS location only if needed
        if (
            st.session_state["last_input_mode"] != "gps"
            or gps_lat != st.session_state["user_lat"]
            or gps_lon != st.session_state["user_lon"]
        ):
            gps_address = reverse_geocode(gps_lat, gps_lon)
            if gps_address:
                st.session_state["gps_address"] = gps_address
                st.session_state["user_lat"] = gps_lat
                st.session_state["user_lon"] = gps_lon
                st.session_state["location_source"] = "gps"
                st.session_state["last_input_mode"] = "gps"
                st.rerun()

# --- Geocoding Execution ---
trigger = st.session_state.get("geocode_trigger", "")
if trigger:
    geocoded = geocode_address(trigger)
    if geocoded:
        st.session_state["user_lat"], st.session_state["user_lon"] = geocoded
        st.session_state["location_source"] = "address"
        st.session_state["last_input_mode"] = "address"
        st.session_state["last_address"] = trigger
    else:
        st.error("Could not geocode the provided address. Please try a different one.")
        st.stop()

# Final coordinates
user_lat = st.session_state.get("user_lat")
user_lon = st.session_state.get("user_lon")

if not user_lat or not user_lon:
    st.info("Please enter an address or click 'Use My Location' to continue.")
    st.stop()

# Use updated coordinates
user_lat = st.session_state["user_lat"]
user_lon = st.session_state["user_lon"]
gps_coords = None

# Check for valid coordinates
if not user_lat or not user_lon:
    st.info("Please enter an address or click 'Use My Location' to continue.")
    st.stop()

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
            if dist_miles <= 5.0:
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

@st.cache_data(show_spinner=False)
def get_precip_data(stations):
    #stations = pd.read_json(stations_json)
    BASE_URL = "https://api.weather.com/v2/pws/history/all"
    API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=29)  # ✅ Always 30 days
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
    df = pd.DataFrame(records, columns=["Date", "Avg Precip [in]"])
    df = df.set_index("Date").asfreq("D", fill_value=0).reset_index()
    return df
    
# --- Number of days slider ---
# --- Number of days slider ---
#num_days = st.slider("Number of past days to show", 1, 30, 7)
#st.write("⏳ Slider says:", num_days)
num_days = 7

### Precip Chart
st.subheader("Precipitation Trends")

precip_df_full = get_precip_data(stations)  # still fetches 30 days
#st.write("📅 Full data range:", precip_df_full['Date'].min(), "to", precip_df_full['Date'].max())

# Trim and compute rolling/cumulative
precip_df = precip_df_full.tail(num_days).copy()
#st.write("📊 Subset shape:", precip_df.shape)
#st.write("📊 Subset date range:", precip_df['Date'].min(), "to", precip_df['Date'].max())

# Cumulative sum
cum_col = f'{num_days}-Day Cumulative'
precip_df[cum_col] = precip_df['Avg Precip [in]'].cumsum()

# Plot
fig, ax1 = plt.subplots(figsize=(10, 6))
ax1.bar(precip_df['Date'], precip_df['Avg Precip [in]'], color='skyblue')
ax1.set_ylabel('Daily Precipitation [in]', color='black')
ax1.tick_params(axis='x', rotation=45)
ax1.set_xticks(precip_df['Date'])
ax1.set_xticklabels(precip_df['Date'].dt.strftime('%m-%d'), rotation=45)

ax2 = ax1.twinx()
ax2.plot(precip_df['Date'], precip_df[cum_col], color='darkblue')
ax2.set_ylabel(f'Cumulative Rainfall over {num_days} Days [in]', color='black')

y_max = max(
    precip_df['Avg Precip [in]'].max(),
    precip_df[cum_col].max()
) * 1.1
ax1.set_ylim(0, y_max)
ax2.set_ylim(0, y_max)

fig.suptitle(f'Daily Precipitation and {num_days}-Day Cumulative')
fig.tight_layout()
st.pyplot(fig)

# --- Separator ---
st.markdown("---")

# --- Map Visualization ---
st.subheader("Map of Your Location and Nearby Stations")
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

del num_days
