import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Performance Monitor", layout="wide")
st.title("Performance Monitor (10% Sensitivity)")

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
    
    # Fetch batch data
    stats = api.get_stats(start_date.isoformat())
    
    # CRITICAL FIX: Normalize into a flat list of dicts first
    clean_data = []
    for day_stats in stats:
        # Flatten the dictionary so it has no nested structures
        row = {
            'Date': day_stats.get('calendarDate'),
            'restingHeartRate': day_stats.get('restingHeartRate'),
            'steps': day_stats.get('totalSteps'),
            'sleepScore': day_stats.get('sleepScore'),
            'latestRespirationValue': day_stats.get('latestRespirationValue'),
            'averageStressLevel': day_stats.get('averageStressLevel'),
            'bodyBatteryMostRecentValue': day_stats.get('bodyBatteryMostRecentValue'),
            'vo2MaxValue': day_stats.get('vo2MaxValue'),
            'activeCalories': day_stats.get('activeKilocalories')
        }
        clean_data.append(row)
        
    df = pd.DataFrame(clean_data)
    df['Date'] = pd.to_datetime(df['Date'])
    return df.set_index('Date').sort_index(ascending=False)

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("Processing..."):
        df = get_data().apply(pd.to_numeric, errors='coerce')
        
        last_7 = df.iloc[:7].mean()
        prev_23 = df.iloc[7:30].mean()
        
        active_shifts = []
        for display_name, api_key in METRIC_MAP.items():
            if api_key in df.columns and pd.notna(last_7[api_key]) and prev_23[api_key] != 0:
                shift = (last_7[api_key] - prev_23[api_key]) / prev_23[api_key]
                if abs(shift) > 0.10: # 10% Sensitivity
                    active_shifts.append({
                        "Metric": display_name, 
                        "7-Day": f"{last_7[api_key]:.1f}", 
                        "Prev 23": f"{prev_23[api_key]:.1f}", 
                        "Shift": f"{shift:.2%}"
                    })
        
        if active_shifts:
            st.subheader("⚠️ Detected Shifts (>10%)")
            st.table(pd.DataFrame(active_shifts).set_index("Metric"))
        else:
            st.success("✅ All primary metrics stable within 10%.")
            
except Exception as e:
    st.error(f"Data Processing Error: {e}")
