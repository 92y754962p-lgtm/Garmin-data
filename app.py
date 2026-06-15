import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Garmin Health Monitor", layout="centered")
st.title("Performance Monitor (Trends)")

# --- AUTHENTICATION ---
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

METRIC_DIRECTION = {
    'restingHeartRate': False, 
    'averageStressLevel': False, 
    'sleepScore': True, 
    'bodyBattery': True
}

# --- DATA PIPELINE ---
@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(email, password)
    api.login()
    today = datetime.date.today()
    stats_list = []
    # Pull 30 days of data for baselining
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            data = api.get_stats(day.isoformat())
            if data:
                data['Date'] = day
                stats_list.append(data)
        except Exception: continue
    return pd.DataFrame(stats_list)

# --- MAIN DASHBOARD ---
try:
    with st.spinner("Calculating 7-day and 30-day trends..."):
        df = get_data()
        
    if df is not None and not df.empty:
        df = df.set_index('Date')
        df = df.apply(pd.to_numeric, errors='coerce')
        
        # CALCULATE TRENDS
        last_7_days = df.head(7).mean()
        last_30_days = df.mean() # This is already our 30-day mean
        
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        st.subheader("Trend Comparison")
        
        # Create a table for side-by-side comparison
        comparison_data = []
        for col in key_metrics:
            if col in df.columns:
                comparison_data.append({
                    "Metric": col,
                    "7-Day Avg": last_7_days[col],
                    "30-Day Avg": last_30_days[col]
                })
        st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        
        # ALERTS
        alerts = []
        for col in key_metrics:
            if col in df.columns and pd.notna(last_7_days[col]) and pd.notna(last_30_days[col]) and last_30_days[col] != 0:
                shift = (last_7_days[col] - last_30_days[col]) / last_30_days[col]
                is_higher_better = METRIC_DIRECTION.get(col, True)
                
                if (is_higher_better and shift < -0.075) or (not is_higher_better and shift > 0.075):
                    alerts.append(f"⚠️ **{col}**: Trending **{shift:.1%}** vs. 30-day baseline.")

        if not alerts:
            st.success("✅ No negative shifts detected.")
        else:
            for alert in alerts:
                st.warning(alert)
                
    else:
        st.error("No data found.")

except Exception as e:
    st.error(f"Analysis Error: {str(e)}")
