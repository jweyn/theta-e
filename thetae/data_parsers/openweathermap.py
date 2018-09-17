#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve OpenWeatherMap forecast data.
"""

from thetae import Forecast
from thetae.util import date_to_datetime, mm_to_in, mph_to_kt, dewpoint_from_t_rh
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np

default_model_name = 'OpenWeatherMap'


def get_parameter(value, param, is_list=False):
    """
    Get a specific parameter from a dictionary-valued Series element.

    :param value: element of Series
    :param param: str: desired parameter
    :param is_list: bool: if True, 'value' is interpreted as a list
    :return: new_value: desired value for parameter in element
    """
    try:
        if is_list:
            new_value = value[0][param]
        else:
            new_value = value[param]
    except (TypeError, KeyError, ValueError):
        new_value = np.nan
    return new_value


def get_owm_forecast(stid, lat, lon, api_key, forecast_date):

    # Retrieve data
    api_url = 'http://api.openweathermap.org/data/2.5/forecast'
    api_options = {
        'APPID': api_key,
        'lat': lat,
        'lon': lon,
        'units': 'imperial',
    }
    response = requests.get(api_url, params=api_options)
    owm_data = response.json()
    # Raise error for invalid HTTP response
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print('openweathermap: got HTTP error when querying API')
        raise

    # Convert to pandas DataFrame and fix time
    owm_df = pd.DataFrame(owm_data['list'])
    owm_df['DateTime'] = np.nan
    for idx in owm_df.index:
        owm_df.loc[idx, 'DateTime'] = date_to_datetime(owm_df.loc[idx, 'dt_txt'])
    owm_df.set_index('DateTime', inplace=True)

    # OWM has a column 'main' which contains some parameters at all times. Get all of those.
    for parameter in owm_df.loc[owm_df.index[0], 'main'].keys():
        owm_df[parameter] = owm_df['main'].apply(get_parameter, args=(parameter,))

    # Get some other special parameters
    # Make sure the 'rain' parameter exists (if no rain in forecast, the column is missing)
    if 'rain' not in owm_df:
        owm_df = owm_df.assign(**{'rain': 0.0})
    else:
        owm_df.loc[:, 'rain'] = mm_to_in(owm_df['rain'].apply(get_parameter, args=('3h',)))
    owm_df['condition'] = owm_df['weather'].apply(get_parameter, args=('description',), is_list=True)
    owm_df['windSpeed'] = mph_to_kt(owm_df['wind'].apply(get_parameter, args=('speed',)))
    owm_df['windDirection'] = owm_df['wind'].apply(get_parameter, args=('deg',))
    owm_df['cloud'] = owm_df['clouds'].apply(get_parameter, args=('all',))
    owm_df['dewpoint'] = np.nan
    for idx in owm_df.index:
        owm_df.loc[idx, 'dewpoint'] = dewpoint_from_t_rh(owm_df.loc[idx, 'temp'], owm_df.loc[idx, 'humidity'])

    # Rename remaining columns for default schema
    column_names_dict = {
        'temp': 'temperature',
    }
    owm_df = owm_df.rename(columns=column_names_dict)

    # Calculate daily values. OWM includes period maxima and minima. Note that rain in OWM is cumulative for the LAST
    # 3 hours.
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    try:
        daily_high = owm_df.loc[forecast_start:forecast_end, 'temp_max'].max()
    except KeyError:
        daily_high = owm_df.loc[forecast_start:forecast_end, 'temperature'].max()
    try:
        daily_low = owm_df.loc[forecast_start:forecast_end, 'temp_min'].min()
    except KeyError:
        daily_low = owm_df.loc[forecast_start:forecast_end, 'temperature'].min()
    daily_wind = owm_df.loc[forecast_start:forecast_end, 'windSpeed'].max()
    daily_rain = np.nanmax([owm_df.loc[forecast_start + timedelta(hours=3):forecast_end, 'rain'].sum(), 0.0])

    # Create Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.setValues(daily_high, daily_low, daily_wind, daily_rain)
    forecast.timeseries.data = owm_df.reset_index()

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from owm.
    """
    # Get latitude and longitude from the config
    try:
        lat = float(config['Stations'][stid]['latitude'])
        lon = float(config['Stations'][stid]['longitude'])
    except KeyError:
        raise (KeyError('openweathermap: missing or invalid latitude or longitude for station %s' % stid))

    # Get the API key from the config
    try:
        api_key = config['Models'][model]['api_key']
    except KeyError:
        raise KeyError('openweathermap: no api_key parameter defined for model %s in config!' % model)

    # Get forecast
    forecast = get_owm_forecast(stid, lat, lon, api_key, forecast_date)

    return forecast
