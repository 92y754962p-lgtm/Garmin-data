import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Garmin Dashboard", layout="wide")
st.title("Garmin Master Dashboard")

# 1. Credentials
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# 2. Data Fetching
@st.cache_data(ttl=3600)
def get_data():
    api = Garmin(email, password)
    api.login()
    today = datetime.date.today()
    stats_list = []
    
    # Iterate through days
    for i in range(14):
        day = today - datetime.timedelta(days=i)
        try:
            data = api.get_stats(day.isoformat())
            if data:
                data['Date'] = day
                stats_list.append(data)
        except Exception:
            continue
            
    return pd.DataFrame(stats_list)

try:
    with st.spinner("Connecting to Garmin..."):
        df = get_data()
        
    if df is not None and not df.empty:
        # Numeric cleanup
        for col in df.columns:
            if col != 'Date':
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Metric Selection
        st.subheader("Visual Analysis")
        cols = [c for c in df.columns if c != 'Date']
        
        # Dynamically determine valid defaults to prevent "default value" errors
        valid_defaults = [c for c in ['restingHeartRate', 'sleepScore', 'averageStressLevel'] if c in cols]
        
        selected = st.multiselect("Select metrics:", cols, default=valid_defaults)
        
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
                st.info("Select a metric to calculate your Readiness Index.")
    else:
        st.error("No data found. This often happens if 2FA is enabled or the account has restricted API access.")

except Exception as e:
    st.error(f"Application Error: {e}")
