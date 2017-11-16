#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Service to get all forecasts specified in config
'''

from thetae.db import db_writeForecast
from datetime import datetime, timedelta
from thetae.util import _get_object

def main(config):
    '''
    Main function
    '''

    # Figure out which day we are forecasting for: the next UTC day.
    time_now = datetime.utcnow()
    forecast_date = (datetime(time_now.year, time_now.month, time_now.day) +
                     timedelta(days=1))
    print('getForecasts: forecast date %s' % forecast_date)
    
    # Go through the models in config
    for model in config['Models'].keys():
        try:
            driver = config['Models'][model]['driver']
        except KeyError:
            print('getForecasts: driver not specified for model %s' % model)
            continue
        print('getForecasts: getting forecasts from %s' % model)

        # Get the forecast from the driver at each site
        for stid in config['Stations'].keys():
            if int(config['debug']) > 9:
                print('getForecasts: getting forecast for station %s' % stid)
            try:
                # Each forecast has a function main and returns a Forecast
                forecast = _get_object(driver).main(config, stid, forecast_date)
            except BaseException as e:
                print('getForecast: failed to get forecast from %s for %s' %
                      (model, stid))
                print("Reason: '%s'" % str(e))
                continue
            # Write to the database
            try:
                if int(config['debug']) > 9:
                    print('getForecasts: writing forecast to database')
#                db_write(config, stid, forecast, 'DAILY_FORECAST', model=model)
                db_writeForecast(config, forecast)
            except BaseException as e:
                print('getForecast: failed to write forecast to database')
                print("*** Reason: '%s'" % str(e))

