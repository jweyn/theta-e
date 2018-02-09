#
# Copyright (c) 2017-18 Jonathan Weyn & Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve UKMET data

Currently only handles daily high and low
To do: add wind and hourly data
"""

from thetae import Forecast
from datetime import datetime, timedelta
import urllib2
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from thetae.util import c_to_f, mph_to_kt, wind_dir_to_deg
import pdb

default_model_name = 'UKMET'

#needs ukmet code
def get_ukmet_forecast(stid, ukmet_code, init_date, forecast_date):
    """
    Retrieve UKMET data. 

    :param init_date: datetime of model initialization
    :return: dict of high, low, max wind for next 6Z--6Z. No precip.
    
    """
    # Create forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)

    #Header that is needed for urllib2 to work properly
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

    # Retrieve the model data
    url = 'https://www.metoffice.gov.uk/public/weather/forecast/%s' % ukmet_code
    req = urllib2.Request(url,headers=hdr) 
    response = urllib2.urlopen(req)
    page = response.read().decode('utf-8','ignore')
    soup = BeautifulSoup(page,'lxml')

    # Find utc offset and current time in HTML
    utcoffset = int(soup.find(id='country').text.split('-')[1][0:2])
    epoch = float(soup.find("td", { "id" : "firstTimeStep" })['data-epoch'])
    utcnow = datetime.utcfromtimestamp(epoch)

    #store daily variables 
    days = []
    highs = []
    lows = []
    wspds = []

    #First part: li tages for "tabDay1, tabDay2" (tomorrow, next day high and low)
    tabids = ['tabDay1','tabDay2','tabDay3','tabDay4']
    for ids in tabids:
        pars = soup.find(id=ids)
        days.append(datetime.strptime(pars['data-date'],'%Y-%m-%d')) 
        highs.append(c_to_f(pars.findAll("span", { "title" : "Maximum daytime temperature" })[0]['data-value-raw']))
        lows.append(c_to_f(pars.findAll("span", { "title" : "Minimum nighttime temperature" })[0]['data-value-raw']))

    #Make list of forecast objects
    forecast = []

    for i in range(0,len(days)):
        forecast_tmp = Forecast(stid, default_model_name, days[i])
        forecast_tmp.daily.date = days[i]
        forecast_tmp.daily.high = highs[i]
        forecast_tmp.daily.low = lows[i]
        forecast.append(forecast_tmp)

    return forecast[0]


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from UKMET data.
    """

    # Get the ukmet code from the config
    try:
        ukmet_code = config['Stations'][stid]['ukmet_code']
    except KeyError:
        raise KeyError('ukmet.py: no ukmet parameter defined for stid %s in config!' % stid)

    # Init date, determined from current time.

    time_now = datetime.utcnow()
    if time_now.hour >= 16:
        init_date = forecast_date - timedelta(hours=12)
    else:
        init_date = forecast_date - timedelta(hours=24)

    # Get forecast
    forecast = get_ukmet_forecast(stid, ukmet_code, init_date, forecast_date)

    return forecast


