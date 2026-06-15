import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime
import os

st.set_page_config(page_title="Garmin Dashboard", layout="wide")
st.title("Garmin Master Dashboard")

# 1. Credentials
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# 2. Resilient Data Fetching
@st.cache_data(ttl=3600)
def get_data():
    # Force clean login by passing None for token path
    # This prevents the library from trying to read/write files that Streamlit deletes
    api = Garmin(email, password)
    
    # login() is sufficient if we don't need persistent tokens between reloads
    api.login()
    
    today = datetime.date.today()
    stats_list = []
    
    # Fetch 30 days
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            # get_stats is the most stable endpoint for daily data
            data = api.get_stats(day.isoformat())
            if data:
                data['Date'] = day
                stats_list.append(data)
        except Exception:
            continue
            
    return pd.DataFrame(stats_list)

try:
    with st.spinner("Connecting..."):
        df = get_data()
        
    if df is not None and not df.empty:
        # Numeric cleanup
        for col in df.columns:
            if col != 'Date':
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Metric Selection
        st.subheader("Visual Analysis")
        cols = [c for c in df.columns if c != 'Date']
        selected = st.multiselect("Select metrics:", cols, default=['restingHeartRate', 'sleepScore'] if 'restingHeartRate' in cols else cols[:2])
        
        if selected:
            st.line_chart(df.set_index('Date')[selected])
            
            # Readiness Index
            latest = df.iloc[0]
            avg = df.mean(numeric_only=True)
            
            score_parts = []
            for s in selected:
                if pd.notna(latest[s]) and pd.notna(avg[s]) and avg[s] != 0:
                    if s in ['restingHeartRate', 'averageStressLevel']:
                        score_parts.append((1 - (latest[s] / avg[s])) * 100)
                    else:
                        score_parts.append((latest[s] / avg[s]) * 100)
            
            if score_parts:
                final_index = sum(score_parts) / len(score_parts)
                st.metric("Readiness Index", f"{int(final_index + 100)}/100")
    else:
        st.error("No data found. Ensure you have no 2FA on your account.")

except Exception as e:
    st.error(f"Application Error: {str(e)}")
