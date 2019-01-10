from datetime import datetime, date
from pathlib import Path

import config
import csv
import json
import requests

####################
# Define constants #
####################

API_KEY = config.API_KEY
BENCHMARKS = config.BENCHMARKS
CURRENCIES = config.CURRENCIES
URL = config.BASE_URL
STOCKS = config.STOCKS
TODAY = date.isoformat(date.today())

##################################################################################
# Converts a non-GBP stock's price to its GBP equivalent. Accepts the stock JSON #
# and relevant currency JSON as arguments, and outputs the converted stock JSON. #
##################################################################################

def converter(stock, forex):
    stock_dict = json.loads(stock)
    forex_dict = json.loads(forex)

    for key, val in stock_dict.items():
        stock_dict[key] = str(float(val) * float(forex_dict[key]))
    
    return json.dumps(stock_dict)

#######################################################################
# Converts JSON string to CSV. Accepts the JSON string, filename, and #  
# a list of headers as arguments, and creates the CSV file in 'csv/'. #
#######################################################################

def json_to_csv(json_str, filename, headers):
    parsed_json = json.loads(json_str)

    Path('csv/').mkdir(parents = True, exist_ok = True)
    with open('csv/' + filename + '.csv', 'w+') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(headers)

        for key, val in parsed_json.items():
            writer.writerow([key, val])

    return None

###############################
# Retrieve and clean datasets #
###############################

with requests.Session() as s:
    # Retrieve and clean benchmark datasets
    for benchmark in BENCHMARKS:
        payload = {
            'symbol': benchmark,
            'sort': 'oldest',
            'api_token': API_KEY,
            'date_from': '2018-06-29',
            'date_to': TODAY,
        }

        data = s.get(URL + 'history', params = payload)
        Path('json/benchmarks/').mkdir(parents = True, exist_ok = True)
        with open('json/benchmarks/' + benchmark + '.json', 'w+') as f:
            parsed_json = json.loads(data.text)
            for key, val in parsed_json['history'].items():
                parsed_json['history'][key] = val['close']
            f.write(json.dumps(parsed_json['history']))
    
    # Retrieve and clean stock datasets
    for ticker in STOCKS:
        payload = {
            'symbol': ticker,
            'sort': 'oldest',
            'api_token': API_KEY,
            'date_from': STOCKS[ticker]['date'],
            'date_to': TODAY,
            }
        
        data = s.get(URL + 'history', params = payload)
        Path('json/stocks/').mkdir(parents = True, exist_ok = True)
        with open('json/stocks/' + ticker + '.json', 'w+') as f:
            parsed_json = json.loads(data.text)
            for key, val in parsed_json['history'].items():
                parsed_json['history'][key] = val['close']
            f.write(json.dumps(parsed_json['history']))
    
    # Retrieve and clean currency datasets
    for currency in CURRENCIES:
        payload = {
            'base': currency,
            'convert_to': 'GBP',
            'api_token': API_KEY,
            'sort': 'oldest',
        }
        
        data = s.get(URL + 'forex_history', params = payload)

        Path('json/currencies/').mkdir(parents = True, exist_ok = True)
        with open('json/currencies/' + currency + 'GBP.json', 'w+') as f:
            parsed_json = json.loads(data.text)
            temp = {key: val for key, val in parsed_json['history'].items()}
            for key, val in parsed_json['history'].items():
                date_val = datetime.strptime(key, '%Y-%m-%d').date()
            if (date_val < date(2018, 1, 1)) or (5 <= date_val.weekday() <= 6):
                temp.pop(key)
            parsed_json['history'] = temp
            f.write(json.dumps(parsed_json['history']))

#################################################
# Convert non-GBP items into its GBP equivalent #
#################################################

for benchmark, info in BENCHMARKS.items():
    if info['curr'] == 'GBP':
        continue
    with open ('json/benchmarks/' + benchmark + '.json', 'r+') as index, open ('json/currencies/' + info['curr'] + 'GBP.json', 'r') as forex:
        converted = converter(index.read(), forex.read())
        index.seek(0)
        index.write(converted)
        index.truncate()

for ticker, info in STOCKS.items():
    if info['curr'] == 'GBP':
        continue
    with open ('json/stocks/' + ticker + '.json', 'r+') as stock, open ('json/currencies/' + info['curr'] + 'GBP.json', 'r') as forex:
        converted = converter(stock.read(), forex.read())
        stock.seek(0)
        stock.write(converted)
        stock.truncate()

#####################################################
# Get the value of our portfolio per stock (in GBP) #
#####################################################

for ticker, info in STOCKS.items():
    with open ('json/stocks/' + ticker + '.json', 'r+') as stock:
        stock_dict = json.loads(stock.read())

        for key, val in stock_dict.items():
            if info['curr'] == 'GBP':
                val = str(float(val) / 100)
            stock_dict[key] = str(float(val) * info['amount'])

        stock.seek(0)
        stock.write(json.dumps(stock_dict))
        stock.truncate()

###########################################
# Get the value of our portfolio (in GBP) #
###########################################

for index, ticker in enumerate(STOCKS):
    if index == 0:
        with open('json/processed.json', 'w') as processed:
            for line in open('json/stocks/' + ticker + '.json'):
                processed.write(line)
        continue

    with open('json/processed.json', 'r+') as processed, open('json/stocks/' + ticker + '.json', 'r') as stock:
        processed_dict = json.loads(processed.read())
        stock_dict = json.loads(stock.read())

        for key in processed_dict:
            try:
                processed_dict[key] = str(float(processed_dict[key]) + float(stock_dict[key]))
            except KeyError:
                pass    
        processed.seek(0)
        processed.write(json.dumps(processed_dict))
        processed.truncate()

#######################################################
# Convert data from JSON to CSV for use with amCharts #
#######################################################

with open('json/processed.json', 'r') as f:
    json_to_csv(f.read(), 'processed', ['date', 'value'])

for benchmark in BENCHMARKS:
    with open('json/benchmarks/' + benchmark + '.json', 'r') as f:
        json_to_csv(f.read(), benchmark, ['date', 'value'])

