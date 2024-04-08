import requests, time, re
import pandas as pd
import streamlit as st
from rich import print
from bs4 import BeautifulSoup

headers = ({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36', 
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.hitta.se/',
            'DNT': '1',})

def format_for_krafman(company_name):
    company_name = company_name.lower()
    company_name = re.sub(r'[^\w\s]', '', company_name)
    company_name = re.sub(r'\s+', ' ', company_name)  # Collapse multiple spaces into one
    company_name = company_name.strip()  # Remove leading/trailing spaces
    company_name = company_name.replace(' ', '-')
    return company_name

def attempt_to_extract_org_and_website_and_button_status(hitta_search_url, headers):
    response = requests.get(hitta_search_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    org_nr = webpage = buttonexists = None

    # First of all, see if we are actually on the company page
    try:
        if soup.find('div', class_='section-header--meta'):
            
            org_nr = soup.find('p', class_="text-caption-md-regular color-text-placeholder").text.split()[1].replace('-', '')
            webpage_source = soup.find('a', attrs={'data-track':'homepage-detail-noncustomer'})
            button_source = soup.find('button', class_='style_button__pqvvx style_phoneNumberButton__g0QE1')
            if webpage_source is None:
                webpage = "Missing"
            else:
                webpage = webpage_source.get('href')
            if button_source is None:
                buttonexists = False
            else:
                buttonexists = True
    except:
        pass
    return (org_nr, webpage, buttonexists)  

def extract_full_name_age_and_city(befattningshavare_url, headers):
    response = requests.get(befattningshavare_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    full_name = age = city = None
    try:
        div = soup.find('div', class_='finance-persons__text-container')
        if div.find_all('a'):
            href = soup.find('a', attrs={'data-track':'show-person, Styrelsemedlemmar'}).get('href')
            divs = div.find_all('div')
            if divs:
                info_div = divs[2]
                if info_div:
                    age = info_div.text.split()[0]
                    city = info_div.text.split()[2]
            next_page = f"https://hitta.se{href}"
            response = requests.get(next_page, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            try:
                full_name = soup.find('h1', class_='heading--1').text
            except:
                pass
        else:
            full_name = div.text
    except:
        pass
    return (full_name, age, city)

def extract_phone_number(krafman_url, headers):
    response = requests.get(krafman_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    phone_number = None
    try:
        info_div = soup.find('div', class_='card card-login card-creditstart ccb s-third')
        if info_div:
            form_rows = info_div.find_all('div', class_='form-row')
            if form_rows and len(form_rows) >= 4:
                phone_div = form_rows[3]
                span = phone_div.find('span')
                if span:
                    phone_number = span.get_text()
    except:
        pass
    return phone_number

def transform_df(df, progress_bar, status_text):
    df.drop('CompanyLogo src', axis='columns', inplace=True)
    df.rename(columns= {'CompanyLink':'Företag', 'rt-td':'Omsättning',
                    'rt-td 2':'Resultat', 'CompanyLink href':'Bizzdo URL'}, inplace=True)

    vd_name_list = []
    webpage_list = []
    phone_list_bizzdo = []
    phone_list_hitta = []
    personal_phone_list = []

    for index, row in df.iterrows():
        # Update progress bar and status text
        progress = int((index + 1) / len(df) * 100)
        progress_bar.progress(progress)
        status_text.text(f"Processing row {index + 1} out of {len(df)}")

        company_name_query_1 = row['Företag'].replace(' ', '%20').replace('&', '%26').strip()
        company_name_query_2 = row['Företag'].lower().replace(' ', '+').strip()
        company_name_query_3 = format_for_krafman(row['Företag'])
        try:
            hitta_url = f"https://www.hitta.se/sök?vad={company_name_query_1}"

            # Go to the hitta_url, see if we can find a div with class section-header--meta
            # If we can , we are on the company page. If we can't, we give the url
            org_nr, webpage, buttonexists = attempt_to_extract_org_and_website_and_button_status(hitta_url, headers)
            if org_nr is None or webpage is None:
                webpage_list.append(hitta_url)
                vd_name_list.append(None)
                phone_list_hitta.append(None)
            else:
                webpage_list.append(webpage)  
                if buttonexists:
                    phone_list_hitta.append(hitta_url)
                else:
                    phone_list_hitta.append("Saknas på Hitta.se")
                try:      
                    beslutfattare_page = f"https://hitta.se/företagsinformation/{company_name_query_2}/{org_nr}#persons"
                    full_name, age, city = extract_full_name_age_and_city(beslutfattare_page, headers)
                    vd_name_list.append(full_name)
                except:
                    vd_name_list.append(f"https://proff.se/bransch-sök?q={company_name_query_1}")
        except:
            vd_name_list.append(None)
            webpage_list.append(None)
            phone_list_hitta.append(None)

        try:
            krafman_url = f"https://krafman.se/{company_name_query_3}/{org_nr}/sammanfattning"
            phone_number = extract_phone_number(krafman_url, headers)
            phone_list_bizzdo.append(phone_number)
        except:
            phone_list_bizzdo.append(None)

        if full_name:
            if age and city:
                personal_phone_list.append(f"https://mrkoll.se/resultat?n={full_name.lower().replace(' ', '+').strip()}&c={city}&min={age}&max={age}&sex=a&c_stat=all&company=")
            else:
                personal_phone_list.append(f"https://mrkoll.se/resultat?n={full_name.lower().replace(' ', '+').strip()}&c=&min=30&max=100&sex=a&c_stat=all&company=")
        else:
            personal_phone_list.append(None)

    df['Hemsida'] = pd.Series(webpage_list, index=df.index)
    df['VD Namn'] = pd.Series(vd_name_list, index=df.index)
    df['Företagsnummer (Bizzdo)'] = pd.Series(phone_list_bizzdo, index=df.index)
    df['Företagsnummer (Hitta.se)'] = pd.Series(phone_list_hitta, index=df.index)
    df['Personligt nummer'] = None
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