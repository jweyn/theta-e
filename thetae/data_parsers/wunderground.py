#
# Copyright (c) 2017-18 Thomas Lamb <lambt@uw.edu>
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

default_model_name = 'Weather Underground'


# Helper methods

def convert_fcttime(fcttime_series, timezone):
    """
    Convert API's FCTTIME from epoch time to UTC time
    """
    new_fcttime_series = fcttime_series.copy()
    for j in range(len(fcttime_series)):
        new_fcttime_series.iloc[j] = int(fcttime_series.iloc[j]['epoch'])
        new_fcttime_series.iloc[j] = epoch_time_to_datetime(new_fcttime_series.iloc[j], timezone)
    return new_fcttime_series


def get_english_units(series):
    """
    Gets the english units from dicts containing multiple units and converts to float values
    """
    new_series = series.copy()
    for j in range(len(series)):
        try:
            new_series.iloc[j] = float(series.iloc[j]['english'])
        except (TypeError,KeyError):
            try:
                new_series.iloc[j] = float(series.iloc[j])
            except:
                pass
            pass
    return new_series


def get_wind_degrees(series):
    """
    Returns the wind direction in degrees from a dict containing degrees and direction
    """
    new_series = series.copy()
    for j in range(len(series)):
        try:
            new_series.iloc[j] = float(series.iloc[j]['degrees'])
        except (TypeError, KeyError):
            pass
    return new_series


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
    wunderground_df = pd.DataFrame(wunderground_data['hourly_forecast'])

    # get timezone information
    timezone_df = pd.DataFrame(wunderground_data['forecast']['simpleforecast'])
    timezone = get_timezone(timezone_df['forecastday'])
    time_series = convert_fcttime(wunderground_df['FCTTIME'], timezone)

    for column in wunderground_df.columns.values:
        wunderground_df[column] = get_english_units(wunderground_df[column])
    wunderground_df['mslp'] = inhg_to_mb(wunderground_df['mslp'])
    wunderground_df['wspd'] = mph_to_kt(wunderground_df['wspd'])
    wunderground_df['wdir'] = get_wind_degrees(wunderground_df['wdir'])

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
    forecast.daily.setValues(daily_high, daily_low, daily_wind, daily_rain)
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
