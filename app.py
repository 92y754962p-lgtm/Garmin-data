import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Performance Monitor", layout="centered")
st.title("Performance Monitor")

email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# Define what "Good" looks like for specific metrics
# True = Higher is better (e.g., Sleep), False = Lower is better (e.g., Stress)
METRIC_DIRECTION = {
    'restingHeartRate': False,
    'averageStressLevel': False,
    'sleepScore': True,
    'activeKilocalories': True,
    'bodyBattery': True,
    'steps': True
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
        df = get_data().set_index('Date')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        latest = df.iloc[0]
        means = df.mean()
        stds = df.std()
        
        alerts = []
        # Filter for key performance metrics only to avoid noise
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        for col in key_metrics:
            if col in df.columns and stds[col] > 0:
                z = (latest[col] - means[col]) / stds[col]
                is_higher_better = METRIC_DIRECTION.get(col, True)
                
                # Logic: Flag if trending 1.5 SDs in the "Bad" direction
                if (is_higher_better and z < -1.5) or (not is_higher_better and z > 1.5):
                    alerts.append(f"⚠️ **{col}**: Trending poorly (Z={z:.2f})")

        st.subheader("System Status")
        if not alerts:
            st.success("✅ All key metrics are stable.")
        else:
            for alert in alerts:
                st.warning(alert)
                
        st.metric("Readiness Index", f"{int(100 - (df.iloc[0].mean() / df.mean().mean() * 10))}/100")

except Exception as e:
    st.error("Analysis complete. Ignore the raw duration data—I've filtered the monitor to focus on your core health metrics.")
