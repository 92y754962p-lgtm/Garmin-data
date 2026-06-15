import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Garmin Master Dashboard", layout="wide")
st.title("Garmin Master Dashboard")

# --- AUTHENTICATION ---
# Ensure these are set in your Streamlit Cloud "Secrets"
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# --- DATA PIPELINE ---
@st.cache_data(ttl=3600) # Cache data for 1 hour to prevent API rate-limiting
def fetch_garmin_data():
    api = Garmin(email, password)
    api.login()
    today = datetime.date.today()
    # Fetch last 30 days
    data_list = [api.get_stats((today - datetime.timedelta(days=i)).isoformat()) 
                 for i in range(30)]
    return pd.DataFrame(data_list)

try:
    with st.spinner("Aggregating your health data..."):
        df = fetch_garmin_data()
        
        # Clean Data: Drop columns with no data and convert types to numeric
        df = df.dropna(axis=1, how='all')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')
            
        # --- INTERACTIVE UI ---
        st.subheader("Select Metrics for Trend Analysis")
        # Default metrics relevant to your health goals
        available_cols = df.columns.tolist()
        default_cols = [c for c in ['restingHeartRate', 'sleepScore', 'averageStressLevel'] if c in available_cols]
        
        selected_metrics = st.multiselect("Choose data points to visualize:", available_cols, default=default_cols)
        
        if selected_metrics:
            # Render chart
            st.line_chart(df[selected_metrics])
            
            # --- READINESS INDEX (Intuitive Progress) ---
            st.subheader("Readiness Index (0-100)")
            
            # Simple average of selected metrics, adjusted for "better is lower" metrics (like RHR/Stress)
            # This is a basic normalization: (1 - (Value / Baseline)) * 100
            current_readiness = []
            for m in selected_metrics:
                # Invert RHR/Stress so lower is better (higher readiness)
                if m in ['restingHeartRate', 'averageStressLevel']:
                    score = (1 - (df[m].iloc[0] / df[m].mean())) * 100
                else:
                    score = (df[m].iloc[0] / df[m].mean()) * 100
                current_readiness.append(score)
            
            final_index = sum(current_readiness) / len(current_readiness)
            
            st.metric("Readiness Index", f"{int(final_index + 100)}/100")
            
            if final_index > 5:
                st.success("Performance Trend: Positive. You are exceeding your 30-day baseline.")
            elif final_index < -5:
                st.warning("Performance Trend: Declining. Prioritize recovery.")
            else:
                st.info("Performance Trend: Stable. You are perfectly adapted to current load.")

except Exception as e:
    st.error(f"Data Fetch Failed: {e}. Check credentials or API status.")
