#
# Copyright (c) 2017-18 Jonathan Weyn & Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve UKMET data

"""

from thetae import Forecast
from thetae.util import localized_date_to_utc
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_iso
import requests
import pandas as pd
import numpy as np
import pdb

default_model_name = 'UKMET'

def get_ukmet_forecast(stid, lat, lon, api_id, api_secret, forecast_date):
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

    json_url = 'https://api-metoffice.apiconnect.ibmcloud.com/metoffice/production/v0/forecasts/point/hourly'
    response = requests.get(json_url, params=api_options, headers=headers)
    ukmet_data = response.json()

    # Raise error for invalid HTTP response
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print('aeris: got HTTP error when querying API')
        raise

    ukmet_df = pd.DataFrame(ukmet_data['features'][0]['properties']['timeSeries'])



    pdb.set_trace()
    return


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
    forecast = get_ukmet_forecast(stid, lat, lon, api_id, api_secret, forecast_date)

    return forecast
