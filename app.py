import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Performance Monitor", layout="wide")
st.title("Performance Monitor (Color-Coded Health Shifts)")

# The confirmed, accurate internal API keys mapped to your preferred names
METRIC_MAP = {
    'Resting Heart Rate': 'restingHeartRate',
    'Average Steps': 'totalSteps',
    'Sleep Score': 'sleepScore',
    'Respiration': 'latestRespirationValue',
    'Stress': 'averageStressLevel',
    'Body Battery': 'bodyBatteryMostRecentValue',
    'HRV': 'hrvValue',
    'VO2 Max': 'vo2MaxValue',
    'Total Calories': 'activeKilocalories'
}

# Define which metrics are considered "healthy" when they increase
HIGHER_IS_BETTER = [
    'Average Steps', 'Sleep Score', 'Body Battery', 
    'HRV', 'VO2 Max', 'Total Calories'
]

def apply_health_colors(row):
    """Pandas Styler function to color the Shift column based on healthy metric direction."""
    metric = row.name
    shift_val = float(row['Shift'].strip('%'))
    
    if shift_val > 0:
        color = 'lightgreen' if metric in HIGHER_IS_BETTER else 'lightcoral'
    elif shift_val < 0:
        color = 'lightcoral' if metric in HIGHER_IS_BETTER else 'lightgreen'
    else:
        color = 'inherit'
        
    # Return empty strings for the first two columns to leave them uncolored, color the 3rd column
    return [''] * 2 + [f'color: {color}; font-weight: bold']

@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(st.secrets["GARMIN_EMAIL"], st.secrets["GARMIN_PASSWORD"])
    api.login()
    today = datetime.date.today()
    clean_data = []
    
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            day_stats = api.get_stats(day.isoformat()) or {}
            day_stats['Date'] = day
            clean_data.append(day_stats)
        except Exception:
            continue
            
    df = pd.DataFrame(clean_data)
    if not df.empty and 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        return df.set_index('Date').sort_index(ascending=False)
    return pd.DataFrame()

if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("Processing..."):
        df = get_data()
        
        if not df.empty:
            df = df.apply(pd.to_numeric, errors='coerce')
            
            last_7 = df.iloc[:7].mean()
            prev_23 = df.iloc[7:30].mean()
            
            active_shifts = []
            stable_metrics = []
            
            for display_name, api_key in METRIC_MAP.items():
                if api_key in df.columns and pd.notna(last_7.get(api_key)) and prev_23.get(api_key, 0) != 0:
                    shift = (last_7[api_key] - prev_23[api_key]) / prev_23[api_key]
                    
                    data_row = {
                        "Metric": display_name, 
                        "7-Day": f"{last_7[api_key]:.1f}", 
                        "Prev 23": f"{prev_23[api_key]:.1f}", 
                        "Shift": f"{shift:.2%}"
                    }
                    
                    if abs(shift) > 0.10: # 10% Sensitivity
                        active_shifts.append(data_row)
                    else:
                        stable_metrics.append(data_row)
            
            # Using st.dataframe instead of st.table because it renders Pandas Stylers flawlessly
            if active_shifts:
                st.subheader("⚠️ Detected Shifts (>10%)")
                active_df = pd.DataFrame(active_shifts).set_index("Metric")
                st.dataframe(active_df.style.apply(apply_health_colors, axis=1), use_container_width=True)
            else:
                st.success("✅ All primary metrics stable within 10%.")
                
            with st.expander("View Stable Metrics (<=10% shift)"):
                if stable_metrics:
                    stable_df = pd.DataFrame(stable_metrics).set_index("Metric")
                    st.dataframe(stable_df.style.apply(apply_health_colors, axis=1), use_container_width=True)
        else:
            st.error("No data retrieved. Please check Garmin login/servers.")
            
except Exception as e:
    st.error(f"Data Processing Error: {e}")
