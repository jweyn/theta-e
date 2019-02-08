#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve NWS forecast data.
"""

from thetae import Forecast
from thetae.util import to_float, localized_date_to_utc, mph_to_kt
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_iso
import requests
from collections import defaultdict
from xml.etree import cElementTree as eTree
import pandas as pd
import numpy as np
import re
from builtins import str

default_model_name = 'NWS'


def etree_to_dict(t):
    """
    Convert an XML tree to a dictionary, courtesy of @K3---rnc (StackOverflow)
    """
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def xml_to_values(l):
    """
    Return a list of values from a list of XML data potentially including null values.
    """
    new = []
    for element in l:
        if isinstance(element, dict):
            new.append(None)
        else:
            new.append(to_float(element))
    return new


def xml_to_condition(l):
    """
    Returns a list of values from a list of 'weather-condition' XML data.
    """
    new = []
    for element in l:
        if isinstance(element, dict):
            key = list(element.keys())[0]
            if key.endswith('nil'):
                new.append(None)
            elif key == 'value':
                if isinstance(element[key], list):
                    new.append(','.join([t['@weather-type'] for t in element[key]]))
                elif isinstance(element[key], dict):
                    new.append(element[key]['@weather-type'])
                else:
                    new.append(str(element[key])[:20])
            else:
                new.append(None)
        else:
            try:
                new.append(str(element)[:20])
            except:
                new.append(None)
    return new


def wind_speed_interpreter(wind):
    """
    Interprets NWS wind speed to return the maximum.
    """
    pattern = re.compile(r'(\d{1,3})')
    try:
        new_wind = float(pattern.findall(wind)[-1])
    except:
        new_wind = np.nan
    return new_wind


def get_nws_forecast(config, stid, lat, lon, forecast_date):
    """
    Retrieve current NWS forecast for a point location.

    :param config:
    :param stid: str: station ID
    :param lat: float: latitude
    :param lon: float: longitude
    :param forecast_date: datetime:
    :return:
    """
    hourly_url = 'http://forecast.weather.gov/MapClick.php?lat=%f&lon=%f&FcstType=digitalDWML'
    response = requests.get(hourly_url % (lat, lon))
    hourly_xml = eTree.fromstring(response.text)
    hourly_dict = etree_to_dict(hourly_xml)

    # Create a DataFrame for hourly data
    hourly = pd.DataFrame()
    hourly['DateTime'] = hourly_dict['dwml']['data']['time-layout']['start-valid-time']
    # De-localize the starting time so we can do an explicit datetime comparison
    hourly['DateTime'] = [localized_date_to_utc(parse_iso(hourly['DateTime'].iloc[j])) for j in
                          range(len(hourly['DateTime']))]
    hourly['DateTime'] = [hourly['DateTime'].iloc[j].to_pydatetime().replace(tzinfo=None) for j in
                          range(len(hourly['DateTime']))]
    hourly['datetime_index'] = hourly['DateTime']
    hourly.set_index('datetime_index', inplace=True)
    parameters = hourly_dict['dwml']['data']['parameters']

    # Get the temperatures
    for element in parameters['temperature']:
        if element['@type'] == 'hourly':
            hourly['temperature'] = xml_to_values(element['value'])
        elif element['@type'] == 'dew point':
            hourly['dewPoint'] = xml_to_values(element['value'])
    # Get the winds
    for element in parameters['wind-speed']:
        if element['@type'] == 'sustained':
            hourly['windSpeed'] = xml_to_values(element['value'])
            hourly['windSpeed'] = mph_to_kt(hourly['windSpeed'])
        elif element['@type'] == 'gust':
            hourly['windGust'] = xml_to_values(element['value'])
            hourly['windGust'] = mph_to_kt(hourly['windGust'])
    # Get other parameters
    hourly['cloud'] = xml_to_values(parameters['cloud-amount']['value'])
    hourly['windDirection'] = xml_to_values(parameters['direction']['value'])
    hourly['rain'] = xml_to_values(parameters['hourly-qpf']['value'])
    try:
        hourly['condition'] = xml_to_condition(parameters['weather']['weather-conditions'])
    except:
        pass

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

    # Now do the daily data from the Forecast API
    api_url = 'https://api.weather.gov/points'
    point = '%0.3f,%0.3f' % (lat, lon)
    # Retrieve daily forecast
    daily_url = '%s/%s/forecast' % (api_url, point)
    response = requests.get(daily_url)
    # Test for an error HTTP response. If there is an error response, omit the daily part.
    try:
        response.raise_for_status()
        daily_data = response.json()
    except BaseException as e:
        if config['debug'] > 0:
            print("nws: warning: no daily values used for %s ('%s')" % (stid, str(e)))
        return forecast

    # Daily values: convert to DataFrame
    daily = pd.DataFrame.from_dict(daily_data['properties']['periods'])
    # Change the wind to its max value
    daily['windSpeed'] = daily['windSpeed'].apply(wind_speed_interpreter)
    # De-localize the starting time so we can do an explicit datetime comparison
    daily['startTime'] = [parse_iso(daily['startTime'].iloc[j]) for j in range(len(daily['startTime']))]
    daily['startTime'] = [daily['startTime'].iloc[j].replace(tzinfo=None) for j in range(len(daily['startTime']))]
    daily.set_index('startTime', inplace=True)
    try:
        daily_high = daily.loc[forecast_date + timedelta(hours=6), 'temperature']
    except KeyError:
        daily_high = np.nan
    try:
        daily_low = daily.loc[forecast_date - timedelta(hours=6), 'temperature']
    except KeyError:
        daily_low = np.nan
    daily_wind = mph_to_kt(np.max(daily.loc[forecast_start:forecast_end]['windSpeed']))

    # Update the Forecast object
    forecast.daily.set_values(np.nanmax([hourly_high, daily_high]), np.nanmin([hourly_low, daily_low]),
                              np.nanmax([hourly_wind, daily_wind]), hourly_rain)

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from NWS.
    """
    # Get latitude and longitude from the config
    try:
        lat = float(config['Stations'][stid]['latitude'])
        lon = float(config['Stations'][stid]['longitude'])
    except KeyError:
        raise(KeyError('nws: missing or invalid latitude or longitude for station %s' % stid))

    # Get forecast
    forecast = get_nws_forecast(config, stid, lat, lon, forecast_date)

    return forecast
