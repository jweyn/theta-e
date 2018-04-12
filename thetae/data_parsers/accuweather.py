#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve forecast data from AccuWeather. AccuWeather has a very limited number (50) of daily API calls, so we have to
be efficient. We cache the API result for 12 hours, unless the current hour is 23Z, in which case we make sure that the
API has been updated in the last hour. AccuWeather also retrieves forecasts only based on a "location key", which must
be separately obtained from the API with a location call. These keys will be automatically archived in a codes file.
"""

from thetae import Forecast
from thetae.util import get_codes, write_codes, epoch_time_to_datetime, check_cache_file, mph_to_kt
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np
import json

default_model_name = 'AccuWeather'


def get_accuwx_location(lat, lon, api_key):
    """
    Retrieves a site's location key from the AccuWeather API.

    :param lat:
    :param lon:
    :param api_key:
    :return:
    """
    api_url = 'http://dataservice.accuweather.com/locations/v1/cities/geoposition/search'
    point = '%0.3f,%0.3f' % (lat, lon)
    api_options = {'apikey': api_key, 'q': point}
    response = requests.get(api_url, params=api_options)
    accuwx_location = response.json()
    location_key = accuwx_location['Key']

    return location_key


def get_location_key(config, stid, lat, lon, api_key):
    """
    Gets a site's location key either from the archived codes file or the API, writing to the archive file in the
    process.

    :param config:
    :param stid:
    :param lat:
    :param lon:
    :param api_key:
    :return:
    """
    codes_file = 'accuwx.codes'
    try:
        location_key = get_codes(config, codes_file, stid=stid)
    except OSError:  # codes file does not exist
        location_key = get_accuwx_location(lat, lon, api_key)
        codes = {stid: location_key}
        write_codes(config, codes, codes_file, header='station ID,location key')
    except KeyError:  # site not in codes file
        location_key = get_accuwx_location(lat, lon, api_key)
        codes = get_codes(config, codes_file)
        codes[stid] = location_key
        write_codes(config, codes, codes_file, header='station ID,location key')

    return location_key


def get_accuwx_forecast(config, stid, location_key, api_key, forecast_date):
    """
    Get a Forecast from the AccuWeather API or the cache file.

    :param config:
    :param stid:
    :param location_key:
    :param api_key:
    :param forecast_date:
    :return:
    """
    # Check if we have a cached file and if it is recent enough
    site_directory = '%s/site_data' % config['THETAE_ROOT']
    cache_file = '%s/%s_accuwx.txt' % (site_directory, stid)
    cache_ok = check_cache_file(config, cache_file)

    # Retrieve data
    if not(cache_ok):
        api_url = 'http://dataservice.accuweather.com/forecasts/v1/daily/5day/%s' % location_key
        api_options = {'apikey': api_key}
        response = requests.get(api_url, params=api_options)
        accuwx_data = response.json()
        # Write to cache
        with open(cache_file, 'w') as f:
            f.write(response.text)
    else:
        accuwx_data = json.load(open(cache_file))

    # Convert to pandas DataFrame and fix time, units, and columns
    accuwx_df = pd.DataFrame(accuwx_data)

    return accuwx_df


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from Dark Sky.
    """
    # Get latitude and longitude from the config
    try:
        lat = float(config['Stations'][stid]['latitude'])
        lon = float(config['Stations'][stid]['longitude'])
    except KeyError:
        raise (KeyError('accuweather.py: missing or invalid latitude or longitude for station %s' % stid))

    # Get the API key from the config
    try:
        api_key = config['Models'][model]['api_key']
    except KeyError:
        raise KeyError('accuweather.py: no api_key parameter defined for model %s in config!' % model)

    # Get the location key
    location_key = get_location_key(config, stid, lat, lon, api_key)

    # Get forecast
    forecast = get_accuwx_forecast(config, stid, location_key, api_key, forecast_date)

    return forecast
