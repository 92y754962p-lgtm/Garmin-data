import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Performance Monitor", layout="wide")
st.title("Performance Monitor (10% Sensitivity)")

email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# --- DATA PIPELINE ---
@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(email, password)
    api.login()
    today = datetime.date.today()
    stats_list = []
    
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            # Fetch base stats
            data = api.get_stats(day.isoformat()) or {}
            
            # Explicitly fetch Steps and Calories
            steps_data = api.get_steps_data(day.isoformat())
            daily_summary = api.get_daily_summary(day.isoformat())
            
            data['Date'] = day
            data['steps'] = steps_data[0]['steps'] if steps_data else 0
            data['activeCalories'] = daily_summary.get('activeKilocalories', 0)
            
            stats_list.append(data)
        except Exception: continue
    return pd.DataFrame(stats_list)

if st.button("Clear Cache & Refresh"):
    st.cache_data.clear()
    st.rerun()

# --- MAIN DASHBOARD ---
try:
    with st.spinner("Analyzing..."):
        df = get_data()
        
    if df is not None and not df.empty:
        df = df.set_index('Date').sort_index(ascending=False)
        df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
        
        last_7 = df.iloc[:7].mean()
        prev_23 = df.iloc[7:30].mean()
        
        active_shifts = []
        stable_metrics = []
        
        for col in df.columns:
            if pd.notna(last_7[col]) and pd.notna(prev_23[col]) and prev_23[col] != 0:
                shift = (last_7[col] - prev_23[col]) / prev_23[col]
                data_row = {"Metric": col, "7-Day": f"{last_7[col]:.1f}", "Prev 23": f"{prev_23[col]:.1f}", "Shift": f"{shift:.2%}"}
                
                # THRESHOLD: 10%
                if abs(shift) > 0.10:
                    active_shifts.append(data_row)
                else:
                    stable_metrics.append(data_row)
        
        if active_shifts:
            st.subheader("⚠️ Detected Shifts (>10%)")
            st.table(pd.DataFrame(active_shifts).set_index("Metric"))
        else:
            st.success("✅ No metrics have shifted by more than 10%.")
            
        with st.expander("View Stable Metrics (<=10% shift)"):
            if stable_metrics:
                st.table(pd.DataFrame(stable_metrics).set_index("Metric"))
        
        st.divider()
        st.subheader("General Readiness")
        readiness_df = df.drop(columns=['steps'], errors='ignore')
        readiness = int(100 - (readiness_df.iloc[0].mean() / readiness_df.mean().mean() * 10))
        st.metric("Aggregate Health Index", f"{readiness}/100")
        
    else:
        st.error("No data found.")

except Exception as e:
    st.error(f"Analysis Error: {e}")
