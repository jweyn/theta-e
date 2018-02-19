#
# Copyright (c) 2018 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates timeseries plots for various models.
"""

from datetime import datetime, timedelta


def plot_timeseries(config, stid, models, forecast_date, variable):
    """
    Timeseries plotting function
    """

    return


def main(config, stid, forecast_date):
    """
    Make timeseries plots for a given station.
    """

    # Get list of models
    models = config['Models'].keys()
    
    # Define variables. Possibly move this to config later
    variables = ['TEMPERATURE']

    # Get forecast
    for variable in variables:
        plot_timeseries(config, stid, models, forecast_date, variable)

    return
