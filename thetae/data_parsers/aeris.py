#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve Aeris forecast data.
"""

from thetae import Forecast
from thetae.util import localized_date_to_utc
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_iso
import requests
import pandas as pd
import numpy as np

default_model_name = 'Aeris'


def get_aeris_forecast(stid, lat, lon, api_id, api_secret, forecast_date):

    # Retrieve data
    api_url = 'https://api.aerisapi.com/forecasts/%s'
    point = '%0.3f,%0.3f' % (lat, lon)
    api_options = {
        'client_id': api_id,
        'client_secret': api_secret,
        'filter': '1hr',
        'plimit': '60',
    }
    json_url = api_url % point
    response = requests.get(json_url, params=api_options)
    aeris_data = response.json()
    # Raise error for invalid HTTP response
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print('aeris: got HTTP error when querying API')
        raise

    # Convert to pandas DataFrame and fix time, units, and columns
    aeris_df = pd.DataFrame(aeris_data['response'][0]['periods'])
    aeris_df['DateTime'] = np.nan
    for idx in aeris_df.index:
        aeris_df.loc[idx, 'DateTime'] = localized_date_to_utc(parse_iso(aeris_df.loc[idx, 'dateTimeISO']))
    aeris_df.set_index('DateTime', inplace=True)
    column_names_dict = {
        'avgTempF': 'temperature',
        'avgDewpointF': 'dewpoint',
        'sky': 'cloud',
        'windSpeedMaxKTS': 'windSpeed',
        'windGustKTS': 'windGust',
        'windDirDEG': 'windDirection',
        'precipIN': 'rain',
        'pressureMB': 'pressure',
        'weatherPrimary': 'condition'
    }
    aeris_df = aeris_df.rename(columns=column_names_dict)

    # Calculate daily values. Aeris includes period maxima and minima, although they appear just to be hourly values.
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    try:
        daily_high = aeris_df.loc[forecast_start:forecast_end, 'maxTempF'].max()
    except KeyError:
        daily_high = aeris_df.loc[forecast_start:forecast_end, 'temperature'].max()
    try:
        daily_low = aeris_df.loc[forecast_start:forecast_end, 'minTempF'].min()
    except KeyError:
        daily_low = aeris_df.loc[forecast_start:forecast_end, 'temperature'].min()
    try:
        daily_wind = aeris_df.loc[forecast_start:forecast_end, 'windSpeedMaxKTS'].max()
    except KeyError:
        daily_wind = aeris_df.loc[forecast_start:forecast_end, 'windSpeed'].max()
    daily_rain = aeris_df.loc[forecast_start:forecast_end - timedelta(hours=1), 'rain'].sum()

    # Create Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.setValues(daily_high, daily_low, daily_wind, daily_rain)
    forecast.timeseries.data = aeris_df.reset_index()

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from Aeris.
    """
    # Get latitude and longitude from the config
    try:
        lat = float(config['Stations'][stid]['latitude'])
        lon = float(config['Stations'][stid]['longitude'])
    except KeyError:
        raise (KeyError('aeris.py: missing or invalid latitude or longitude for station %s' % stid))

    # Get the API ID and Secret from the config
    try:
        api_id = config['Models'][model]['api_id']
    except KeyError:
        raise KeyError('aeris.py: no api_id parameter defined for model %s in config!' % model)
    try:
        api_secret = config['Models'][model]['api_secret']
    except KeyError:
        raise KeyError('aeris.py: no api_secret parameter defined for model %s in config!' % model)

    # Get forecast
    forecast = get_aeris_forecast(stid, lat, lon, api_id, api_secret, forecast_date)

    return forecast
