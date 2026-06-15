import streamlit as st
import pandas as pd

st.set_page_config(page_title="Garmin Trends", layout="wide")
st.title("Holistic Health & Performance Trends")

# 1. UI File Ingestion
uploaded_file = st.file_uploader("Upload your Garmin CSV", type=["csv"])

if uploaded_file is not None:
    try:
        # Pandas reads the uploaded file object directly from memory
        df = pd.read_csv(uploaded_file)
        
        # 2. Data Normalization
        # Note: Update 'date' and 'rhr' to match your exact Garmin column headers
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 3. Trend Rendering
        df['7_day_rhr'] = df['rhr'].rolling(window=7, min_periods=1).mean()
        
        st.subheader("Resting Heart Rate (RHR) Trend")
        st.line_chart(df.set_index('date')[['rhr', '7_day_rhr']])
        
        # 4. Algorithmic Advice Engine
        st.subheader("Actionable Directives")
        latest_rhr = df['rhr'].iloc[-1]
        mean_rhr = df['rhr'].mean()
        std_rhr = df['rhr'].std()
        
        if latest_rhr > (mean_rhr + std_rhr):
            st.error(f"High Fatigue: RHR is elevated ({latest_rhr:.1f} bpm). Reduce bench press and standing row volume today to allow central nervous system recovery.")
        elif latest_rhr < (mean_rhr - std_rhr):
            st.success(f"Prime Readiness: RHR is suppressed ({latest_rhr:.1f} bpm). Excellent physiological state to maximize intensity during Saturday tennis.")
        else:
            st.info(f"Baseline Normal: RHR ({latest_rhr:.1f} bpm) is stable. You are adapting predictably to the 700-calorie deficit. Proceed with standard scheduled load.")

    except KeyError as e:
        st.error(f"Error: Could not find column {e}. Please verify your CSV headers match the script.")
else:
    st.info("Awaiting CSV upload...")
