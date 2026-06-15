import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(layout="wide")
st.title("Performance Dashboard")

email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

try:
    api = Garmin(email, password)
    api.login()
    today = datetime.date.today()
    
    # 1. Fetch Daily Summaries for the last 30 days
    # This returns a list of dictionaries with all metrics
    stats = api.get_stats(today.isoformat())
    
    # Let's create a DataFrame from the stats
    # Note: Adjust these keys if your Garmin version returns different nested structures
    df = pd.DataFrame([api.get_stats( (today - datetime.timedelta(days=i)).isoformat() ) 
                       for i in range(30)])
    
    # Clean up: Select key metrics
    # You can see available columns by uncommenting: st.write(df.columns)
    metrics_map = {
        'restingHeartRate': 'Resting Heart Rate',
        'averageStressLevel': 'Avg Stress',
        'sleepScore': 'Sleep Score',
        'activeKilocalories': 'Active Calories'
    }
    
    # Filter for columns that exist in the returned data
    available_metrics = {k: v for k, v in metrics_map.items() if k in df.columns}
    
    # 2. Interactive Selector
    selection = st.selectbox("Select Metric to Analyze:", list(available_metrics.values()))
    metric_key = [k for k, v in available_metrics.items() if v == selection][0]
    
    # 3. Process & Trend
    df[metric_key] = pd.to_numeric(df[metric_key], errors='coerce')
    st.line_chart(df[metric_key])
    
    # 4. Math-based Advice
    latest = df[metric_key].iloc[0]
    mean = df[metric_key].mean()
    std = df[metric_key].std()
    z = (latest - mean) / std if std > 0 else 0
    
    st.subheader(f"Status: {selection}")
    if abs(z) > 1.5:
        st.error(f"Alert: {selection} is deviating significantly (Z={z:.2f}). Adjust intensity.")
    else:
        st.success(f"Status: Baseline stable (Z={z:.2f}).")

except Exception as e:
    st.error(f"Data Fetch Error: {e}")
