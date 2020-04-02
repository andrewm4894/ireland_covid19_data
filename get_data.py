#%%

from bs4 import BeautifulSoup, SoupStrainer
import requests
import pandas as pd
import re
import numpy as np

##%%

# define some helper functions

def get_press_release_links(
        base_url: str = 'https://www.gov.ie',
        page_url: str = '/en/news/7e0924-latest-updates-on-covid-19-coronavirus/') -> list:
    url = f'{base_url}{page_url}'
    page = requests.get(url)
    data = page.text
    soup = BeautifulSoup(data)

    links = []
    for link in soup.find_all('a'):
        link_href = link.get('href')
        if link_href:
            if '/en/press-release/' in link_href:
                if link_href[0:4] == '/en/':
                    links.append(f"{base_url}{link_href}")
                else:
                    links.append(link_href)
    return links

##%%

# get all press releases
press_release_links = get_press_release_links(page_url='/en/publication/ce3fe8-previous-updates-on-covid-19-coronavirus/')
press_release_links.extend(get_press_release_links(page_url='/en/news/7e0924-latest-updates-on-covid-19-coronavirus/'))
print(press_release_links)

##%%

# create some empty dataframes to collect data into
df_hospital_statistics = pd.DataFrame()
df_gender = pd.DataFrame()
df_age = pd.DataFrame()
df_spread = pd.DataFrame()
df_healthcare_workers = pd.DataFrame()
df_county = pd.DataFrame()
df_text = pd.DataFrame()

