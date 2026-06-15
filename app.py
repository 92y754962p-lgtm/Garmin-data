import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Performance Monitor", layout="centered")
st.title("Performance Monitor (0.05% Sensitivity)")

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
    # Fetch 30 days total
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
        
    if df is not None and not df.empty:
        df = df.set_index('Date').sort_index(ascending=False)
        df = df.apply(pd.to_numeric, errors='coerce')
        
        # CLEAR SLICING: Most recent 7 vs the 23 days before that
        last_7 = df.iloc[:7].mean()
        prev_23 = df.iloc[7:30].mean()
        
        key_metrics = ['restingHeartRate', 'sleepScore', 'averageStressLevel', 'bodyBattery']
        
        comparison_data = []
        for col in key_metrics:
            if col in df.columns and pd.notna(last_7[col]) and pd.notna(prev_23[col]) and prev_23[col] != 0:
                shift = (last_7[col] - prev_23[col]) / prev_23[col]
                
                # Flag if shift > 0.05% in the "bad" direction
                is_better = METRIC_DIRECTION.get(col, True)
                if (is_better and shift < -0.0005) or (not is_better and shift > 0.0005):
                    comparison_data.append({
                        "Metric": col, 
                        "7-Day": f"{last_7[col]:.1f}", 
                        "Prev 23": f"{prev_23[col]:.1f}", 
                        "Status": "🔴"
                    })
        
        if comparison_data:
            st.subheader("⚠️ Attention Required")
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        else:
            st.success("✅ Metrics stable within 0.05% for this period.")
            
        # DEBUG: Verify shifts are being calculated
        with st.expander("View Raw Shift Data"):
            debug_df = pd.DataFrame({'Shift %': (last_7 - prev_23) / prev_23})
            st.write(debug_df.dropna())

except Exception as e:
    st.error(f"Analysis Error: {e}")
