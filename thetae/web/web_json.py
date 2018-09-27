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
from collections import OrderedDict
from thetae.util import Forecast, date_to_string, last_leap_year, date_to_datetime
from thetae.db import readForecast, readTimeSeries, readDaily


def json_daily(config, stid, models, forecast_date, start_date=None):
    """
    Produce a json file for daily forecast values at a station from the given models, and save it to file.
    """
    daily = OrderedDict()
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
        daily[model]['DATETIME'] = [d.isoformat() + 'Z' for d in dates]

    return daily


def json_hourly(config, stid, models, forecast_date):
    """
    Produce a json file for hourly forecast values at a station from the given models, and save it to file.
    """
    hourly = OrderedDict()
    for model in models:
        if config['debug'] > 9:
            print('web.json: retrieving hourly data for %s at %s' % (model, stid))
        try:
            forecast = readForecast(config, stid, model, forecast_date, hour_padding=18, no_hourly_ok=True)
            # Eliminate 'NaN'
            ts = forecast.timeseries.data.where(pd.notnull(forecast.timeseries.data), None)
            ts['DATETIME'] = pd.to_datetime(ts['DATETIME']).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            hourly[model] = ts.to_dict(orient='list', into=OrderedDict)
        except (ValueError, KeyError):
            hourly[model] = OrderedDict()

    return hourly


def json_verif(config, stid, start_date):
    """
    Produce a json file for verification values at a station starting at start_date and going to the latest
    available verification, and save it to file.
    """
    verif = OrderedDict()
    variables = ['high', 'low', 'wind', 'rain']
    if config['debug'] > 9:
        print('web.json: retrieving verification for %s' % stid)
    dailys = readDaily(config, stid, 'forecast', 'verif', start_date=start_date, end_date=datetime.utcnow())
    for v in variables:
        verif[v.upper()] = [getattr(dailys[j], v) for j in range(len(dailys))]
    verif['DATETIME'] = [getattr(dailys[j], 'date').isoformat() + 'Z' for j in range(len(dailys))]

    return verif


def json_obs(config, stid, start_date):
    """
    Produce a json file for observations at a station starting at start_date and going to the current time, and save it
    to file.
    """
    if config['debug'] > 9:
        print('web.json: retrieving obs for %s' % stid)
    ts = readTimeSeries(config, stid, 'forecast', 'obs', start_date=start_date, end_date=datetime.utcnow())
    ts.data['DATETIME'] = pd.to_datetime(ts.data['DATETIME']).dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    return ts.data.where(ts.data.notnull(), None).to_dict(orient='list', into=OrderedDict)


def json_climo(config, stid, start_date):
    """
    Produce a json file for verification values at a station starting at start_date and going to the latest
    available verification, and save it to file.
    """
    climo = OrderedDict()
    end_date = datetime.utcnow()
    variables = ['high', 'low', 'wind', 'rain']
    if config['debug'] > 9:
        print('web.json: retrieving climo for %s' % stid)
    dailys = []
    current_date = start_date
    while current_date <= end_date:
        climo_date = current_date.replace(year=last_leap_year())
        daily = readDaily(config, stid, 'forecast', 'climo', start_date=climo_date, end_date=climo_date)
        daily.date = current_date
        dailys.append(daily)
        current_date += timedelta(days=1)
    for v in variables:
        climo[v.upper()] = [getattr(dailys[j], v) for j in range(len(dailys))]
    climo['DATETIME'] = [getattr(dailys[j], 'date').isoformat() + 'Z' for j in range(len(dailys))]

    return climo


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
        file_dir = config['Web']['Options']['web_directory']
    except KeyError:
        file_dir = '%s/site_data' % config['THETAE_ROOT']
        print('web.json warning: setting output directory to default')
    if not(os.path.isdir(file_dir)):
        os.makedirs(file_dir)
    if config['debug'] > 9:
        print('web.json: writing output to %s' % file_dir)

    json_file = '%s/%s.json' % (file_dir, stid.upper())

    # Get output
    json_dict = OrderedDict()
    json_dict['dailyForecast'] = json_daily(config, stid, models, forecast_date, start_date=start_date)
    json_dict['hourlyForecast'] = json_hourly(config, stid, models, forecast_date)
    json_dict['verification'] = json_verif(config, stid, start_date)
    json_dict['obs'] = json_obs(config, stid, start_date)
    json_dict['climo'] = json_climo(config, stid, start_date)

    with open(json_file, 'w') as f:
        json.dump(json_dict, f)

    return
