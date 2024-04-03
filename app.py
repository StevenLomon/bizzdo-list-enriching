import requests, time, re
import pandas as pd
import streamlit as st
from rich import print
from bs4 import BeautifulSoup

def transform_df(df):
    headers = ({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36', 
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.hitta.se/',
            'DNT': '1',})

    df.rename(columns= {'CompanyLink':'Företag', 'LabeledText__text':'Omsättning', 
                        'LabeledText__text 2':'Resultat', 'CompanyLink href':'Bizzdo URL'}, inplace=True)
    df['Hemsida'] = ''
    df['Telefon'] = ''
    df['VD Tilltalsnamn'] = ''
    df['VD Efternamn'] = ''
    df['VD Ålder'] = ''
    df['VD Stad'] = ''
    df['Få kontorsnummer från'] = ''
    df['Få personligt nummer från'] = ''

    for company in df.iterrows():
        pass

def extract_org_and_website_status(url, headers):
    request = requests.get(url, headers=headers)
    soup = Beau
        


##STREAMLIT
st.title('Bizzdo List Enricher')

uploaded_file = st.file_uploader("Upload your input CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df_transformed = transform_df(df)

    