# loop over each press release, pull out tables and wrangle accordingly
for press_release_link in press_release_links:

    print(f"... getting tables from {press_release_link} ...")
    page = requests.get(press_release_link)
    data = page.text
    soup = BeautifulSoup(data)
    num_tables = len(soup.find_all('table'))

    # get published date from the press release
    published_search = re.search('Published:(.*)2020', data, re.IGNORECASE)
    if published_search:
        published_date = published_search.group(1).strip()
    else:
        published_date = ''
    date_cleaner = [
        ('March', '03'),
        ('April', '04'),
        ('May', '05'),
    ]
    for month_string, month_num in date_cleaner:
        if month_string in published_date:
            published_date = published_date.replace(month_string, '').strip()
            published_date = published_date.strip().zfill(2)
            published_date = f'2020-{month_num}-{published_date}'

    # get some metrics from the text
    patterns = [
        ('There are now (.*) confirmed cases of COVID-19 in Ireland', 'txt_cases'),
        ('There have now been (.*) COVID-19 related deaths in Ireland', 'txt_deaths'),
        ('informed of (.*) new confirmed cases', 'txt_new_cases'),
        ('To date, (.*) tests have been carried out', 'txt_tests'),
        ('today been informed that (.*) patients diagnosed with COVID-19 in Ireland have died', 'txt_new_deaths'),
        ('median age of today’s reported deaths is (.*)', 'txt_new_deaths_median_age'),
        ('median age of confirmed cases is (.*) years', 'txt_cases_median_age'),
        ('(.*) cases .* have been hospitalised', 'txt_cases_hospitalised'),
        ('cases (.*) have been hospitalised', 'txt_cases_hospitalised_pct'),
        ('of those hospitalised, (.*) cases have been admitted to ICU', 'txt_cases_admitted_icu'),
        ('(.*) cases are associated with healthcare workers', 'txt_cases_healthcare_workers'),
        ('(.*) cases \(.*%\) are associated with healthcare workers', 'txt_cases_healthcare_workers'),
        (' cases \((.*)\) are associated with healthcare workers', 'txt_cases_healthcare_workers_pct'),
        ('.*% are male and (.*) are female', 'txt_female_pct'),
        ('(.*) are male and .*% are female', 'txt_male_pct'),
        ('community transmission accounts for (.*), close contact accounts for .*%, travel abroad accounts for .*%',
         'txt_community_transmission_pct'),
        ('community transmission accounts for .*%, close contact accounts for (.*), travel abroad accounts for .*%',
         'txt_close_contact_pct'),
        ('community transmission accounts for .*%, close contact accounts for .*%, travel abroad accounts for (.*)',
         'txt_travel_abroad_pct'),
        ('Dublin has the highest number of cases at (.*) \(.* followed by Cork with .* cases .*%',
         'txt_cases_dublin'),
        ('Dublin has the highest number of cases at .* \((.*) of all cases\) followed by Cork with .* cases .*%',
         'txt_cases_dublin_pct'),
        ('Dublin has the highest number of cases at .* followed by Cork with (.*) cases .*%',
         'txt_cases_cork'),
        ('Dublin has the highest number of cases at .* followed by Cork with .* cases (.*)',
         'txt_cases_cork_pct'),
        ('with (.*) clusters involving .* cases', 'txt_clusters'),
        ('with .* clusters involving (.*) cases', 'txt_clusters_cases'),
        ('(.*) deaths located in the east of the country', 'txt_new_deaths_east'),
        ('(.*) deaths are located in the east of the country, .* in the northwest of the country and .* in the south',
         'txt_new_deaths_east'),
        (' deaths are located in the east of the country, (.*) in the northwest of the country and .* in the south',
         'txt_new_deaths_northwest'),
        (' deaths are located in the east of the country, .* in the northwest of the country and (.*) in the south',
         'txt_new_deaths_south'),
        ('(.*) deaths located in the east, .* in the south and .* in the west of the country',
         'txt_new_deaths_east'),
        (' deaths located in the east, (.*) in the south and .* in the west of the country',
         'txt_new_deaths_south'),
        (' deaths located in the east, .* in the south and (.*) in the west of the country',
         'txt_new_deaths_west'),
        ('have died. (.*) person in the north-west of the country and two females in the east',
         'txt_new_deaths_northwest'),
        ('One person in the north-west of the country and (.*) females in the east',
         'txt_new_deaths_east'),
        ('(.*) patients were based in the east of the country and 1 in the south.',
         'txt_new_deaths_east'),
        ('9 patients were based in the east of the country and (.*) in the south.',
         'txt_new_deaths_south'),
        ('(.*) deaths located in the east',
         'txt_new_deaths_east'),
        ('in the east, (.*) in the south',
         'txt_new_deaths_south'),
        ('(.*) patients were reported as having underlying health conditions',
         'txt_new_deaths_underlying'),
        ('patients included (.*) females and .* males',
         'txt_new_deaths_females'),
        ('patients included .* females and (.*) males',
         'txt_new_deaths_males'),
        ('The median age of deaths in Ireland is (.*).',
         'txt_deaths_median_age'),
        #('and (.*) in the west',
        # 'txt_new_deaths_west'),
    ]
    rubbish_strings = [
        ' ', 'anadditional', ',', '</li>', '<listyle="margin-left:15px;text-indent:-15px;">', '(', ')',
        'cases-25%of', 'themedianageofpatientsdiagnosedwithcovid-19whohavediedis79years.', 'ofthe712casesnotified',
        'ofthe584casesnotified', 'ofthe438casesnotified', 'ofthe350casesnotified', 'all', '8deathslocatedintheeast',
        '3inthesouth', '3inthenorth-westand', '6deathslocatedintheeast', '1inthesouthand', '6deathsarelocatedintheeastofthecountry3inthenorthwestofthecountryand'
    ]
    replacements = [
        ('ten', '10'),
        ('nine', '9'),
        ('eight', '8'),
        ('seven', '7'),
        ('six', '6'),
        ('five', '5'),
        ('four', '4'),
        ('three', '3'),
        ('two', '2'),
        ('one', '1'),
    ]
    for pattern, name in patterns:
        text = re.search(pattern, data, re.IGNORECASE)
        if text:
            value = text.group(1).lower()
            for to_replace, replace_with in replacements:
                value = value.replace(to_replace, replace_with)
            for rubbish_string in rubbish_strings:
                value = value.replace(rubbish_string, '')
            if '%' in value:
                value = float(value.replace('%', '')) / 100
            else:
                value = float(value.replace('%', ''))
            df_tmp = pd.DataFrame([[published_date, name, value, press_release_link]],
                                  columns=['published_date', 'variable', 'value', 'source'])
            df_text = df_text.append(df_tmp)
    df_text = df_text.drop_duplicates()

    # if tables found then try process them
    if num_tables > 0:

        print(f"... {num_tables} tables found ...")

        # read all tables into a list of data frames
        df_list = pd.read_html(press_release_link)

        #print(df_list)

        # add a tag to each df relating to what table it is from
        df_list_tagged = []

        # now process each data frame
        for df in df_list:

            #print(df)

            # make a big string of all the raw data to help in tagging it below
            raw_data = '|'.join([str(x).lower() for x in df.values.tolist()])

            # look for specific things in the raw data to determine what table we are dealing with
            if 'total number of cases' in raw_data:
                tag = 'hospital_statistics'
                df = df.rename({0: 'measure', 1: 'number', 2: 'pct'}, axis='columns')
            elif 'male' in raw_data:
                tag = 'gender'
                df = df.rename({0: 'gender', 1: 'number', 2: 'pct'}, axis='columns')
            elif 'community transmission' in raw_data:
                tag = 'spread'
                if df.shape[1] == 2:
                    df[2] = np.nan
                df = df.rename({0: 'measure', 1: 'number', 2: 'pct'}, axis='columns')
                df['pct'] = np.where(df['number'].astype(str).str.contains('%'), df['number'], df['pct'])
            elif 'travel related' in raw_data:
                tag = 'healthcare_workers'
                df = df.rename({0: 'measure', 1: 'number', 2: 'pct'}, axis='columns')
            elif 'dublin' in raw_data:
                tag = 'county'
                df = df.rename({0: 'county', 1: 'metric', 2: 'pct'}, axis='columns')
            elif ('age group' in raw_data) & ('<1' in raw_data):
                tag = 'age'
                df = df.rename({0: 'age', 1: 'number', 2: 'pct'}, axis='columns')
            elif ('<5' in raw_data) & ('65+' in raw_data):
                tag = 'age_hospital'
            else:
                tag = 'UNKNOWN'

            # clean up first col
            df[df.columns[0]] = df[df.columns[0]].str.lower()
            df[df.columns[0]] = df[df.columns[0]].str.replace(' of ', ' ')
            df[df.columns[0]] = df[df.columns[0]].str.replace(' to ', ' ')
            df[df.columns[0]] = df[df.columns[0]].str.replace('total ', '')
            df[df.columns[0]] = df[df.columns[0]].str.replace('number ', '')
            df[df.columns[0]] = df[df.columns[0]].str.replace('close ', '')
            df[df.columns[0]] = df[df.columns[0]].str.replace(' with ', ' ')
            df[df.columns[0]] = df[df.columns[0]].str.replace(' a ', ' ')
            df[df.columns[0]] = df[df.columns[0]].str.replace(' ', '_')

            #print(tag)

            # clean up data a bit
            if 'number' in df.columns:
                df = df[df['number'] != 'Number of people']
                df = df[df['number'] != 'Number']
                df = df[df['number'] != '% known']
                df['number'] = np.where(df['number'].astype(str).str.contains('%'), np.nan, df['number'])
                df['number'] = df['number'].astype(float)
            if 'pct' in df.columns:
                df = df[df['pct'] != '% of total']
                df['pct'] = df['pct'].astype(str).str.replace('%', '').astype(float) / 100
            if 'metric' in df.columns:
                df = df[df['metric'] != 'Number of cases']

            # add some metadata
            df['tag'] = tag
            df['published_date'] = published_date
            df['source'] = press_release_link
            df_list_tagged.append(df)
            #print(df_list_tagged)

        # break out df's and append to df specific for each table in the html
        for df in df_list_tagged:
            tag = df['tag'].unique()[0]
            if tag == 'hospital_statistics':
                df_hospital_statistics = df_hospital_statistics.append(df)
                df_hospital_statistics = df_hospital_statistics.dropna(how='all', axis=1)
            elif tag == 'gender':
                df_gender = df_gender.append(df)
                df_gender = df_gender.dropna(how='all', axis=1)
            elif tag == 'age':
                df_age = df_age.append(df)
                df_age = df_age.dropna(how='all', axis=1)
            elif tag == 'spread':
                df_spread = df_spread.append(df)
                df_spread = df_spread.dropna(how='all', axis=1)
            elif tag == 'healthcare_workers':
                df_healthcare_workers = df_healthcare_workers.append(df)
                df_healthcare_workers = df_healthcare_workers.dropna(how='all', axis=1)
            elif tag == 'county':
                df_county = df_county.append(df)
                df_county = df_county.dropna(how='all', axis=1)

    else:

        print("... no tables found ...")

