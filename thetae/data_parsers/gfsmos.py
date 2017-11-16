#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Retrieve GFS MOS data.
'''

from thetae import Forecast
from datetime import datetime, timedelta

# For now, let's return some junk!

def gfs_mos_forecast(stid, forecast_date):
    '''
    Do the data retrieval.
    '''
    
    # Generate a Forecast object
    forecast = Forecast(stid, 'GFS MOS', forecast_date)
    forecast.daily.high = 52.
    forecast.daily.low = 41.
    forecast.daily.wind = 17.
    forecast.daily.rain = 0.41
    
    # Create a dummy pd dataframe to test
    forecast.timeseries.data['DateTime'] = [forecast_date, forecast_date +
                                            timedelta(hours=3)]
    forecast.timeseries.data['temperature'] = [56., 55.]
    forecast.timeseries.data['dewpoint'] = [51., 51.]

    return forecast

def main(config, stid, forecast_date):
    '''
    Produce a Forecast object from GFS MOS.
    '''

    # Get forecast
    forecast = gfs_mos_forecast(stid, forecast_date)

    return forecast

