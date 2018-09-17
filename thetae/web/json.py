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
import os
import pandas as pd
from thetae.util import Forecast, date_to_string
from thetae.db import readForecast, readTimeSeries, readDaily


def json_daily(config, stid, models, forecast_date, file, start_date=None):
    """
    Produce a json file for daily forecast values at a station from the given models, and save it to file.
    """
    daily = {}
    variables = ['high', 'low', 'wind', 'rain']
    if start_date is None:
        dates = [forecast_date]
    else:
        dates = pd.date_range(start_date, forecast_date, freq='D').to_pydatetime()
    for model in models:
        if config['debug'] > 9:
            print('web.json: retrieving daily data for %s at %s' % (model, stid))
        forecasts = []
        for date in dates:
            try:
                forecasts.append(readForecast(config, stid, model, date, no_hourly_ok=True))
            except (ValueError, IndexError):
                forecasts.append(Forecast(stid, model, date))
        daily[model] = {v.upper(): [getattr(forecasts[f].daily, v) for f in range(len(forecasts))] for v in variables}
        daily[model]['DATETIME'] = [date_to_string(d) + ' Z' for d in dates]

    with open(file, 'w') as f:
        json.dump(daily, f)


def json_hourly(config, stid, models, forecast_date, file):
    """
    Produce a json file for hourly forecast values at a station from the given models, and save it to file.
    """
    hourly = {}
    for model in models:
        if config['debug'] > 9:
            print('web.json: retrieving hourly data for %s at %s' % (model, stid))
        try:
            forecast = readForecast(config, stid, model, forecast_date, hour_padding=18, no_hourly_ok=True)
            # Eliminate 'NaN'
            ts = forecast.timeseries.data.where(pd.notnull(forecast.timeseries.data), None)
            ts['DATETIME'] = ts['DATETIME'].apply(lambda x: x + ' Z')
            hourly[model] = ts.to_dict(orient='list')
        except (ValueError, KeyError):
            hourly[model] = {}

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
        print('web.json: retrieving verification for %s' % stid)
    dailys = readDaily(config, stid, 'forecast', 'verif', start_date=start_date, end_date=datetime.utcnow())
    for v in variables:
        verif[v.upper()] = [getattr(dailys[j], v) for j in range(len(dailys))]
    verif['DATETIME'] = [getattr(dailys[j], 'date') + ' Z' for j in range(len(dailys))]

    with open(file, 'w') as f:
        json.dump(verif, f)


def json_obs(config, stid, start_date, file):
    """
    Produce a json file for observations at a station starting at start_date and going to the current time, and save it
    to file.
    """
    if config['debug'] > 9:
        print('web.json: retrieving obs for %s' % stid)
    ts = readTimeSeries(config, stid, 'forecast', 'obs', start_date=start_date, end_date=datetime.utcnow())
    ts.data['DATETIME'] = ts.data['DATETIME'].apply(lambda x: x + ' Z')

    with open(file, 'w') as f:
        json.dump(ts.data.where(ts.data.notnull(), None).to_dict(orient='list'), f)


def main(config, stid, forecast_date):
    """
    Produce json output for a given station.
    """

    # Get list of models
    models = config['Models'].keys()

    # For historical outputs, set the date to 31 days back
    start_date = forecast_date - timedelta(days=31)

    # Get the file directory and attempt to create it if it doesn't exist
    try:
        file_dir = config['Web']['Options']['json_file_dir']
    except KeyError:
        file_dir = '%s/site_data' % config['THETAE_ROOT']
        print('web.json warning: setting output directory to default')
    os.makedirs(file_dir, exist_ok=True)
    if config['debug'] > 9:
        print('web.json: writing output to %s' % file_dir)

    # Get output
    daily_file = '%s/%s_daily_forecast.json' % (file_dir, stid)
    json_daily(config, stid, models, forecast_date, daily_file, start_date=start_date)
    hourly_file = '%s/%s_hourly_forecast.json' % (file_dir, stid)
    json_hourly(config, stid, models, forecast_date, hourly_file)
    verif_file = '%s/%s_verif.json' % (file_dir, stid)
    json_verif(config, stid, start_date, verif_file)
    obs_file = '%s/%s_obs.json' % (file_dir, stid)
    json_obs(config, stid, start_date, obs_file)

    return
