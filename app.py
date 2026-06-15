import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Performance Monitor", layout="wide")
st.title("Performance Monitor (Custom Health View)")

# Mapping: Display Name -> API Key
METRIC_MAP = {
    'Resting Heart Rate': 'restingHeartRate',
    'Average Steps': 'steps',
    'Sleep Score': 'sleepScore',
    'Respiration': 'latestRespirationValue',
    'Stress': 'averageStressLevel',
    'Body Battery': 'bodyBatteryMostRecentValue',
    'HRV': 'hrvValue',
    'VO2 Max': 'vo2MaxValue',
    'Total Calories': 'activeCalories'
}

@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(st.secrets["GARMIN_EMAIL"], st.secrets["GARMIN_PASSWORD"])
    api.login()
    today = datetime.date.today()
    stats_list = []
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            row = api.get_stats(day.isoformat()) or {}
            steps = api.get_steps_data(day.isoformat())
            summary = api.get_daily_summary(day.isoformat())
            row['Date'] = day
            row['steps'] = steps[0]['steps'] if steps else 0
            row['activeCalories'] = summary.get('activeKilocalories', 0)
            stats_list.append(row)
        except Exception: continue
    return pd.DataFrame(stats_list)

try:
    df = get_data().set_index('Date').sort_index(ascending=False)
    df = df.apply(pd.to_numeric, errors='coerce')
    
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
        st.success("✅ No selected metrics have shifted by more than 10%.")

except Exception as e:
    st.error(f"Error: {e}")
