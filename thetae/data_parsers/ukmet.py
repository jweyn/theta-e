#
# Copyright (c) 2017-18 Jonathan Weyn & Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve UKMET data

Daily: high, low, wind speed
Hourly: temp, dewpt, wind speed, wind gust, wind direction
"""

from thetae import Forecast
from datetime import datetime, timedelta
import urllib2
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from thetae.util import get_codes, c_to_f, mph_to_kt, wind_dir_to_deg, dewpoint_from_t_rh
from selenium import webdriver 

default_model_name = 'UKMET'


# needs ukmet code
def get_ukmet_forecast(stid, ukmet_code, init_date, forecast_date):
    """
    Retrieve UKMET data. 

    :param stid:
    :param ukmet_code:
    :param forecast_date:
    :param init_date: datetime of model initialization
    :return: dict of high, low, max wind for next 6Z--6Z. No precip.
    """
    # Create forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)

    # Header that is needed for urllib2 to work properly
    hdr = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 '
                      'Safari/537.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'
    }

    # Retrieve the model data
    url = 'https://www.metoffice.gov.uk/public/weather/forecast/%s' % ukmet_code
    req = urllib2.Request(url, headers=hdr)
    response = urllib2.urlopen(req)
    page = response.read().decode('utf-8', 'ignore')
    soup = BeautifulSoup(page, 'lxml')

    # Find UTC offset and current time in HTML
    utcoffset = int(soup.find(id='country').text.split('-')[1][0:2])
    epoch = float(soup.find("td", {"id": "firstTimeStep"})['data-epoch'])
    utcnow = datetime.utcfromtimestamp(epoch)

    # Store daily variables 
    days = []
    highs = []  # this can be overwritten by hourly
    lows = []  # this can be overwritten by hourly
    winds = []  # this comes from hourly

    # Pull in daily data using li tabs
    tabids = ['tabDay1', 'tabDay2', 'tabDay3']
    for ids in tabids:
        pars = soup.find(id=ids)
        days.append(datetime.strptime(pars['data-date'], '%Y-%m-%d')) 
        highs.append(c_to_f(pars.findAll("span", {"title": "Maximum daytime temperature"})[0]['data-value-raw']))
        lows.append(c_to_f(pars.findAll("span", {"title": "Minimum nighttime temperature"})[0]['data-value-raw']))

    # Pull in hourly data
    # This requires PhantomJS to pull out additional HTML code
    driver = webdriver.PhantomJS(executable_path='/home/disk/p/wxchallenge/bin/phantomjs')
    driver.get(url + '#?date=2017-09-21')
    source = driver.page_source
    soup = BeautifulSoup(source, 'html.parser')

    dateTime = []
    temperature = []
    temperature_c = []
    dewpoint = []
    windSpeed = []
    windGust = []
    windDirection = []
    humidity = []  # this is temporary--converted to dew point below

    divids = ['divDayModule0', 'divDayModule1', 'divDayModule2', 'divDayModule3']
    for i, divs in enumerate(divids):
        day0 = datetime.strptime(soup.find("div", {"id": "divDayModule0"})['data-content-id'], '%Y-%m-%d')
        day1 = (day0+timedelta(days=1)).strftime('%Y-%m-%d')
        pars = soup.find(id=divs)
        divdate = datetime.strptime(pars['data-content-id'], '%Y-%m-%d').date()
        hourels = pars.findAll("tr", {"class": "weatherTime"})[0].find_all('td')
        for ii, ele in enumerate(hourels):
            if ele.text == 'Now':
                dateTime.append(utcnow)
            else:
                dtmp = datetime(divdate.year, divdate.month, divdate.day, int(ele.text.split(':')[0]),
                                int(ele.text.split(':')[1]))
                dateTime.append(dtmp + timedelta(hours=utcoffset))
        tempels = pars.findAll("tr", {"class": "weatherTemp"})[0].findAll("i", {"class": "icon icon-animated"})
        for ele in tempels:
            temperature_c.append(float(ele['data-value-raw']))
            temperature.append(c_to_f(ele['data-value-raw']))
        # relative humidity for conversion to dew point
        humels = pars.findAll("tr", {"class": "weatherHumidity"})[0].text.split() 
        for ele in humels:
            humidity.append(float(ele.split('%')[0]))
        # add wind 
        speedels = pars.findAll("i", {"data-type": "windSpeed"})  
        for ele in speedels:
            windSpeed.append(np.round(mph_to_kt(ele['data-value-raw']), 2))
        gustels = pars.findAll("span", {"class": "gust"})  
        for ele in gustels:
            windGust.append(mph_to_kt(ele['data-value-raw']))
        direls = pars.findAll("span", {"class": "direction"})  
        for ele in direls:
            windDirection.append(wind_dir_to_deg(ele.text))

    # Convert T and humidity to dewpt
    for ii, rh in enumerate(humidity):
        td_tmp = dewpoint_from_t_rh(temperature_c[ii], rh)
        dewpoint.append(c_to_f(td_tmp))

    # Make into dataframe
    df = pd.DataFrame({
        'temperature': temperature,
        'dewpoint': dewpoint,
        'windSpeed': windSpeed,
        'windGust': windGust,
        'windDirection': windDirection,
        'dateTime': dateTime
    }, index=dateTime)

    # Correct the highs and lows with the hourly data, find max wind speed
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    for d in range(0, len(days)):
        try:
            # unlike the mos code, we always use the 'include'
            iloc_start_include = df.index.get_loc(forecast_start)
        except BaseException:
            print('Error getting start time index in db; check data.')
            break
        try:
            iloc_end = df.index.get_loc(forecast_end)
        except BaseException:
            print('Error getting end time index in db; check data.')
            break
        raw_high = df.iloc[iloc_start_include:iloc_end]['temperature'].max()
        raw_low = df.iloc[iloc_start_include:iloc_end]['temperature'].min()
        winds.append(int(np.round(df.iloc[iloc_start_include:iloc_end]['windSpeed'].max())))
        if raw_high > highs[d]:
            highs[d] = raw_high
        if raw_low < lows[d]:
            lows[d] = raw_low
        forecast_start = forecast_start + timedelta(days=1)
        forecast_end = forecast_end + timedelta(days=1)

    forecast = Forecast(stid, default_model_name, days[0])        
    forecast.timeseries.data = df
    forecast.daily.high = highs[0]
    forecast.daily.low = lows[0]
    forecast.daily.wind = winds[0]

    # # Make list of forecast objects for future days--currently not implemented
    #
    # forecast = []
    #
    # for i in range(0,len(days)):
    #     forecast_tmp = Forecast(stid, default_model_name, days[i])
    #     forecast_tmp.daily.date = days[i]
    #     forecast_tmp.daily.high = highs[i]
    #     forecast_tmp.daily.low = lows[i]
    #     forecast.append(forecast_tmp)

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from UKMET data.
    """

    # Get the codes file from config and the specific codes for stid
    try:
        ukmet_codes_file = config['Models'][model]['codes_file']
    except KeyError:
        raise KeyError('ukmet.py: no codes file specified for model %s in config!' % model)
    try:
        ukmet_code = get_codes(ukmet_codes_file, stid)
    except BaseException as e:
        print("'ukmet.py: can't find code in %s for site %s!" % (ukmet_codes_file, stid))
        raise

    # Init date, determined from current time
    time_now = datetime.utcnow()
    if time_now.hour >= 16:
        init_date = forecast_date - timedelta(hours=12)
    else:
        init_date = forecast_date - timedelta(hours=24)

    # Get forecast
    forecast = get_ukmet_forecast(stid, ukmet_code, init_date, forecast_date)

    return forecast


