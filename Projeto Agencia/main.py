import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout='wide')

df = pd.read_csv('JANEIRO.csv', quotechar='"', skipinitialspace=True)
df
