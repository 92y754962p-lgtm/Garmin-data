import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Performance Monitor", layout="centered")
st.title("Performance Monitor (Debug Mode)")

email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

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
    df = get_data()
    if df is not None and not df.empty:
        df = df.set_index('Date')
        df = df.apply(pd.to_numeric, errors='coerce')
        
        last_7 = df.head(7).mean()
        last_30 = df.mean()
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        # FORCE-SHOW TABLE
        comparison_data = []
        for col in key_metrics:
            if col in df.columns:
                shift = (last_7[col] - last_30[col]) / last_30[col]
                comparison_data.append({
                    "Metric": col, 
                    "7-Day": f"{last_7[col]:.2f}", 
                    "30-Day": f"{last_30[col]:.2f}", 
                    "Shift %": f"{shift:.4%}"
                })
        
        st.subheader("Raw Data Comparison")
        st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        
        st.divider()
        st.subheader("General Readiness")
        numeric_df = df.select_dtypes(include=['number'])
        readiness = int(100 - (numeric_df.iloc[0].mean() / numeric_df.mean().mean() * 10))
        st.metric("Aggregate Health Index", f"{readiness}/100")
        
    else:
        st.error("No data found.")
except Exception as e:
    st.error(f"Error: {e}")
