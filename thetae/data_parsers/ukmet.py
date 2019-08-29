#
# Copyright (c) 2017-18 Jonathan Weyn & Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve UKMET data

"""

from thetae import Forecast
from thetae.util import c_to_f, ms_to_kt, mm_to_in, check_cache_file
from datetime import timedelta
import requests
import pandas as pd
import json

default_model_name = 'UKMET'


def get_ukmet_forecast(config, stid, lat, lon, api_id, api_secret, forecast_date):
    json_url = 'https://api-metoffice.apiconnect.ibmcloud.com/metoffice/production/v0/forecasts/point'
    headers = {
        'x-ibm-client-id': api_id,
        'x-ibm-client-secret': api_secret,
        'accept': "application/json"
    }

    api_options = {
        'excludeParameterMetaData': 'false',
        'includeLocationName': 'false',
        'latitude': lat,
        'longitude': lon,
    }

    # Get hourly forecast data
    # Check if we have a cached hourly file and if it is recent enough
    site_directory = '%s/site_data' % config['THETAE_ROOT']
    cache_file = '%s/%s_ukmet_hourly.txt' % (site_directory, stid)
    cache_ok = check_cache_file(config, cache_file, interval=4)

    if not cache_ok:
        response = requests.get('%s/hourly' % json_url, params=api_options, headers=headers)
        ukmet_data_hourly = response.json()
        # Raise error for invalid HTTP response
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            print('ukmet: got HTTP error when querying API for hourly data')
            raise
        # Cache the response
        with open(cache_file, 'w') as f:
            f.write(response.text)
    else:
        ukmet_data_hourly = json.load(open(cache_file))

    # model run date--currently not using this but might be of interest later
    model_run_date = ukmet_data_hourly['features'][0]['properties']['modelRunDate']

    ukmet_df = pd.DataFrame(ukmet_data_hourly['features'][0]['properties']['timeSeries'])
    ukmet_df['DateTime'] = ukmet_df['time'].apply(pd.to_datetime).apply(lambda x: x.replace(tzinfo=None))
    ukmet_df.set_index('DateTime', inplace=True)

    # rename columns
    column_names_dict = {
        'screenTemperature': 'temperature',
        'screenDewPointTemperature': 'dewpoint',
        'windSpeed10m': 'windSpeed',
        'windGustSpeed10m': 'windGust',
        'windDirectionFrom10m': 'windDirection',
        'totalPrecipAmount': 'rain',
        'mslp': 'pressure',
    }
    ukmet_df = ukmet_df.rename(columns=column_names_dict)

    # drop columns that we are not using
    ukmet_df.drop(['feelsLikeTemperature', 'probOfPrecipitation', 'screenRelativeHumidity', 'significantWeatherCode',
                   'precipitationRate', 'totalSnowAmount', 'uvIndex', 'visibility'], inplace=True, axis=1)

    # correct units
    ukmet_df['pressure'] /= 100.
    ukmet_df['temperature'] = c_to_f(ukmet_df['temperature'])
    ukmet_df['dewpoint'] = c_to_f(ukmet_df['dewpoint'])
    ukmet_df['windSpeed'] = ms_to_kt(ukmet_df['windSpeed'])
    ukmet_df['windGust'] = ms_to_kt(ukmet_df['windGust'])
    ukmet_df['rain'] = mm_to_in(ukmet_df['rain'])

    # Create Forecast object, save timeseries
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.timeseries.data = ukmet_df.reset_index()

    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)

    # Now use the daily API to find daily values
    # Check if we have a cached daily file and if it is recent enough
    site_directory = '%s/site_data' % config['THETAE_ROOT']
    cache_file = '%s/%s_ukmet_daily.txt' % (site_directory, stid)
    cache_ok = check_cache_file(config, cache_file, interval=4)

    have_daily_values = True
    if not cache_ok:
        response = requests.get('%s/daily' % json_url, params=api_options, headers=headers)
        ukmet_data_daily = response.json()
        # Raise error for invalid HTTP response
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            print('ukmet warning: got HTTP error when querying API for daily data; using hourly values')
            have_daily_values = False
        # Cache the response
        with open(cache_file, 'w') as f:
            f.write(response.text)
    else:
        ukmet_data_daily = json.load(open(cache_file))

    # extract daily values for the forecast date
    if have_daily_values:
        ukmet_df_daily = pd.DataFrame(ukmet_data_daily['features'][0]['properties']['timeSeries'])
        ukmet_df_daily.set_index('time', inplace=True)
        ukmet_df_daily.index = pd.to_datetime(ukmet_df_daily.index)
        daily_forecast = ukmet_df_daily.loc[forecast_date]
        daytime_max = c_to_f(daily_forecast['dayMaxScreenTemperature'])
        nighttime_min = c_to_f(daily_forecast['nightMinScreenTemperature'])
    else:
        daytime_max = -1000.
        nighttime_min = 1000.

    # compare hourly temperature to daily--update if needed
    daily_high = ukmet_df.loc[forecast_start:forecast_end, 'temperature'].max()
    if daytime_max > daily_high:
        daily_high = daytime_max

    daily_low = ukmet_df.loc[forecast_start:forecast_end, 'temperature'].min()
    if nighttime_min < daily_low:
        daily_low = nighttime_min

    daily_wind = ukmet_df.loc[forecast_start:forecast_end, 'windSpeed'].max()
    daily_rain = ukmet_df.loc[forecast_start:forecast_end - timedelta(hours=1), 'rain'].sum()

    forecast.daily.set_values(daily_high, daily_low, daily_wind, daily_rain)

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from UKMET data.
    """

    # Get latitude and longitude from the config
    try:
        lat = float(config['Stations'][stid]['latitude'])
        lon = float(config['Stations'][stid]['longitude'])
    except KeyError:
        raise (KeyError('ukmet: missing or invalid latitude or longitude for station %s' % stid))

    # Get the API ID and Secret from the config
    try:
        api_id = config['Models'][model]['api_id']
    except KeyError:
        raise KeyError('ukmet: no api_id parameter defined for model %s in config!' % model)
    try:
        api_secret = config['Models'][model]['api_secret']
    except KeyError:
        raise KeyError('ukmet: no api_secret parameter defined for model %s in config!' % model)

    # Get forecast
    forecast = get_ukmet_forecast(config, stid, lat, lon, api_id, api_secret, forecast_date)

    return forecast
