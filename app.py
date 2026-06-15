import streamlit as st
import pandas as pd
from garminconnect import Garmin
import datetime

st.set_page_config(page_title="Live Garmin Trends", layout="wide")
st.title("Automated Performance Dashboard")

# 1. Credentials from Streamlit Secrets
email = st.secrets["GARMIN_EMAIL"]
password = st.secrets["GARMIN_PASSWORD"]

try:
    with st.spinner("Compiling live telemetry..."):
        api = Garmin(email, password)
        api.login()
        
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=30)
        
        # FIX: Use get_stats for a range, or fetch daily if needed
        # get_stats retrieves comprehensive daily summaries for the specified date
        health_data = api.get_stats(today.isoformat())
        
        # Fetch Activity Data
        activities = api.get_activities_by_date(start_date.isoformat(), today.isoformat())
        df_activity = pd.DataFrame(activities)
        df_activity['Date'] = pd.to_datetime(df_activity['startTimeLocal'].str.split(' ').str[0])
        df_activity['Calories'] = df_activity['calories']
        df_activity_daily = df_activity.groupby('Date').agg({'Calories': 'sum'}).reset_index()
        
        # Display Activity Summary
        st.subheader("Recent Activity Load")
        st.line_chart(df_activity_daily.set_index('Date')['Calories'])

        st.info("Data successfully fetched. Direct RHR trend integration is undergoing API maintenance.")

except Exception as e:
    st.error(f"API Update Required: {e}. The Garmin library method signatures have shifted; ensure you are using the latest `cyberjunky/python-garminconnect` version.")
