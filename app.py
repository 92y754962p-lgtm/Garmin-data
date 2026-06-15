import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Garmin Auto-Monitor", layout="centered")
st.title("Performance Monitor")

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
    with st.spinner("Analyzing health trends..."):
        df = get_data()
        
    if df is not None and not df.empty:
        # 1. Clean numeric data
        df = df.set_index('Date')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 2. Automated Trend Detection
        # We define 'trending poorly' as > 1.5 standard deviations from mean
        latest = df.iloc[0]
        means = df.mean()
        stds = df.std()
        
        alerts = []
        for col in df.columns:
            if stds[col] > 0:
                z = (latest[col] - means[col]) / stds[col]
                # Logic: Invert for RHR/Stress (where high = bad)
                if col in ['restingHeartRate', 'averageStressLevel']:
                    if z > 1.5: alerts.append(f"⚠️ **{col}**: Significantly elevated.")
                # Logic: Standard for Sleep/Activity (where low = bad)
                else:
                    if z < -1.5: alerts.append(f"⚠️ **{col}**: Significantly low.")

        # 3. Render Summaries
        st.subheader("System Status")
        if not alerts:
            st.success("✅ All systems stable. No abnormal trends detected.")
        else:
            st.warning("Action Required:")
            for alert in alerts:
                st.markdown(alert)
                
        st.subheader("General Readiness")
        # Simplified Readiness Index display
        st.metric("Aggregate Health Index", f"{int(100 - (df.iloc[0].mean() / df.mean().mean() * 10))}/100")

    else:
        st.error("No data found. Ensure 2FA is disabled.")

except Exception as e:
    st.error(f"Analysis Error: {str(e)}")
