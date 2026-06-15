import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Live Garmin API Trends", layout="wide")
st.title("Automated Performance Dashboard")

# 1. Secure Authentication via Sidebar
with st.sidebar:
    st.header("Garmin Connect Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    days_to_fetch = st.slider("Days of history to analyze:", 7, 30, 14)
    fetch_button = st.button("Fetch Live Data")

if fetch_button and email and password:
    try:
        with st.spinner("Authenticating and compiling Garmin JSON payloads..."):
            # Initialize API bridge
            api = Garmin(email, password)
            api.login()
            
            today = datetime.date.today()
            start_date = today - datetime.timedelta(days=days_to_fetch)
            
            # Fetch Health Data (RHR)
            rhr_data = api.get_rhr_day(start_date.isoformat(), today.isoformat())
            df_health = pd.DataFrame(rhr_data)
            # Normalize Garmin's JSON keys
            df_health['Date'] = pd.to_datetime(df_health['calendarDate'])
            df_health['RHR'] = df_health['values'].apply(lambda x: x.get('restingHR') if isinstance(x, dict) else None)
            
            # Fetch Activity Data
            activities = api.get_activities_by_date(start_date.isoformat(), today.isoformat())
            df_activity = pd.DataFrame(activities)
            df_activity['Date'] = pd.to_datetime(df_activity['startTimeLocal'].str.split(' ').str[0])
            df_activity['Calories'] = df_activity['calories']
            
            # Aggregate daily activity calories
            df_activity_daily = df_activity.groupby('Date').agg({'Calories': 'sum'}).reset_index()
            
            # Inner join
            df_merged = pd.merge(df_health[['Date', 'RHR']], df_activity_daily, on='Date', how='left').fillna(0)
            df_merged['day_of_week'] = df_merged['Date'].dt.day_name()
            df_merged = df_merged.sort_values('Date')
            
            # Render Trends
            df_merged['7_day_trend'] = df_merged['RHR'].rolling(window=7, min_periods=1).mean()
            st.subheader("RHR & Active Caloric Load")
            st.line_chart(df_merged.set_index('Date')[['RHR', '7_day_trend']])
            
            # 2. Algorithmic Directives
            latest_rhr = df_merged['RHR'].iloc[-1]
            mean_rhr = df_merged['RHR'].mean()
            std_rhr = df_merged['RHR'].std()
            current_day = df_merged['day_of_week'].iloc[-1]
            z_score = (latest_rhr - mean_rhr) / std_rhr
            
            st.subheader("Actionable Directives")
            
            if current_day == "Saturday":
                if z_score > 1.0:
                    st.error("Elevated Fatigue: Pre-match metrics are statistically poor. Throttle your 1.5-hour tennis intensity today to prevent overtraining.")
                else:
                    st.success("Prime Readiness: Metrics are highly suppressed. You are cleared for peak exertion during today's tennis match.")
            elif current_day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
                if z_score > 1.5:
                    st.error(f"Critical Strain (Z={z_score:.2f}): Central nervous system is mathematically compromised. Skip the 50kg bench press and standing rows today; maintain only the 1-mile outdoor walk.")
                elif z_score > 0.5:
                    st.warning(f"Moderate Fatigue (Z={z_score:.2f}): Keep resistance training strictly in the 30kg range for 12 reps. Do not push to failure.")
                else:
                    st.info(f"Baseline Normal (Z={z_score:.2f}): You are adapting predictably to the 700-calorie deficit. Proceed with standard scheduled lifting loads.")

    except Exception as e:
        st.error(f"API Connection Failed: {e}. Check your credentials or wait 15 minutes if Garmin is temporarily rate-limiting your IP.")
else:
    st.info("Awaiting credentials to query the Garmin API...")
