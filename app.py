import time
import pandas as pd
import streamlit as st
from rich import print
from functions import transform_df, generate_csv

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