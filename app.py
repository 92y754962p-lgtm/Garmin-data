import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Performance Monitor", layout="centered")
st.title("Performance Monitor")

# --- AUTHENTICATION ---
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
    with st.spinner("Analyzing trends..."):
        df = get_data()
        
    if df is not None and not df.empty:
        df = df.set_index('Date')
        df = df.apply(pd.to_numeric, errors='coerce')
        
        last_7 = df.head(7).mean()
        last_30 = df.mean()
        
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        # STRICT EXCEPTION-ONLY LOGIC
        comparison_data = []
        for col in key_metrics:
            if col in df.columns and pd.notna(last_7[col]) and pd.notna(last_30[col]) and last_30[col] != 0:
                shift = (last_7[col] - last_30[col]) / last_30[col]
                is_better = METRIC_DIRECTION.get(col, True)
                
                # Only append if drift > 7.5% in the "bad" direction
                if (is_better and shift < -0.075) or (not is_better and shift > 0.075):
                    comparison_data.append({
                        "Metric": col, 
                        "7-Day": f"{last_7[col]:.1f}", 
                        "30-Day": f"{last_30[col]:.1f}", 
                        "Status": "🔴"
                    })
        
        # DISPLAY RESULTS
        if comparison_data:
            st.subheader("⚠️ Attention Required")
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        else:
            st.success("✅ All metrics are stable. No attention required.")
                
        st.divider()
        st.subheader("General Readiness")
        numeric_df = df.select_dtypes(include=['number'])
        readiness = int(100 - (numeric_df.iloc[0].mean() / numeric_df.mean().mean() * 10))
        st.metric("Aggregate Health Index", f"{readiness}/100")
        
    else:
        st.error("No data found. Ensure no 2FA on account.")

except Exception as e:
    st.error(f"Analysis Error: {str(e)}")
