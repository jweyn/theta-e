#
# Copyright (c) 2018 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates json output for web graphing.
"""

from datetime import datetime, timedelta
import json
from thetae.db import readForecast, readTimeSeries, readDaily


def json_daily(config, stid, models, forecast_date, file):
    """
    Produce a json file for daily forecast values at a station from the given models, and save it to file.
    """
    daily = {}
    variables = ['high', 'low', 'wind', 'rain']
    for model in models:
        if config['debug'] > 9:
            print('json: retrieving daily data for %s at %s' % (model, stid))
        forecast = readForecast(config, stid, model, forecast_date, no_hourly_ok=True)
        daily[model] = {v: getattr(forecast.daily, v) for v in variables}

    with open(file, 'w') as f:
        json.dump(daily, f)


def json_hourly(config, stid, models, forecast_date, file):
    """
    Produce a json file for hourly forecast values at a station from the given models, and save it to file.
    """
    hourly = {}
    for model in models:
        if config['debug'] > 9:
            print('json: retrieving hourly for %s at %s' % (model, stid))
        forecast = readForecast(config, stid, model, forecast_date, no_hourly_ok=True)
        hourly[model] = forecast.timeseries.data.to_dict(orient='list')

    with open(file, 'w') as f:
        json.dump(hourly, f)


def json_verif(config, stid, start_date, file):
    """
    Produce a json file for verification values at a station starting at start_date and going to the latest
    available verification, and save it to file.
    """
    verif = {}
    variables = ['high', 'low', 'wind', 'rain']
    if config['debug'] > 9:
        print('json: retrieving verification for %s' % stid)
    dailys = readDaily(config, stid, 'forecast', 'verif', start_date=start_date, end_date=datetime.utcnow())
    for v in variables:
        verif[v] = [getattr(dailys[j], v) for j in range(len(dailys))]
    verif['DateTime'] = [getattr(dailys[j], 'date') for j in range(len(dailys))]

    with open(file, 'w') as f:
        json.dump(verif, f)


def json_obs(config, stid, start_date, file):
    """
    Produce a json file for observations at a station starting at start_date and going to the current time, and save it
    to file.
    """
    if config['debug'] > 9:
        print('json: retrieving obs for %s' % stid)
    ts = readTimeSeries(config, stid, 'forecast', 'obs', start_date=start_date, end_date=datetime.utcnow())

    with open(file, 'w') as f:
        json.dump(ts.data.to_dict(orient='list'), f)


def main(config, stid, forecast_date):
    """
    Produce json output for a given station.
    """

    # Get list of models
    models = config['Models'].keys()

    # For historical outputs, set the date to 31 days back
    start_date = forecast_date - timedelta(days=31)

    # Get the file names
    try:
        file_dir = config['Web']['Options']['json_file_dir']
    except KeyError:
        file_dir = '%s/site_data' % config['THETAE_ROOT']
        print('json: warning: setting output directory to default')

    # Get output
    daily_file = '%s/%s_daily_forecast.json' % (file_dir, stid)
    json_daily(config, stid, models, forecast_date, daily_file)
    hourly_file = '%s/%s_hourly_forecast.json' % (file_dir, stid)
    json_hourly(config, stid, models, forecast_date, hourly_file)
    verif_file = '%s/%s_verif.json' % (file_dir, stid)
    json_verif(config, stid, start_date, verif_file)
    obs_file = '%s/%s_obs.json' % (file_dir, stid)
    json_obs(config, stid, start_date, obs_file)

    return
