#
#
#
#

from datetime import datetime, timedelta
from highcharts import Highchart
#import sqlite3
import pandas as pd
import pdb
from thetae.db import db_readTimeSeries

"""
Generates timeseries plot for various models
"""

def plot_timeseries(config, stid, models, forecast_date, variable):
    """
    Timeseries plotting function
    """

    return

def main(config, stid, forecast_date):
    """
    Make a timeseries plot
    """

    # Get list of models
    models = config['Models'].keys()
    
    # Define variables. Possibly move this to config later
    variables = ['TEMPERATURE']

    # Get forecast
    for variable in variables:
        plot_timeseries(config, stid, models, forecast_date, variable)

    return
