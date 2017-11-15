#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Retrieve GFS MOS data.
'''

from thetae import Forecast

# For now, let's return some junk! It's not even using a Forecast object yet.

def gfs_mos_forecast(stid, forecast_date):
    '''
    Do the data retrieval.
    '''
    
    # Generate a Forecast object
    forecast = Forecast(stid, 'GFS MOS', forecast_date)

    # Temporarily use a dictionary of junk
    temp = {}
    temp[forecast_date] = { 'high' : 52.,
                            'low'  : 41.,
                            'wind' : 17.,
                            'rain' : 0.40
                            }

    return temp

def main(config, stid, forecast_date):
    '''
    Produce a Forecast object from GFS MOS.
    '''

    # Get forecast
    forecast = gfs_mos_forecast(stid, forecast_date)

    return forecast

