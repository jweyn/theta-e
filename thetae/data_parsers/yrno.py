#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve forecast data from yr.no.
"""

from thetae import Forecast
from thetae.util import to_float, c_to_f, ms_to_kt, mm_to_in
from datetime import timedelta
from dateutil.parser import parse as parse_iso
import requests
from xml.etree import cElementTree as eTree
import pandas as pd
from .nws import etree_to_dict

default_model_name = 'YRNO'


def get_yrno_forecast(stid, state, city, forecast_date):
    """
    Retrieve yr.no forecast for a city, state

    :param stid:
    :param state:
    :param city:
    :param forecast_date:
    :return:
    """
    yrno_url = 'https://www.yr.no/place/United_States/%s/%s/forecast_hour_by_hour.xml' % (state, city)
    response = requests.get(yrno_url)
    # Raise error for invalid HTTP response
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print('nws: got HTTP error when querying for XML file from %s' % yrno_url)
        raise

    # Get the XML tree into dictionary form
    hourly_xml = eTree.fromstring(response.text)
    hourly_dict = etree_to_dict(hourly_xml)
    hourly_list = hourly_dict['weatherdata']['forecast']['tabular']['time']
    timezone = hourly_dict['weatherdata']['location']['timezone']['@id']

    # Create a DataFrame for hourly data
    hourly = pd.DataFrame()
    hourly['DateTime'] = [v['@from'] for v in hourly_list]
    hourly['DateTime'] = hourly['DateTime'].apply(parse_iso).apply(lambda x: x.tz_localize(timezone))
    hourly['DateTime'] = hourly['DateTime'].apply(lambda x: x.astimezone('UTC').replace(tzinfo=None))
    hourly['datetime_index'] = hourly['DateTime']
    hourly.set_index('datetime_index', inplace=True)

    # Add in the other parameters
    hourly['temperature'] = [c_to_f(to_float(v['temperature']['@value'])) for v in hourly_list]
    hourly['windSpeed'] = [ms_to_kt(to_float(v['windSpeed']['@mps'])) for v in hourly_list]
    hourly['windDirection'] = [to_float(v['windDirection']['@deg']) for v in hourly_list]
    hourly['pressure'] = [to_float(v['pressure']['@value']) for v in hourly_list]
    hourly['condition'] = [v['symbol']['@name'] for v in hourly_list]
    hourly['rain'] = [mm_to_in(to_float(v['precipitation']['@value'])) for v in hourly_list]

    # Aggregate daily values from hourly series
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    hourly_high = hourly.loc[forecast_start:forecast_end, 'temperature'].max()
    hourly_low = hourly.loc[forecast_start:forecast_end, 'temperature'].min()
    hourly_wind = hourly.loc[forecast_start:forecast_end, 'windSpeed'].max()
    hourly_rain = hourly.loc[forecast_start:forecast_end - timedelta(hours=1), 'rain'].sum()

    # Create the Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.set_values(hourly_high, hourly_low, hourly_wind, hourly_rain)
    forecast.timeseries.data = hourly

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from NWS.
    """
    # Get the city and state from the config option 'long_name'
    try:
        long_name = config['Stations'][stid]['long_name']
    except KeyError:
        raise(KeyError("yrno: missing 'long_name' parameter for station %s" % stid))

    if ',' not in long_name:
        raise ValueError("yrno error: 'long_name' for station %s must be comma-delimited 'city, state'" % stid)

    try:
        city, state = long_name.split(',')
    except (IndexError, ValueError):
        raise ValueError("yrno error: could not parse 'long_name' for %s" % stid)

    city = '_'.join([s.lower().capitalize() for s in city.split()])
    state = '_'.join([s.lower().capitalize() for s in state.split()])

    # Get forecast
    forecast = get_yrno_forecast(stid, state, city, forecast_date)

    return forecast
