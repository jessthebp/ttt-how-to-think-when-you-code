, keyword
import requests
from flask import Flask, render_template, request, Response
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

app = Flask(__name__)
run_with_ngrok(app)

# Custom exception handler decorator
def exception_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_code = getattr(e, "code", 500)
            error_message = str(e)
            response_data = {"message": error_message, "error_code": error_code}
            return Response(json.dumps(response_data), status=error_code, mimetype='application/json')
    wrapper.__name__ = func.__name__
    return wrapper


def fetch_connected_web_properties(creds):
    credentials = service_account.Credentials.from_service_account_file(creds, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
    webmasters_service = authorize_creds(creds)

    sites_response = webmasters_service.sites().list().execute()
    connected_properties = [site['siteUrl'] for site in sites_response.get('siteEntry', [])]
    return connected_properties


# Fetch search console data for a given web property
def fetch_search_console_data(property):
    creds = ''  # YOUR CRED LOCATION HERE

    def authorize_creds(creds):
        SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
        credentials = service_account.Credentials.from_service_account_file(creds, scopes=SCOPES)
        webmasters_service = build('searchconsole', 'v1', credentials=credentials)
        return webmasters_service

    def extract_data(site, creds):
        service = authorize_creds(creds)
        request = {
            'startDate': '2022-03-26',
            'endDate': '2023-03-26',
            'dimensions': ['query'],
            'rowLimit': 10
        }
        response = execute_request(service, site, request)
        data = response.get('rows', [])
        if not data:
            print('No data found.')
            return None
        df = pd.DataFrame(data)
        df.to_csv('/data.csv', index=False)
        return df

    def execute_request(service, property_uri, request):
        return service.searchanalytics().query(siteUrl=site, body=request).execute()

    site = '\'
    creds = ''
    df = extract_data(site, creds)
    df.sort_values('clicks', ascending=False)

    return df.to_dict(orient='records')  # Return data as a list of dictionaries

# Fetch related keywords data from SEMRush API
def fetch_related_keywords(keyword):
    print("fetching keywords")
    YOUR_SEMRUSH_API_KEY = ''  # Replace with your actual SEMRush API key

    def get_related_keywords(api_key, keyword):
        keywordsresponse = requests.get('https://api.semrush.com/?type=phrase_fullsearch&key={}&phrase={}&export_columns=Ph,&database=us&display_limit=10&display_sort=nq_desc&display_filter=%2B|Nq|Lt|1000'.format(api_key, keyword[0]))
        # handle 500 error:
        print(keywordsresponse)
        if keywordsresponse.status_code == 500:
            related_keywords = ['']
        if keywordsresponse.text.split('\n')[0] == 'ERROR 50 :: NOTHING FOUND':
           print("no related keywords found")
           related_keywords = ['']
           return related_keywords
        else:
            print(keywordsresponse.text.split('\n')[0:10])
            related_keywords = keywordsresponse.text.split('\n')
            # remove \r from keywords
            related_keywords = [keyword.replace('\r', '') for keyword in related_keywords]
            print(related_keywords)

        return related_keywords

    related_keywords_data = []
    related_keywords = get_related_keywords(YOUR_SEMRUSH_API_KEY, keyword)
    if related_keywords and related_keywords != 'ERROR 50 :: NOTHING FOUND' and related_keywords != 'ERROR 50 :: NOTHING FOUND':
        print(related_keywords)
        related_keywords_data.append(related_keywords)
    else:
        print("No related keywords found")
        related_keywords_data.append([''])
    print(related_keywords_data)
    print('finished getting keywords')
    return (related_keywords_data)

@app.route('/', methods=['GET', 'POST'])
@exception_handler
def dashboard():
    creds = ''  # YOUR CRED FILENAME HERE
    connected_properties = fetch_connected_web_properties(creds)
    if request.method == 'POST':
        selected_property = request.form['web_property']
        search_console_data = fetch_search_console_data(selected_property)
        print(search_console_data)
        print(search_console_data[0]['keys'])
        for i in search_console_data:
            print(i)
            #search_console_data[i]['related keywords'] = [keyword for keyword in fetch_related_keywords(i['keys'][0]) where keyword != '' and keyword !='Keyword']
            i['related_keywords'] = [keyword for keyword in fetch_related_keywords(i['keys']) if keyword != '' and keyword !='Keyword']

        connected_properties = fetch_connected_web_properties(creds)
        print(connected_properties)
        print(search_console_data)
        return render_template('dashboard.html', connected_properties=connected_properties, search_console_data=search_console_data)

    return render_template('dashboard.html', connected_properties=connected_properties)


if __name__ == '__main__':
    app.run()
