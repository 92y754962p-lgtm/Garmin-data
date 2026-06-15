import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Dual-File Garmin Trends", layout="wide")
st.title("Holistic Health & Performance Trends")

col1, col2 = st.columns(2)
with col1:
    health_file = st.file_uploader("1. Upload Health CSV (e.g., RHR)", type=["csv"])
with col2:
    activity_file = st.file_uploader("2. Upload Activities CSV", type=["csv"])

if health_file and activity_file:
    try:
        # Load data
        df_health = pd.read_csv(health_file)
        df_activity = pd.read_csv(activity_file)
        
        # Standardize dates (Update 'Date' strings if Garmin headers differ)
        df_health['Date'] = pd.to_datetime(df_health.iloc[:, 0])
        df_activity['Date'] = pd.to_datetime(df_activity['Date'].str.split(' ').str[0])
        
        # Aggregate daily activity metrics (e.g., total calories burned per day)
        df_activity_daily = df_activity.groupby('Date').agg({'Calories': 'sum'}).reset_index()
        
        # Inner join on the exact date
        df_merged = pd.merge(df_health, df_activity_daily, on='Date', how='inner')
        df_merged['
