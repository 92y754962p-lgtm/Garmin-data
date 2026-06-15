import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Performance Monitor", layout="wide")
st.title("Performance Monitor (10% Sensitivity)")

# Mapping: Display Name -> API Key
METRIC_MAP = {
    'Resting Heart Rate': 'restingHeartRate',
    'Average Steps': 'steps',
    'Sleep Score': 'sleepScore',
    'Respiration': 'latestRespirationValue',
    'Stress': 'averageStressLevel',
    'Body Battery': 'bodyBatteryMostRecentValue',
    'VO2 Max': 'vo2MaxValue',
    'Total Calories': 'activeCalories'
}

@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(st.secrets["GARMIN_EMAIL"], st.secrets["GARMIN_PASSWORD"])
    api.login()
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=30)
    
    # SINGLE BATCH FETCH: Much faster and stable
    stats = api.get_stats(start_date.isoformat())
    
    # Convert list of dicts to DataFrame directly
    df = pd.DataFrame(stats)
    df['Date'] = pd.to_datetime(df['calendarDate'])
    return df.set_index('Date')

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("Fetching data..."):
        df = get_data()
        df = df.apply(pd.to_numeric, errors='coerce')
        
        last_7 = df.iloc[:7].mean()
        prev_23 = df.iloc[7:30].mean()
        
        active_shifts = []
        for display_name, api_key in METRIC_MAP.items():
            if api_key in df.columns and pd.notna(last_7[api_key]) and prev_23[api_key] != 0:
                shift = (last_7[api_key] - prev_23[api_key]) / prev_23[api_key]
                if abs(shift) > 0.10:
                    active_shifts.append({
                        "Metric": display_name, 
                        "7-Day": f"{last_7[api_key]:.1f}", 
                        "Prev 23": f"{prev_23[api_key]:.1f}", 
                        "Shift": f"{shift:.2%}"
                    })
        
        if active_shifts:
            st.table(pd.DataFrame(active_shifts).set_index("Metric"))
        else:
            st.success("✅ All primary metrics stable within 10%.")
            
except Exception as e:
    st.error(f"Data Fetch Error: {e}")
