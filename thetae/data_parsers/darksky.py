#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve Dark Sky forecast data.
"""

from thetae import Forecast
from thetae.util import epoch_time_to_datetime, mph_to_kt
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np

default_model_name = 'Dark Sky'


def get_darksky_forecast(stid, lat, lon, api_key, forecast_date):

    # Retrieve data
    api_url = 'https://api.darksky.net/forecast/%s/%s'
    point = '%0.3f,%0.3f' % (lat, lon)
    api_options = {'exclude': 'currently,minutely,daily,alerts,flags'}
    json_url = api_url % (api_key, point)
    response = requests.get(json_url, params=api_options)
    darksky_data = response.json()

    # Convert to pandas DataFrame and fix time, units, and columns
    darksky_df = pd.DataFrame(darksky_data['hourly']['data'])
    darksky_df['DateTime'] = np.nan
    for idx in darksky_df.index:
        darksky_df.loc[idx, 'DateTime'] = epoch_time_to_datetime(darksky_df.loc[idx, 'time'],
                                                                 timezone=darksky_data['timezone'])
    darksky_df.set_index('DateTime', inplace=True)
    column_names_dict = {
        'cloudCover': 'cloud',
        'dewPoint': 'dewpoint',
        'precipIntensity': 'rain',
        'windBearing': 'windDirection',
        'summary': 'condition'
    }
    darksky_df = darksky_df.rename(columns=column_names_dict)
    darksky_df.loc[:, 'cloud'] = 100. * darksky_df.loc[:, 'cloud']
    darksky_df.loc[:, 'windSpeed'] = mph_to_kt(darksky_df.loc[:, 'windSpeed'])
    darksky_df.loc[:, 'windGust'] = mph_to_kt(darksky_df.loc[:, 'windGust'])

    # Calculate daily values
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    daily_high = darksky_df.loc[forecast_start:forecast_end, 'temperature'].max()
    daily_low = darksky_df.loc[forecast_start:forecast_end, 'temperature'].min()
    daily_wind = darksky_df.loc[forecast_start:forecast_end, 'windSpeed'].max()
    daily_rain = darksky_df.loc[forecast_start:forecast_end - timedelta(hours=1), 'rain'].sum()

    # Create Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.setValues(daily_high, daily_low, daily_wind, daily_rain)
    forecast.timeseries.data = darksky_df.reset_index()

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from Dark Sky.
    """
    # Get latitude and longitude from the config
    try:
        lat = float(config['Stations'][stid]['latitude'])
        lon = float(config['Stations'][stid]['longitude'])
    except KeyError:
        raise (KeyError('nws.py: missing or invalid latitude or longitude for station %s' % stid))

    # Get the API key from the config
    try:
        api_key = config['Models'][model]['api_key']
    except KeyError:
        raise KeyError('darksky.py: no api_key parameter defined for model %s in config!' % model)

    # Get forecast
    forecast = get_darksky_forecast(stid, lat, lon, api_key, forecast_date)

    return forecast
