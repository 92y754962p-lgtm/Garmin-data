import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Performance Monitor", layout="centered")
st.title("Performance Monitor (Sensitivity: 7.5%)")

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
    with st.spinner("Analyzing trends..."):
        df = get_data()
        
    if df is not None and not df.empty:
        df = df.set_index('Date')
        df = df.apply(pd.to_numeric, errors='coerce')
        
        last_7_days = df.head(7).mean()
        last_30_days = df.mean()
        
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        st.subheader("7-Day vs 30-Day Trends")
        
        # Table with formatted whole percentages/numbers (no overkill decimals)
        comparison_data = []
        for col in key_metrics:
            if col in df.columns:
                comparison_data.append({
                    "Metric": col,
                    "7-Day Avg": round(last_7_days[col], 1),
                    "30-Day Avg": round(last_30_days[col], 1)
                })
        st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        
        # ALERTS
        alerts = []
        for col in key_metrics:
            if col in df.columns and pd.notna(last_7_days[col]) and pd.notna(last_30_days[col]) and last_30_days[col] != 0:
                shift = (last_7_days[col] - last_30_days[col]) / last_30_days[col]
                is_higher_better = METRIC_DIRECTION.get(col, True)
                
                if (is_higher_better and shift < -0.075) or (not is_higher_better and shift > 0.075):
                    # Changed {:.1%} to {:.0%} to show whole percentages only
                    alerts.append(f"⚠️ **{col}**: Trending **{shift:.0%}** vs baseline.")

        if not alerts:
            st.success("✅ No negative shifts detected.")
        else:
            for alert in alerts:
                st.warning(alert)
                
        st.divider()
        st.subheader("General Readiness")
        numeric_df = df.select_dtypes(include=['number'])
        readiness = int(100 - (numeric_df.iloc[0].mean() / numeric_df.mean().mean() * 10))
        st.metric("Aggregate Health Index", f"{readiness}/100")

except Exception as e:
    st.error(f"Analysis Error: {str(e)}")
