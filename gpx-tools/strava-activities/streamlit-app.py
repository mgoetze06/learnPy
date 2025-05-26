from strava import getStravaData
import numpy as np
import streamlit as st
import time


activities = getStravaData(True)

rides = activities.loc[activities['type'] == 'Ride']


last_rows = np.random.randn(1, 1)
chart = st.line_chart(last_rows)

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

st.bar_chart(data=rides, x='start_date_local', y='distance')

#data = df.loc[countries]
#data /= 1000000.0
st.subheader("Bike Rides")
st.dataframe(rides.sort_index(), use_container_width=True)

# Streamlit widgets automatically run the script from top to bottom. Since
# this button is not connected to any other logic, it just causes a plain
# rerun.
st.button("Rerun")