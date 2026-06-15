import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Performance Monitor", layout="centered")
st.title("Performance Monitor (Sensitivity: 7.5%)")

# --- AUTHENTICATION ---
# Ensure these are set in your App Settings -> Secrets in Streamlit Cloud
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# Define metric "health" direction: True = Higher is better, False = Lower is better
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
    # Pull 30 days to build a robust baseline
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            data = api.get_stats(day.isoformat())
            if data:
                data['Date'] = day
                stats_list.append(data)
        except Exception: 
            continue
    return pd.DataFrame(stats_list)

# --- MAIN DASHBOARD ---
try:
    with st.spinner("Analyzing your health trends..."):
        df = get_data()
        
    if df is not None and not df.empty:
        # CLEANING: Set Date as index, then force everything to numeric
        df = df.set_index('Date')
        df = df.apply(pd.to_numeric, errors='coerce')
        
        # Calculate Rolling Shift: Last 7 days vs Previous 23 days
        last_7_days = df.head(7).mean()
        previous_23_days = df.tail(23).mean()
        
        alerts = []
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        st.subheader("7-Day Trend Analysis")
        for col in key_metrics:
            if col in df.columns and pd.notna(last_7_days[col]) and pd.notna(previous_23_days[col]) and previous_23_days[col] != 0:
                # Calculate percentage shift
                shift = (last_7_days[col] - previous_23_days[col]) / previous_23_days[col]
                
                is_higher_better = METRIC_DIRECTION.get(col, True)
                
                # Flag if shift > 7.5% in the "bad" direction
                if (is_higher_better and shift < -0.075) or (not is_higher_better and shift > 0.075):
                    alerts.append(f"⚠️ **{col}**: Trending **{shift:.1%}** vs baseline.")

        if not alerts:
            st.success("✅ No negative shifts detected in the last week.")
        else:
            for alert in alerts:
                st.warning(alert)
                
        # READINESS INDEX
        st.divider()
        st.subheader("General Readiness")
        numeric_df = df.select_dtypes(include=['number'])
        readiness = int(100 - (numeric_df.iloc[0].mean() / numeric_df.mean().mean() * 10))
        st.metric("Aggregate Health Index", f"{readiness}/100")
        
    else:
        st.error("No data returned. Ensure you have no 2FA on your account.")

except Exception as e:
    st.error(f"Analysis Error: {str(e)}")
