#
# Copyright (c) 2017-19 Thomas Lamb <lambt@uw.edu> and Jonathan Weyn
#
# See the file LICENSE for your rights.
#

"""
Retrieve Weather Underground forecast data.
"""

from thetae import Forecast
from thetae.util import epoch_time_to_datetime, mph_to_kt, inhg_to_mb
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np

default_model_name = 'Weather Underground'


# Helper methods

def convert_fcttime(fcttime_series, timezone=None):
    """
    Convert API's FCTTIME from epoch time to UTC time
    """
    new_fcttime_series = fcttime_series.copy()
    for j in range(len(fcttime_series)):
        new_fcttime_series.iloc[j] = int(fcttime_series.iloc[j]['epoch'])
        new_fcttime_series.iloc[j] = epoch_time_to_datetime(new_fcttime_series.iloc[j], timezone)
    return new_fcttime_series


def get_english_units(value):
    """
    Gets the english units from dicts containing multiple units and converts to float values
    """
    try:
        new_value = float(value['english'])
    except (TypeError, KeyError):
        try:
            new_value = float(value)
        except (TypeError, ValueError):
            return value
    return new_value


def get_wind_degrees(value):
    """
    Returns the wind direction in degrees from a dict containing degrees and direction
    """
    try:
        new_value = float(value['degrees'])
    except (TypeError, KeyError):
        return value
    return new_value


def get_timezone(series):
    """
    Return the timezone for the station of interest
    """
    new_series = series.copy()
    new_date = new_series[0]
    timezone = new_date['date']['tz_long']
    return timezone


def get_wunderground_forecast(stid, api_key, forecast_date):

    # retrieve api json data
    api_url = 'https://api.wunderground.com/api/%s/hourly/forecast/q/%s.json'
    api_options = {'features': 'hourly,forecast'}
    json_url = api_url % (api_key, stid)
    response = requests.get(json_url, params=api_options)
    wunderground_data = response.json()
    # Raise error for invalid HTTP response
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print('wunderground: got HTTP error when querying API')
        raise

    # Convert to DataFrame, fix time
    wunderground_df = pd.DataFrame(wunderground_data['hourly_forecast'])
    timezone_df = pd.DataFrame(wunderground_data['forecast']['simpleforecast'])
    timezone = get_timezone(timezone_df['forecastday'])
    time_series = convert_fcttime(wunderground_df['FCTTIME'])  # already UTC

    for column in wunderground_df.columns.values:
        wunderground_df[column] = wunderground_df[column].apply(get_english_units)
    wunderground_df['mslp'] = inhg_to_mb(wunderground_df['mslp'])
    wunderground_df['wspd'] = mph_to_kt(wunderground_df['wspd'])
    wunderground_df['wdir'] = wunderground_df['wdir'].apply(get_wind_degrees)

    column_names_dict = {
          'FCTTIME': 'DateTime',
          'temp': 'temperature',
          'wspd': 'windSpeed',
          'mslp': 'pressure',
          'sky': 'cloud',
          'dewpoint': 'dewpoint',
          'qpf': 'rain',
          'wdir': 'windDirection',
          'wx': 'condition'
    }
    wunderground_df.drop('condition', axis=1, inplace=True)
    wunderground_df = wunderground_df.rename(columns=column_names_dict)
    wunderground_df['DateTime'] = time_series
    wunderground_df.set_index('DateTime', inplace=True)

    # calculate daily values
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    daily_high = wunderground_df.loc[forecast_start:forecast_end, 'temperature'].max()
    daily_low = wunderground_df.loc[forecast_start:forecast_end, 'temperature'].min()
    daily_wind = wunderground_df.loc[forecast_start:forecast_end, 'windSpeed'].max()
    daily_rain = wunderground_df.loc[forecast_start:forecast_end - timedelta(hours=1), 'rain'].sum()

    # create Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.set_values(daily_high, daily_low, daily_wind, daily_rain)
    forecast.timeseries.data = wunderground_df.reset_index()

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from Weather Underground.
    """
    # Get the API key from the config
    try:
        api_key = config['Models'][model]['api_key']
    except KeyError:
        raise KeyError('wunderground.py: no api_key parameter defined for model %s in config!' % model)

    # Get forecast
    forecast = get_wunderground_forecast(stid, api_key, forecast_date)

    return forecast