##%%

# create a daily stats wide table
df_daily_stats = df_hospital_statistics.pivot(
    index='published_date', columns='measure', values=['number', 'pct']
).reset_index()
df_daily_stats.columns = ['_'.join(col).replace('number_', '').replace('published_date_', 'published_date') for col in df_daily_stats.columns]
df_spread_daily = df_spread.pivot(index='published_date', columns='measure', values=['number', 'pct']).reset_index()
df_spread_daily.columns = ['_'.join(col).replace('number_', '').replace('published_date_', 'published_date') for col in df_spread_daily.columns]
df_gender_daily = df_gender.pivot(index='published_date', columns='gender', values='number').reset_index()[['published_date', 'male', 'female']]
df_county_daily = df_county.pivot(index='published_date', columns='county', values='metric').reset_index()[['published_date', 'dublin', 'cork']]
df_age_daily = df_age.pivot(index='published_date', columns='age', values='number').reset_index()[['published_date', '65+']]
df_text_daily = df_text.pivot(index='published_date', columns='variable', values='value').reset_index()
df_text_daily['txt_growth_rate'] = df_text_daily['txt_new_cases'] / (df_text_daily['txt_cases'] - df_text_daily['txt_new_cases'])
df_tmp = df_healthcare_workers[['published_date', 'measure', 'number']].copy()
df_tmp['measure'] = 'health_worker_' + df_tmp['measure']
df_healthcare_workers_daily = df_tmp.pivot(index='published_date', columns='measure', values='number').reset_index()

