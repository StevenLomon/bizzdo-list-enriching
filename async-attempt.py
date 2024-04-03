import requests, time, re, asyncio, aiohttp
import pandas as pd
import streamlit as st
from rich import print
from bs4 import BeautifulSoup
from io import BytesIO

async def fetch(url, headers, sem, session):
    async with sem:
        async with session.get(url, headers=headers) as response:
            page_content = await response.text()
            return BeautifulSoup(page_content, 'html.parser')

async def construct_company_page(url, headers, sem, session):
    async with sem:
        soup = await fetch(url, headers, sem, session)
        page = None
        try:
            href = soup.find('a', class_="style_searchResultLink__2i2BY").get('href')
            page = f"https://hitta.se{href}"
        except:
            pass
        return page

async def extract_org_and_website_status(url, headers, sem, session):
    async with sem:
        soup = await fetch(url, headers, sem, session)
        org_nr = webpage = None
        try:
            org_nr = soup.find('p', class_="text-caption-md-regular color-text-placeholder").text.split()[1].replace('-', '')
        except:
            pass
        try:
            webpage_source = soup.find('a', attrs={'data-track':'homepage-detail-noncustomer'})
            webpage = webpage_source.get('href') if webpage_source else "Missing"
        except Exception:
            pass
        return (org_nr, webpage)

async def extract_age_city_and_personal_url(url, headers, sem, session):
    async with sem:
        soup = await fetch(url, headers, sem, session)
        age = city = next_page = None
        try:
            info = soup.find('div', class_='finance-persons__text-container').find_all('div')[2].text
            age = int(info.split(",")[0].split()[0])
            city = info.split(",")[1].strip()
            href = soup.find('a', attrs={'data-track':'show-person, Styrelsemedlemmar'}).get('href')
            next_page = f"https://hitta.se{href}"
        except:
            pass
        return (age, city, next_page)

async def extract_full_name(url, headers, sem, session):
    async with sem:
        soup = await fetch(url, headers, sem, session)
        h1 = None
        try:
            h1 = soup.find('h1', class_='heading--1').text
        except:
            pass
        return h1

async def process_row(index, row, headers, sem, session):
    company_name_query_1 = row['Företag'].replace(' ', '%20').strip()
    company_name_query_2 = row['Företag'].lower().replace(' ', '+').strip()
    hitta_url = f"https://www.hitta.se/s%C3%B6k?vad={company_name_query_1}"

    try:
        company_page = await construct_company_page(hitta_url, headers, sem, session)
        if not company_page:
            raise Exception("Company page not found")
        org_nr, webpage = await extract_org_and_website_status(company_page, headers, sem, session)
        office_phone_url = company_page

        if org_nr:
            beslutfattare_page = f"https://hitta.se/företagsinformation/{company_name_query_2}/{org_nr}#persons"
            age, city, personal_url = await extract_age_city_and_personal_url(beslutfattare_page, headers, sem, session)
            
            if personal_url:
                full_name = await extract_full_name(personal_url, headers, sem, session)
                fname, lname = (full_name.split() + [None, None])[:2]

            return {
                'webpage': webpage,
                'vd_fname': fname,
                'vd_lname': lname,
                'age': age,
                'city': city,
                'office_phone_url': office_phone_url,
                'personal_phone_url': f"https://mrkoll.se/resultat?n={fname}+{lname}&c={city}&min={age}&max={age}&sex=a&c_stat=all&company:" if fname and lname and city and age else None
            }
    except Exception as e:
        print(f"Error processing row: {e}")
        return None

async def transform_df_async(df, headers, semaphore_value=10):
    async with aiohttp.ClientSession() as session:
        sem = asyncio.Semaphore(semaphore_value)  # Adjust the concurrency level as needed
        tasks = [process_row(index, row, headers, sem, session) for index, row in df.iterrows()]
        results = await asyncio.gather(*tasks)

    # Convert the list of dicts (results) into a DataFrame
    results_df = pd.DataFrame(results)
    # Merge the original DataFrame with the results DataFrame
    new_df = pd.concat([df, results_df], axis=1)
    return new_df

