import requests, time
import pandas as pd
import streamlit as st
from rich import print
from bs4 import BeautifulSoup

headers = ({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36', 
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.hitta.se/',
            'DNT': '1',})

def construct_company_page(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    page = None
    try:
        href = soup.find('a', class_="style_searchResultLink__2i2BY").get('href')
        page = f"https://hitta.se{href}"
    except:
        pass
    return page

def extract_org_and_website_status(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    org_nr = soup.find('p', class_="text-caption-md-regular color-text-placeholder").text.split()[1].replace('-', '')
    webpage_source = soup.find('a', attrs={'data-track':'homepage-detail-noncustomer'})
    webpage = None
    if webpage_source is None:
        webpage = "Missing"
    else:
        webpage = webpage_source.get('href')
    return (org_nr, webpage)

def extract_age_city_and_personal_url(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    age = None
    city = None
    next_page = None
    try:
        info = soup.find('div', class_='finance-persons__text-container').find_all('div')[2].text
        age = int(info.split(",")[0].split()[0])
        city = info.split(",")[1].strip()
        href = soup.find('a', attrs={'data-track':'show-person, Styrelsemedlemmar'}).get('href')
        next_page = f"https://hitta.se{href}"
    except:
        pass
    return (age, city, next_page)

def extract_full_name(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    h1 = None
    try:
        h1 = soup.find('h1', class_='heading--1').text
    except:
        pass
    return h1

def transform_df(df, progress_bar, status_text):
    df.rename(columns= {'CompanyLink':'Företag', 'rt-td':'Omsättning', 
                        'rt-td 2':'Resultat', 'CompanyLink href':'Bizzdo URL'}, inplace=True)

    webpage_list = []
    vd_fname_list = []
    vd_lname_list = []
    age_list = []
    city_list = []
    office_phone_list = []
    personal_phone_list = []

    for index, row in df.iterrows():
        # Update progress bar and status text
        progress = int((index + 1) / len(df) * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing row {index + 1} out of {len(df)}")

        company_name_query_1 = row['Företag'].replace(' ', '%20').strip()
        company_name_query_2 = row['Företag'].lower().replace(' ', '+').strip()
        hitta_url = f"https://www.hitta.se/s%C3%B6k?vad={company_name_query_1}"
        office_phone_url = org_nr = webpage = None
        try:
            org_nr, webpage = extract_org_and_website_status(hitta_url, headers)
            office_phone_url = hitta_url
        except:
            company_page = construct_company_page(hitta_url, headers)
            if company_page:
                org_nr, webpage = extract_org_and_website_status(company_page, headers)
                office_phone_url = company_page
        if org_nr:
            beslutfattare_page = f"https://hitta.se/företagsinformation/{company_name_query_2}/{org_nr}#persons"
            age, city, personal_url = extract_age_city_and_personal_url(beslutfattare_page, headers)
            fname = lname = None
            if personal_url:
                full_name = extract_full_name(personal_url, headers)
                try:
                    fname, lname = full_name.split()
                except:
                    pass

        webpage_list.append(webpage)
        vd_fname_list.append(fname)
        vd_lname_list.append(lname)
        age_list.append(age)
        city_list.append(city)
        office_phone_list.append(office_phone_url)
        personal_phone_url = None
        if fname and lname and city and age:
            personal_phone_url = f"https://mrkoll.se/resultat?n={fname}+{lname}&c={city}&min={age}&max={age}&sex=a&c_stat=all&company="
        personal_phone_list.append(personal_phone_url)

    df['Hemsida'] = pd.Series(webpage_list, index=df.index)
    df['VD Tilltalsnamn'] = pd.Series(vd_fname_list, index=df.index)
    df['VD Efternamn'] = pd.Series(vd_lname_list, index=df.index)
    df['VD Ålder'] = pd.Series(age_list, index=df.index)
    df['VD Stad'] = pd.Series(city_list, index=df.index)
    df['Företagsnummer 1'] = None
    df['Företagsnummer 2'] = None
    df['Personligt nummer'] = None
    df['Få företagssnummer från'] = pd.Series(office_phone_list, index=df.index)
    df['Få personligt nummer från'] = pd.Series(personal_phone_list, index=df.index)

    # Reset progress bar at the end of the function
    progress_bar.empty()
    status_text.text("Done processing!")

    return df

def generate_csv(dataframe, result_name):
    if result_name.endswith('.csv'):
        result_name = result_name
    else:
        result_name = result_name + '.csv'
    dataframe.to_csv(result_name, index=False)
    return result_name

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