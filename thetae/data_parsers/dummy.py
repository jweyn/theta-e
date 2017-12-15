#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve GFS or NAM MOS data.
"""

from thetae import Forecast
from datetime import datetime, timedelta

default_model_name = 'DUMMY'


# For now, let's return some junk!

def gfs_mos_forecast(stid, forecast_date):
    """
    Do the data retrieval.
    """

    # Generate a Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)

    import numpy as np
    forecast.daily.high = np.round(np.random.rand() * 100.)
    forecast.daily.low = np.round(np.random.rand() * 100.)
    forecast.daily.wind = np.round(np.random.rand() * 40.)
    forecast.daily.rain = np.round(np.random.rand() * 3., 2)

    # Create a dummy pd dataframe to test
    forecast.timeseries.data['DateTime'] = [forecast_date, forecast_date +
                                            timedelta(hours=3)]
    forecast.timeseries.data['temperature'] = [56., 55.]
    forecast.timeseries.data['dewpoint'] = [51., 51.]

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from MOS.
    """

    # A driver that can be used for multiple model sources or that requires
    # extra parameters would here be tasked with reading the
    # config['Models'][model]. This could also be defined in a separate
    # function, i.e., to use it for both main() and historical().

    # Get forecast
    forecast = gfs_mos_forecast(stid, forecast_date)

    return forecast


def historical(config, model, stid, forecast_dates):
    """
    Produce a list of Forecast objects for each date in forecast_dates.
    """

    forecasts = []
    for forecast_date in forecast_dates:
        forecast = gfs_mos_forecast(stid, forecast_date)
        forecasts.append(forecast)

    return forecasts
