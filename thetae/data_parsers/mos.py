#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve GFS or NAM MOS data.
"""

from thetae import Forecast
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests
from builtins import str

default_model_name = 'MOS'


def qpf_interpreter(qpf):
    """
    Interprets a QPF value average estimates

    :param qpf: q06 or q12 value from MOS
    :return: new_p: average estimated precip
    """
    translator = {
        0: 0.0,
        1: 0.05,
        2: 0.15,
        3: 0.35,
        4: 0.75,
        5: 1.5,
        6: 2.5
    }
    try:
        new_p = translator[qpf]
    except KeyError:
        new_p = 0.0
    return new_p


def get_mos_forecast(stid, mos_model, init_date, forecast_date):
    """
    Retrieve MOS data. No unit conversions, yay!

    :param stid: station ID
    :param mos_model: model name ('GFS' or 'NAM')
    :param init_date: datetime of model initialization
    :param forecast_date: datetime of day to forecast
    :return: Forecast object for forecast_date
    """
    # Create forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)

    # For NBS, model run time is 1 hour later
    if mos_model.upper() == 'NBS':
        init_date = init_date + timedelta(hours=1)

    # Retrieve the model data
    base_url = 'http://mesonet.agron.iastate.edu/mos/csv.php?station=%s&runtime=%s&model=%s'
    formatted_date = init_date.strftime('%Y-%m-%d%%20%H:00')
    url = base_url % (stid, formatted_date, mos_model)
    response = requests.get(url, stream=True)
    # Create pandas DataFrame
    df = pd.read_csv(response.raw, index_col=False)
    # Raise exception if DataFrame is empty
    if len(df.index) == 0:
        raise ValueError('mos: error: empty DataFrame; data missing.')
    date_index = pd.Index(pd.to_datetime(df['ftime'])).tz_localize(None)
    df['datetime'] = date_index
    # Remove duplicate rows
    df = df.drop_duplicates()
    # Fix rain
    if mos_model.upper() == 'NBS':
        df['q06'] = df['q06'].apply(lambda x: x / 100.)
    else:
        df['q06'] = df['q06'].apply(qpf_interpreter)

    # Format the DataFrame for the default schema
    # Dictionary for renaming columns
    ts = df.copy()
    names_dict = {
        'datetime': 'DateTime',
        'tmp': 'temperature',
        'dpt': 'dewpoint',
        'wsp': 'windSpeed',
        'wdr': 'windDirection',
        'q06': 'rain'
    }
    col_names = list(map(''.join, ts.columns.values))
    for col in col_names:
        if col not in names_dict.keys():
            ts = ts.drop(col, axis=1)
    # Set the timeseries
    forecast.timeseries.data = ts.rename(columns=names_dict)

    # Now do the daily forecast part
    df = df.set_index('datetime')
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    # Some parameters need to include the forecast start; others, like total rain and 6-hour maxes, don't
    try:
        iloc_start_include = df.index.get_loc(forecast_start)
        iloc_start_exclude = iloc_start_include + 1
    except BaseException:
        print('mos.py: error getting start time index in db; check data.')
        raise
    try:
        iloc_end = df.index.get_loc(forecast_end) + 1
    except BaseException:
        print('mos.py: error getting end time index in db; check data.')
        raise
    raw_high = df.iloc[iloc_start_include:iloc_end]['tmp'].max()
    raw_low = df.iloc[iloc_start_include:iloc_end]['tmp'].min()
    nx_high = df.iloc[iloc_start_exclude:iloc_end]['n_x'].max()
    nx_low = df.iloc[iloc_start_exclude:iloc_end]['n_x'].min()
    # Set the daily
    forecast.daily.set_values(np.nanmax([raw_high, nx_high]), np.nanmin([raw_low, nx_low]),
                             df.iloc[iloc_start_include:iloc_end]['wsp'].max(),
                             df.iloc[iloc_start_exclude:iloc_end]['q06'].sum())

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from MOS.
    """
    # Get the model name from the config
    try:
        mos_model = config['Models'][model]['mos_model']
    except KeyError:
        raise KeyError('mos: no mos_model parameter defined for model %s in config!' % model)

    # Init date, determined from current time
    time_now = datetime.utcnow()
    if time_now.hour >= 16:
        init_date = forecast_date - timedelta(hours=12)
    elif time_now.hour < 6:
        init_date = forecast_date - timedelta(hours=36)
    else:
        init_date = forecast_date - timedelta(hours=24)

    # Get forecast
    forecast = get_mos_forecast(stid, mos_model, init_date, forecast_date)

    return forecast


def historical(config, model, stid, forecast_dates):
    """
    Produce a list of Forecast objects from MOS for each date in forecast_dates.
    """
    # Get the model name from the config
    try:
        mos_model = config['Models'][model]['mos_model']
    except KeyError:
        raise KeyError('mos: no mos_model parameter defined for model %s in config!' % model)

    # Get forecasts
    forecasts = []
    for forecast_date in forecast_dates:
        init_date = forecast_date - timedelta(hours=12)
        try:
            forecast = get_mos_forecast(stid, mos_model, init_date, forecast_date)
            forecasts.append(forecast)
        except BaseException as e:
            if int(config['debug']) > 9:
                print('mos: failed to retrieve historical forecast for %s on %s' % (mos_model, init_date))
                print("*** Reason: '%s'" % str(e))

    return forecasts