# join other daily or wide tables
df_daily_stats = df_daily_stats.merge(df_spread_daily, 'outer', on='published_date')
df_daily_stats = df_daily_stats.merge(df_gender_daily, 'outer', on='published_date')
df_daily_stats = df_daily_stats.merge(df_county_daily, 'outer', on='published_date')
df_daily_stats = df_daily_stats.merge(df_text_daily, 'outer', on='published_date')
df_daily_stats = df_daily_stats.merge(df_age_daily, 'outer', on='published_date')
df_daily_stats = df_daily_stats.merge(df_healthcare_workers_daily, 'outer', on='published_date')

# add some more derived fields
df_daily_stats['cases_per_cluster'] = df_daily_stats['cases'] / df_daily_stats['clusters_notified']
df_daily_stats['pct_male'] = df_daily_stats['male'] / (df_daily_stats['male'] + df_daily_stats['female'])
df_daily_stats['pct_dublin'] = df_daily_stats['dublin'].astype(float) / df_daily_stats['cases']
df_daily_stats['pct_deaths'] = df_daily_stats['deaths'] / df_daily_stats['cases']
df_daily_stats['pct_community'] = df_daily_stats['community_transmission'] / df_daily_stats['cases']
df_daily_stats['pct_contact_confirmed'] = df_daily_stats['contact_confirmed_case'] / df_daily_stats['cases']
df_daily_stats['pct_travel_abroad'] = df_daily_stats['travel_abroad'] / df_daily_stats['cases']
df_daily_stats['pct_hospitalised'] = df_daily_stats['hospitalised'] / df_daily_stats['cases']
df_daily_stats['pct_icu'] = df_daily_stats['admitted_icu'] / df_daily_stats['cases']
df_daily_stats['pct_65+'] = df_daily_stats['65+'] / df_daily_stats['cases']
df_daily_stats['pct_test_positive'] = df_daily_stats['cases'] / df_daily_stats['txt_tests']
df_daily_stats['hospitalised_icu_rate'] = df_daily_stats['admitted_icu'] / df_daily_stats['hospitalised']
df_daily_stats['pct_health_workers'] = df_daily_stats['health_worker_total'] / df_daily_stats['cases']

# drop na cols
df_daily_stats = df_daily_stats.dropna(how='all', axis=1)

# make a long version of daily stats
df_daily_stats_long = df_daily_stats.melt(id_vars='published_date')

# ensure data sorted in csv files
df_hospital_statistics = df_hospital_statistics.sort_values(by=['published_date'])
df_gender = df_gender.sort_values(by=['published_date'])
df_gender_daily = df_gender_daily.sort_values(by=['published_date'])
df_age = df_age.sort_values(by=['published_date'])
df_age_daily = df_age_daily.sort_values(by=['published_date'])
df_spread = df_spread.sort_values(by=['published_date'])
df_spread_daily = df_spread_daily.sort_values(by=['published_date'])
df_healthcare_workers = df_healthcare_workers.sort_values(by=['published_date'])
df_healthcare_workers_daily = df_healthcare_workers_daily.sort_values(by=['published_date'])
df_county = df_county.sort_values(by=['published_date'])
df_county_daily = df_county_daily.sort_values(by=['published_date'])
df_text = df_text.sort_values(by=['published_date'])
df_text_daily = df_text_daily.sort_values(by=['published_date'])
df_daily_stats = df_daily_stats.sort_values(by=['published_date'])
df_daily_stats_long = df_daily_stats_long.sort_values(by=['published_date'])

# save as csv to data folder
df_hospital_statistics.to_csv('data/hospital_statistics.csv', index=False)
df_gender.to_csv('data/gender.csv', index=False)
df_gender_daily.to_csv('data/gender_daily.csv', index=False)
df_age.to_csv('data/age.csv', index=False)
df_age_daily.to_csv('data/age_daily.csv', index=False)
df_spread.to_csv('data/spread.csv', index=False)
df_spread_daily.to_csv('data/spread_daily.csv', index=False)
df_healthcare_workers.to_csv('data/healthcare_workers.csv', index=False)
df_healthcare_workers_daily.to_csv('data/healthcare_workers_daily.csv', index=False)
df_county.to_csv('data/county.csv', index=False)
df_county_daily.to_csv('data/county_daily.csv', index=False)
df_text.to_csv('data/text.csv', index=False)
df_text_daily.to_csv('data/text_daily.csv', index=False)
df_daily_stats.to_csv('data/daily_stats.csv', index=False)
df_daily_stats_long.to_csv('data/daily_stats_long.csv', index=False)

#%%

#%%