import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Performance Monitor", layout="centered")
st.title("Performance Monitor (7-Day Shift)")

# Credentials from Streamlit Cloud Secrets
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

METRIC_DIRECTION = {
    'restingHeartRate': False, 
    'averageStressLevel': False, 
    'sleepScore': True, 
    'bodyBattery': True
}

@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(email, password)
    api.login()
    today = datetime.date.today()
    stats_list = []
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            data = api.get_stats(day.isoformat())
            if data:
                data['Date'] = day
                stats_list.append(data)
        except Exception: continue
    return pd.DataFrame(stats_list)

try:
    with st.spinner("Analyzing trends..."):
        df = get_data()
        if df.empty:
            st.error("No data returned.")
            st.stop()

        # CLEANING: Set Date as index, then drop it so only numeric data remains
        df = df.set_index('Date')
        
        # Force conversion of every column to numeric, turning errors (text) into NaN
        df = df.apply(pd.to_numeric, errors='coerce')
        
        # CALCULATE ROLLING SHIFT (Only using numeric columns)
        last_7_days = df.head(7).mean()
        previous_23_days = df.tail(23).mean()
        
        alerts = []
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        st.subheader("7-Day Trend Analysis")
        for col in key_metrics:
            if col in df.columns and pd.notna(last_7_days[col]) and pd.notna(previous_23_days[col]) and previous_23_days[col] != 0:
                shift = (last_7_days[col] - previous_23_days[col]) / previous_23_days[col]
                is_higher_better = METRIC_DIRECTION.get(col, True)
                
                if (is_higher_better and shift < -0.10) or (not is_higher_better and shift > 0.10):
                    alerts.append(f"⚠️ **{col}**: Down {shift:.1%} vs 30-day baseline.")

        if not alerts:
            st.success("✅ No negative shifts detected in the last week.")
        else:
            for alert in alerts:
                st.warning(alert)
                
        # READINESS INDEX
        st.divider()
        st.subheader("General Readiness")
        # Final readiness score using only clean, numeric data
        numeric_df = df.select_dtypes(include=['number'])
        readiness = int(100 - (numeric_df.iloc[0].mean() / numeric_df.mean().mean() * 10))
        st.metric("Aggregate Health Index", f"{readiness}/100")

except Exception as e:
    st.error(f"Analysis Error: {e}")