def transform_df(df):
    headers = ({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36', 
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.hitta.se/',
            'DNT': '1',})
    
    df.rename(columns= {'CompanyLink':'Företag', 'LabeledText__text':'Omsättning', 
                            'LabeledText__text 2':'Resultat', 'CompanyLink href':'Bizzdo URL'}, inplace=True)

    # Run the async transform
    new_df = asyncio.run(transform_df_async(df, headers))
    return new_df

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
            print("Running...")
            start_time = time.time()
            df = pd.read_csv(uploaded_file)
            total_number_of_rows = len(df)
            st.write(f"About to process {total_number_of_rows} rows")
            df_transformed = transform_df(df)
            end_time = time.time()
            st.text(f"Done! Processed {total_number_of_rows} in {end_time - start_time} seconds")
            with open ("times.txt", "a") as f:
                f.write(f"Total: {total_number_of_rows}, Time: {end_time - start_time}\n")


            csv = generate_csv(df_transformed, result_name)
            with open(csv, "rb") as file:
                st.download_button(label="Download enriched list as csv", data=file, file_name=csv, mime='text/csv')
    else:
        st.error("There was an error handling the uploaded csv. Please try again")
    
# def transform_df(df):
#     df.rename(columns= {'CompanyLink':'Företag', 'LabeledText__text':'Omsättning', 
#                         'LabeledText__text 2':'Resultat', 'CompanyLink href':'Bizzdo URL'}, inplace=True)

#     webpage_list = []
#     vd_fname_list = []
#     vd_lname_list = []
#     age_list = []
#     city_list = []
#     office_phone_list = []
#     personal_phone_list = []

#     for index, row in df.iterrows():
#         print(f"Processing row #{index}")
#         company_name_query_1 = row['Företag'].replace(' ', '%20').strip()
#         company_name_query_2 = row['Företag'].lower().replace(' ', '+').strip()
#         hitta_url = f"https://www.hitta.se/s%C3%B6k?vad={company_name_query_1}"
#         office_phone_url = org_nr = webpage = None
#         try:
#             org_nr, webpage = extract_org_and_website_status(hitta_url, headers)
#             office_phone_url = hitta_url
#         except:
#             company_page = construct_company_page(hitta_url, headers)
#             if company_page:
#                 org_nr, webpage = extract_org_and_website_status(company_page, headers)
#                 office_phone_url = company_page
#         if org_nr:
#             beslutfattare_page = f"https://hitta.se/företagsinformation/{company_name_query_2}/{org_nr}#persons"
#             age, city, personal_url = extract_age_city_and_personal_url(beslutfattare_page, headers)
#             fname = lname = None
#             if personal_url:
#                 full_name = extract_full_name(personal_url, headers)
#                 try:
#                     fname, lname = full_name.split()
#                 except:
#                     pass

#         webpage_list.append(webpage)
#         vd_fname_list.append(fname)
#         vd_lname_list.append(lname)
#         age_list.append(age)
#         city_list.append(city)
#         office_phone_list.append(office_phone_url)
#         personal_phone_url = None
#         if fname and lname and city and age:
#             personal_phone_url = f"https://mrkoll.se/resultat?n={fname}+{lname}&c={city}&min={age}&max={age}&sex=a&c_stat=all&company="
#         personal_phone_list.append(personal_phone_url)

#     df['Hemsida'] = pd.Series(webpage_list, index=df.index)
#     df['VD Tilltalsnamn'] = pd.Series(vd_fname_list, index=df.index)
#     df['VD Efternamn'] = pd.Series(vd_lname_list, index=df.index)
#     df['VD Ålder'] = pd.Series(age_list, index=df.index)
#     df['VD Stad'] = pd.Series(city_list, index=df.index)
#     df['Få kontorsnummer från'] = pd.Series(office_phone_list, index=df.index)
#     df['Få personligt nummer från'] = pd.Series(personal_phone_list, index=df.index)

#     return df