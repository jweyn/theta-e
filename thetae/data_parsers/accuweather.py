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
from thetae.util import get_codes, write_codes, check_cache_file, localized_date_to_utc
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_iso
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
    except (IOError, OSError):  # codes file does not exist
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

    # Retrieve data. Looks like only daily temperatures will be of any use right now.
    if not cache_ok:
        api_url = 'http://dataservice.accuweather.com/forecasts/v1/daily/5day/%s' % location_key
        api_options = {'apikey': api_key}
        response = requests.get(api_url, params=api_options)
        accuwx_data = response.json()
        # Raise error if we have invalid HTTP response
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            print('accuwx: got HTTP error when querying API')
            raise
        # Cache the response
        with open(cache_file, 'w') as f:
            f.write(response.text)
    else:
        accuwx_data = json.load(open(cache_file))

    # Convert to pandas DataFrame, fix time, and get high and low
    accuwx_df = pd.DataFrame(accuwx_data['DailyForecasts'])
    accuwx_df['DateTime'] = np.nan
    for idx in accuwx_df.index:
        accuwx_df.loc[idx, 'DateTime'] = localized_date_to_utc(parse_iso(accuwx_df.loc[idx, 'Date'])).replace(hour=0)
    accuwx_df.set_index('DateTime', inplace=True)
    high = float(accuwx_df.loc[forecast_date, 'Temperature']['Maximum']['Value'])
    # Low should be for night before. We can also 'guess' that the low could be non-diurnal and halfway between the
    # max and next min.
    low = float(accuwx_df.loc[forecast_date - timedelta(days=1), 'Temperature']['Minimum']['Value'])
    alt_low = 0.5 * (high + float(accuwx_df.loc[forecast_date, 'Temperature']['Minimum']['Value']))
    if low - alt_low > 3:
        if config['debug'] > 9:
            print('accuweather: warning: setting low down from %0.0f to %0.0f' % (low, alt_low))
        low = alt_low

    # Create Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.setValues(high, low, None, None)

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
