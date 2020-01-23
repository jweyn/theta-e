#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve Climacell forecast data.
"""

from thetae import Forecast
from thetae.util import localized_date_to_utc
from datetime import timedelta
import requests
import pandas as pd

default_model_name = 'Climacell'


def get_climacell_forecast(stid, lat, lon, api_key, forecast_date):

    # Retrieve data
    api_url = 'https://api.climacell.co/v3/weather/forecast/hourly'
    api_options = {
        'apikey': api_key,
        'lat': lat,
        'lon': lon,
        'unit_system': 'us',
         'fields': 'precipitation,temp,dewpoint,wind_speed:knots,wind_gust:knots,baro_pressure:hPa,'
                   'wind_direction:degrees,cloud_cover:%,weather_code'
    }
    response = requests.get(api_url, params=api_options)
    # Raise error for invalid HTTP response
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print('climacell: got HTTP error when querying API')
        raise
    clima_data = response.json()

    # Convert to pandas DataFrame and fix time, units, and columns
    clima_df = pd.DataFrame(clima_data)
    # Drop lat, lon and get values
    clima_df.drop(['lat', 'lon'], axis=1, inplace=True)
    clima_df = clima_df.apply(lambda y: y.apply(lambda x: x['value']))
    column_names_dict = {
        'observation_time': 'DateTime',
        'temp': 'temperature',
        'cloud_cover': 'cloud',
        'precipitation': 'rain',
        'baro_pressure': 'pressure',
        'wind_speed': 'windSpeed',
        'wind_gust': 'windGust',
        'wind_direction': 'windDirection',
        'weather_code': 'condition'
    }
    clima_df = clima_df.rename(columns=column_names_dict)
    clima_df['DateTime'] = clima_df['DateTime'].apply(lambda x: localized_date_to_utc(pd.Timestamp(x)))
    clima_df.set_index('DateTime', inplace=True)

    # Calculate daily values
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    daily_high = clima_df.loc[forecast_start:forecast_end, 'temperature'].max()
    daily_low = clima_df.loc[forecast_start:forecast_end, 'temperature'].min()
    daily_wind = clima_df.loc[forecast_start:forecast_end, 'windSpeed'].max()
    daily_rain = clima_df.loc[forecast_start:forecast_end - timedelta(hours=1), 'rain'].sum()

    # Create Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.set_values(daily_high, daily_low, daily_wind, daily_rain)
    forecast.timeseries.data = clima_df.reset_index()

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from Climacell.
    """
    # Get latitude and longitude from the config
    try:
        lat = float(config['Stations'][stid]['latitude'])
        lon = float(config['Stations'][stid]['longitude'])
    except KeyError:
        raise (KeyError('climacell: missing or invalid latitude or longitude for station %s' % stid))

    # Get the API key from the config
    try:
        api_key = config['Models'][model]['api_key']
    except KeyError:
        raise KeyError('climacell: no api_key parameter defined for model %s in config!' % model)

    # Get forecast
    forecast = get_climacell_forecast(stid, lat, lon, api_key, forecast_date)

    return forecast
