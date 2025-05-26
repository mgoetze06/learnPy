from strava import getStravaData
import numpy as np
import streamlit as st
import time


activities = getStravaData(True)
st.success('Gathered Activities!', icon="✅")
rides = activities.loc[activities['type'] == 'Ride']

rides["distance"] = round(rides["distance"] / 1000,2)
rides["average_speed"] = round(rides['average_speed'] * 3.6,2)
rides["max_speed"] = round(rides['max_speed'] * 3.6,2)


col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Activity Count", value=len(rides))
with col2:
    st.metric(label="Total Distance", value=round(sum(rides["distance"]),2))
with col3:
    st.metric(label="Max Average Speed", value=round(max(rides['average_speed']),2))
# for i in range(1, 101):
#     new_rows = last_rows[-1, :] + np.random.randn(5, 1).cumsum(axis=0)
#     chart.add_rows(new_rows)
#     last_rows = new_rows
#     time.sleep(0.05)

#chart.add_rows(rides["distance"])

# chart = (
#     alt.Chart(rides)
#     .encode(
#         x="year:T",
#         y=alt.Y("Gross Agricultural Product ($B):Q", stack=None),
#         color="Region:N",
#     )
# )
# st.altair_chart(chart, use_container_width=True)

st.bar_chart(data=rides, x='start_date_local',x_label='Datum', y='distance')
st.bar_chart(data=rides, x='start_date_local',x_label='Datum', y='average_speed')
st.bar_chart(data=rides, x='start_date_local',x_label='Datum', y='max_speed')
st.bar_chart(data=rides, x='start_date_local',x_label='Datum', y='elapsed_time')

#data = df.loc[countries]
#data /= 1000000.0
st.subheader("Bike Rides")
st.dataframe(rides.sort_index())

# Streamlit widgets automatically run the script from top to bottom. Since
# this button is not connected to any other logic, it just causes a plain
# rerun.
st.button("Rerun")