#
# Copyright (c) 2018 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates json output for web graphing.
"""

from datetime import datetime, timedelta


def json_timeseries(config, stid, models, forecast_date, variables):
    """
    json timeseries output function
    """

    return


def main(config, stid, forecast_date):
    """
    Produce json output for a given station.
    """

    # Get list of models
    models = config['Models'].keys()

    # Define variables. Possibly move this to config later
    variables = ['TEMPERATURE']

    # Get output
    json_timeseries(config, stid, models, forecast_date, variables)

    return
