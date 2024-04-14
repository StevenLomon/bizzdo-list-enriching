import requests, time, re
import pandas as pd
import streamlit as st
from rich import print
from bs4 import BeautifulSoup
from functions import format_for_krafman, attempt_to_extract_org_and_website_and_button_status, extract_full_name_age_and_city
from functions import extract_phone_number, transform_df, generate_csv

headers = ({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36', 
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.hitta.se/',
            'DNT': '1',})

##STREAMLIT
st.title('Bizzdo List Enricher')

result_name = st.text_input('Enter a name for the resulting csv file:', '')
uploaded_file = st.file_uploader("Upload your input CSV file", type=["csv"])

if st.button('Generate File'):
    if uploaded_file is not None:
        with st.spinner('Generating file, hold on'):
            # Create a progress bar and a dynamic text element
            progress_bar = st.progress(0)
            status_text = st.empty()

            print("Running...")
            start_time = time.time()
            df = pd.read_csv(uploaded_file)
            total_number_of_rows = len(df)

            df_transformed = transform_df(df, progress_bar, status_text)
            end_time = time.time()
            st.text(f"Done! Processed {total_number_of_rows} rows in {end_time - start_time} seconds")
            with open ("times.txt", "a") as f:
                f.write(f"Total: {total_number_of_rows}, Time: {end_time - start_time}\n")

            csv = generate_csv(df_transformed, result_name)
            with open(csv, "rb") as file:
                st.download_button(label="Download enriched list as csv", data=file, file_name=csv, mime='text/csv')
    else:
        st.error("There was an error handling the uploaded csv. Please try again")