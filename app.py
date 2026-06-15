import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Live Garmin Trends", layout="wide")
st.title("Automated Performance Dashboard")

# 1. Secure Authentication via Streamlit Secrets
# Ensure you have set these in your app's Secrets settings on share.streamlit.io
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

try:
    with st.spinner("Fetching live data from Garmin API..."):
        # Initialize API bridge
        api = Garmin(email, password)
        api.login()
        
        today = datetime.date.today()
        # Fetch 30 days of history
        start_date = today - datetime.timedelta(days=30)
        
        # Fetch Health Data (RHR)
        rhr_data = api.get_rhr_day(start_date.isoformat(), today.isoformat())
        df_health = pd.DataFrame(rhr_data)
        df_health['Date'] = pd.to_datetime(df_health['calendarDate'])
        # Extract RHR from dictionary values
        df_health['RHR'] = df_health['values'].apply(lambda x: x.get('restingHR') if isinstance(x, dict) else None)
        
        # Fetch Activity Data
        activities = api.get_activities_by_date(start_date.isoformat(), today.isoformat())
        df_activity = pd.DataFrame(activities)
        df_activity['Date'] = pd.to_datetime(df_activity['startTimeLocal'].str.split(' ').str[0])
        df_activity['Calories'] = df_activity['calories']
        
        # Aggregate daily activity calories
        df_activity_daily = df_activity.groupby('Date').agg({'Calories': 'sum'}).reset_index()
        
        # Merge health and activity data
        df_merged = pd.merge(df_health[['Date', 'RHR']], df_activity_daily, on='Date', how='left').fillna(0)
        df_merged = df_merged.sort_values('Date')
        df_merged['day_of_week'] = df_merged['Date'].dt.day_name()
        
        # Render Trends
        df_merged['7_day_trend'] = df_merged['RHR'].rolling(window=7, min_periods=1).mean()
        st.subheader("RHR & Active Caloric Load")
        st.line_chart(df_merged.set_index('Date')[['RHR', '7_day_trend']])
        
        # 2. Algorithmic Advice Engine
        latest_rhr = df_merged['RHR'].iloc[-1]
        mean_rhr = df_merged['RHR'].mean()
        std_rhr = df_merged['RHR'].std()
        current_day = df_merged['day_of_week'].iloc[-1]
        z_score = (latest_rhr - mean_rhr) / std_rhr
        
        st.subheader("Actionable Directives")
        
        if current_day == "Saturday":
            if z_score > 1.0:
                st.error("Elevated Fatigue: Pre-match metrics are statistically poor. Throttle your 1.5-hour tennis intensity today.")
            else:
                st.success("Prime Readiness: Metrics are highly suppressed. You are cleared for peak exertion during today's tennis match.")
        elif current_day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            if z_score > 1.5:
                st.error(f"Critical Strain (Z={z_score:.2f}): CNS is compromised. Skip 50kg bench/rows today; walk only.")
            elif z_score > 0.5:
                st.warning(f"Moderate Fatigue (Z={z_score:.2f}): Keep resistance training strictly in the 30kg range. Do not push to failure.")
            else:
                st.info(f"Baseline Normal (Z={z_score:.2f}): Adapting well to calorie deficit. Proceed with standard loads.")

except Exception as e:
    st.error(f"API Connection Failed: {e}. Please check your credentials in the Secrets manager.")
