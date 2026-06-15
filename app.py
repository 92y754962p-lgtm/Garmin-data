import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Garmin Master Dashboard", layout="wide")
st.title("Garmin Master Dashboard")

# --- AUTHENTICATION ---
# Ensure GARMIN_EMAIL and GARMIN_PASSWORD are set in Streamlit Cloud Secrets
if "GARMIN_EMAIL" not in st.secrets or "GARMIN_PASSWORD" not in st.secrets:
    st.error("Secrets not found! Please add GARMIN_EMAIL and GARMIN_PASSWORD to your Streamlit Cloud Secrets.")
    st.stop()

email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

# --- DATA PIPELINE ---
@st.cache_data(ttl=3600)
def fetch_garmin_data():
    api = Garmin(email, password)
    api.login()
    today = datetime.date.today()
    # Fetch 30 days of data
    data_list = [api.get_stats((today - datetime.timedelta(days=i)).isoformat()) 
                 for i in range(30)]
    return pd.DataFrame(data_list)

# --- MAIN APP ---
try:
    with st.spinner("Aggregating your health data..."):
        df = fetch_garmin_data()
        
        # Clean Data: Drop columns with no data and convert types
        df = df.dropna(axis=1, how='all')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')
            
        # --- UI: METRIC SELECTION ---
        st.subheader("Select Metrics for Trend Analysis")
        available_cols = df.columns.tolist()
        # Set intuitive defaults
        default_cols = [c for c in ['restingHeartRate', 'sleepScore', 'averageStressLevel'] if c in available_cols]
        
        selected_metrics = st.multiselect("Choose data points to visualize:", available_cols, default=default_cols)
        
        if selected_metrics:
            # Render chart
            st.line_chart(df[selected_metrics])
            
            # --- READINESS INDEX ---
            st.subheader("Readiness Index (0-100)")
            
            # Logic: Normalize scores (100 is baseline)
            current_readiness = []
            for m in selected_metrics:
                # Invert metrics where lower is better
                if m in ['restingHeartRate', 'averageStressLevel']:
                    score = (1 - (df[m].iloc[0] / df[m].mean())) * 100
                else:
                    score = (df[m].iloc[0] / df[m].mean()) * 100
                current_readiness.append(score)
            
            final_index = sum(current_readiness) / len(current_readiness)
            
            st.metric("Readiness Index", f"{int(final_index + 100)}/100")
            
            # Advice
            if final_index > 5:
                st.success("Performance Trend: Positive. You are exceeding your 30-day baseline.")
            elif final_index < -5:
                st.warning("Performance Trend: Declining. Prioritize recovery.")
            else:
                st.info("Performance Trend: Stable. You are perfectly adapted to current load.")
        else:
            st.info("Select metrics above to view your Readiness Index.")

except Exception as e:
    st.error(f"Data Fetch Failed: {e}. If this persists, verify your password has no special character encoding issues.")
