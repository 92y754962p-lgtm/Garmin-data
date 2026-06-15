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
        day_str = day.isoformat()
        try:
            # Start with the date to ensure the column always exists
            row = {'Date': day}
            
            # Fetch data safely
            stats = api.get_stats(day_str)
            if stats: row.update(stats)
            
            steps = api.get_steps_data(day_str)
            if steps: row['steps'] = steps[0].get('steps', 0)
            
            summary = api.get_daily_summary(day_str)
            if summary: row['activeCalories'] = summary.get('activeKilocalories', 0)
            
            stats_list.append(row)
        except Exception: 
            continue
    return pd.DataFrame(stats_list)

if st.button("Clear Cache & Refresh"):
    st.cache_data.clear()
    st.rerun()

try:
    df = get_data()
    if df is not None and not df.empty and 'Date' in df.columns:
        df = df.set_index('Date').sort_index(ascending=False)
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
    else:
        st.error("No data retrieved. Please ensure you are logged into Garmin.")
except Exception as e:
    st.error(f"Analysis Error: {e}")
