import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Performance Monitor", layout="centered")
st.title("Performance Monitor (0.05% Sensitivity)")

# --- AUTHENTICATION ---
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# --- DATA PIPELINE ---
@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(email, password)
    api.login()
    today = datetime.date.today()
    stats_list = []
    # Pull 30 days
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            data = api.get_stats(day.isoformat())
            if data:
                data['Date'] = day
                stats_list.append(data)
        except Exception: continue
    return pd.DataFrame(stats_list)

# --- CACHE CONTROL ---
if st.button("Clear Cache & Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# --- MAIN DASHBOARD ---
try:
    with st.spinner("Analyzing..."):
        df = get_data()
        
    if df is not None and not df.empty:
        df = df.set_index('Date').sort_index(ascending=False)
        df = df.apply(pd.to_numeric, errors='coerce')
        
        # Calculate distinct non-overlapping periods
        last_7 = df.iloc[:7].mean()
        prev_23 = df.iloc[7:30].mean()
        
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        comparison_data = []
        for col in key_metrics:
            if col in df.columns and pd.notna(last_7[col]) and pd.notna(prev_23[col]) and prev_23[col] != 0:
                shift = (last_7[col] - prev_23[col]) / prev_23[col]
                
                # SHOW ANY SHIFT > 0.05% (0.0005) regardless of direction
                if abs(shift) > 0.0005: 
                    comparison_data.append({
                        "Metric": col, 
                        "7-Day": f"{last_7[col]:.2f}", 
                        "Prev 23": f"{prev_23[col]:.2f}", 
                        "Shift": f"{shift:.2%}"
                    })
        
        if comparison_data:
            st.subheader("Detected Shifts (>0.05%)")
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        else:
            st.success("✅ No metrics have shifted by more than 0.05% in the last week.")
                
        st.divider()
        st.subheader("General Readiness")
        numeric_df = df.select_dtypes(include=['number'])
        readiness = int(100 - (numeric_df.iloc[0].mean() / numeric_df.mean().mean() * 10))
        st.metric("Aggregate Health Index", f"{readiness}/100")
        
    else:
        st.error("No data found. Ensure no 2FA on account.")

except Exception as e:
    st.error(f"Analysis Error: {e}")
