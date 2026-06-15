import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Garmin Master Dashboard", layout="wide")
st.title("Garmin Master Dashboard")

# 1. Credentials from Secrets
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# 2. Forceful Data Fetching
@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(email, password)
    # The 'login' method is the most fragile part. 
    # We call it explicitly to capture initialization errors.
    if not api.login():
        return None
    
    today = datetime.date.today()
    # Fetch 30 days of data
    stats_list = []
    for i in range(30):
        day = today - datetime.timedelta(days=i)
        try:
            # We fetch user metrics using the most stable endpoint
            stats = api.get_stats(day.isoformat())
            if stats:
                stats['Date'] = day
                stats_list.append(stats)
        except:
            continue
            
    return pd.DataFrame(stats_list)

try:
    with st.spinner("Authenticating..."):
        df = get_data()
        
    if df is not None and not df.empty:
        # Clean Data
        df = df.dropna(axis=1, how='all')
        for col in df.columns:
            if col != 'Date':
                df[col] = pd.to_numeric(df[col], errors='ignore')
        
        # UI: Metric Selection
        st.subheader("Select Metrics for Trend Analysis")
        cols = [c for c in df.columns if c != 'Date']
        selected = st.multiselect("Visuals:", cols, default=['restingHeartRate', 'sleepScore'] if 'restingHeartRate' in cols else cols[:2])
        
        if selected:
            st.line_chart(df.set_index('Date')[selected])
            
            # Readiness Index
            st.subheader("Readiness Index (0-100)")
            latest = df.iloc[0]
            avg = df.mean(numeric_only=True)
            
            # Simple scoring logic
            scores = []
            for s in selected:
                if s in ['restingHeartRate', 'averageStressLevel']:
                    scores.append((1 - (latest[s] / avg[s])) * 100)
                else:
                    scores.append((latest[s] / avg[s]) * 100)
            
            final_index = sum(scores) / len(scores)
            st.metric("Readiness Index", f"{int(final_index + 100)}/100")
    else:
        st.error("Authentication succeeded, but no data returned. Garmin may be rate-limiting your connection.")

except Exception as e:
    st.error(f"Critical Failure: {str(e)}")
