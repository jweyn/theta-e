#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Service to get all forecasts specified in config. The main process is used to get the next day's forecast in accordance
with the main engine process, while the historical process is used in the engine historical function to produce
historical forecasts for valid sources.
"""

from thetae.db import writeForecast
from datetime import datetime, timedelta
from thetae.util import get_object, config_date_to_datetime, to_bool
from builtins import str


def main(config):
    """
    Main function. Iterates through models and sites and writes each to the 'forecast' database.
    """

    # Figure out which day we are forecasting for: the next UTC day.
    time_now = datetime.utcnow()
    forecast_date = (datetime(time_now.year, time_now.month, time_now.day) + timedelta(days=1))
    print('getForecasts: forecast date %s' % forecast_date)

    # Go through the models in config
    for model in config['Models'].keys():
        try:
            driver = config['Models'][model]['driver']
        except KeyError:
            print('getForecasts warning: driver not specified for model %s' % model)
            continue
        print('getForecasts: getting forecasts from %s' % model)

        # Get the forecast from the driver at each site
        for stid in config['Stations'].keys():
            if config['debug'] > 9:
                print('getForecasts: getting forecast for station %s' % stid)
            try:
                # Each forecast has a function 'main' which returns a Forecast
                forecast = get_object(driver).main(config, model, stid, forecast_date)
                # Set the model name
                forecast.setModel(model)
            except BaseException as e:
                print('getForecasts: failed to get forecast from %s for %s' % (model, stid))
                print("*** Reason: '%s'" % str(e))
                if config['traceback']:
                    raise
                continue
            # Write to the database
            try:
                if config['debug'] > 9:
                    print('getForecasts: writing forecast to database')
                writeForecast(config, forecast)
            except BaseException as e:
                print('getForecasts: failed to write forecast to database')
                print("*** Reason: '%s'" % str(e))
                if config['traceback']:
                    raise


def historical(config, stid):
    """
    Function to obtain historical forecast data, for a specific site. Iterates over models which have the 'historical'
    parameter set to True, and begins at the config start_date.
    """

    print('getForecasts: getting historical forecasts for station %s' % stid)

    # Figure out which days we are forecasting for since config start_date.
    time_now = datetime.utcnow()
    forecast_dates = []
    try:
        start_date = config_date_to_datetime(config['Stations'][stid]['history_start'])
    except:
        print('getForecasts warning: cannot get start_date in config for station %s, setting to -30 days' % stid)
        start_date = (datetime(time_now.year, time_now.month, time_now.day) - timedelta(days=30))
    date = start_date
    while date < time_now:
        forecast_dates.append(date)
        date = date + timedelta(hours=24)
    if config['debug'] > 9:
        print('getForecasts: getting historical forecasts starting %s' % start_date)

    # Go through the models in config
    for model in config['Models'].keys():
        if not (to_bool(config['Models'][model].get('historical', False))):
            if config['debug'] > 9:
                print('getForecasts: no historical to do for model %s' % model)
            continue
        try:
            driver = config['Models'][model]['driver']
        except KeyError:
            print('getForecasts warning: driver not specified for model %s' % model)
            continue

        # Get the forecasts from the driver
        try:
            # Each driver should have a function 'historical' which returns a list of Forecasts
            print('getForecasts: getting historical forecasts from %s' % model)
            forecasts = get_object(driver).historical(config, model, stid, forecast_dates)
            # Set the model name
            forecasts = [f.setModel(model) for f in forecasts]
        except BaseException as e:
            print('getForecasts: failed to get historical forecasts from %s for %s' % (model, stid))
            print("*** Reason: '%s'" % str(e))
            if config['traceback']:
                raise
            continue
        # Write to the database
        try:
            if config['debug'] > 9:
                print('getForecasts: writing historical forecasts to database')
            writeForecast(config, forecasts)
        except BaseException as e:
            print('getForecasts: failed to write historical forecasts to database')
            print("*** Reason: '%s'" % str(e))
            if config['traceback']:
                raise

    return
