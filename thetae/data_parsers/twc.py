#
# Copyright (c) 2019 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve forecasts from the new weather.com API.
"""

from thetae import Forecast
from thetae.util import epoch_time_to_datetime, mph_to_kt, inhg_to_mb
from datetime import datetime, timedelta
import requests
import pandas as pd

default_model_name = 'Weather Channel'


def dn_to_timedelta(s):
    if s == 'D':
        return timedelta(hours=9)
    elif s == 'N':
        return timedelta(hours=21)
    else:
        return s


def get_twc_forecast(stid, api_key, forecast_date):

    # retrieve api json data
    api_url = 'https://api.weather.com/v3/wx/forecast/daily/5day'
    api_options = {
        'language': 'en-US',
        'format': 'json',
        'units': 'e',
        'apiKey': api_key,
        'icaoCode': stid
    }
    response = requests.get(api_url, params=api_options)
    twc_data = response.json()
    # Raise error for invalid HTTP response
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print('twc: got HTTP error when querying API')
        raise

    # The data has a 'daypart' section which has a time series of day/night pairs. This is useful for wind and
    # precipitation information, but we have to make some assumptions about the datetime to use it.
    twc_df = pd.DataFrame(twc_data['daypart'][0])
    valid_days = [epoch_time_to_datetime(d) for d in twc_data['validTimeUtc'] for _ in range(2)]
    twc_df['DateTime'] = pd.Series(valid_days) + twc_df['dayOrNight'].apply(dn_to_timedelta)
    if twc_df['dayOrNight'][0] is None:
        twc_df.drop(0, axis=0, inplace=True)

    column_names_dict = {
          'cloudCover': 'cloud',
          'qpf': 'rain',
          'wxPhraseLong': 'condition'
    }
    twc_df = twc_df.rename(columns=column_names_dict)
    twc_df.set_index('DateTime', inplace=True)

    # Resample to 3-hourly. Carefully consider the QPF.
    offset = twc_df.index[0].hour % 3
    twc_hourly = twc_df.resample('3H', base=offset).interpolate()
    twc_hourly['rain'] = twc_hourly['rain'].apply(lambda x: x / 4.)
    twc_hourly['qpfSnow'] = twc_hourly['qpfSnow'].apply(lambda x: x / 4.)
    twc_hourly['windDirection'] = twc_hourly['windDirection'].round()

    # calculate daily values
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    daily_high = twc_hourly.loc[forecast_start:forecast_end, 'temperature'].max()
    daily_low = twc_hourly.loc[forecast_start:forecast_end, 'temperature'].min()
    daily_wind = twc_hourly.loc[forecast_start:forecast_end, 'windSpeed'].max()
    daily_rain = twc_hourly.loc[forecast_start:forecast_end - timedelta(hours=1), 'rain'].sum()

    # create Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.set_values(daily_high, daily_low, daily_wind, daily_rain)
    forecast.timeseries.data = twc_hourly.reset_index()

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
    forecast = get_twc_forecast(stid, api_key, forecast_date)

    return forecast
